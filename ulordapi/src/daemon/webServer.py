# coding=utf-8
# @File  : webServer.py
# @Author: PuJi
# @Date  : 2018/5/3 0003

import os, time, requests, json, logging
from uuid import uuid1

from flask import request, g, jsonify

from ulordapi.src.db.manage import app, db, User
from ulordapi.src.ulordpaltform.up import ulord_helper
from ulordapi.src.utils.fileHelper import fileHelper
from ulordapi import ulordconfig
from ulordapi.src.utils.Checker import checker
from ulordapi.src.utils.encryption import rsahelper
from ulordapi.src.utils.errcode import return_result

log = logging.getLogger('webServer')

def auth_login_required():
    head_token = request.headers.get('token')
    if not head_token:
        return {
            'errcode':60103,
            'reason': "需要token"
        }
    login_user = User.query.filter_by(token=head_token).first()
    if not login_user:
        return return_result(60104)
    if int(login_user.timestamp) < time.time():
        return return_result(60104)
    return login_user


@app.route('/user/password', methods=['GET', 'POST'])
def get_pubkey():
    print("start get password")
    if request.method == 'GET':
        return jsonify(return_result(0, result={"pubkey":rsahelper.pubkeybytes}))
    elif request.method == 'POST':
        message = request.json.get("password")
        return jsonify(return_result(0, result={'password': rsahelper.decrypt(rsahelper.privkey, message)}))


@app.route('/user/regist',methods=['POST'])
def regist():
    username = request.json.get('username')
    password = request.json.get('password')
    cellphone = request.json.get('cellphone')
    email = request.json.get('email')
    if username is None or password is None:
        # missing arguments
        return jsonify(return_result(60100))
    try:
        username = rsahelper.decrypt(rsahelper.privkey, username)
        password = rsahelper.decrypt(rsahelper.privkey, password)
    except:
        log.warn("fronted doesn't encrypt")
    # if User.query.filter_by(username=username).first() is not None and User.query.filter_by(wallet=username).first() is not None:
    # delete modify username.It will make the publish error
    if User.query.filter_by(username=username).first() is not None and User.query.filter_by(
                wallet=username).first() is not None:
        # existing user
        return jsonify(return_result(60000))
    # check cellphone and email
    if cellphone:
        try:
            cellphone = rsahelper.decrypt(rsahelper.privkey, cellphone)
        except:
            print("frontend doesn't encrypt cellphone")
        if not checker.isCellphone(cellphone):
            return jsonify(return_result(60106))
    if email:
        try:
            email = rsahelper.decrypt(rsahelper.privkey, email)
        except:
            print("frontend doesn't encrypt email")
        if not checker.isMail(email):
            return jsonify({
                'errcode': 60105,
                'reason': '无效的邮箱'
            })
    # user get wallet and password (or not) from ulord platform
    user = User(username=username)
    user.hash_password(password)
    user.wallet = username
    user.pay_password = user.password_hash
    regist_result = ulord_helper.regist(user.wallet, user.pay_password)
    if regist_result.get("errcode") != 0:
        return jsonify(regist_result)
    # 不能移动，先判断再提交。否则验证失败可能也会提交
    if cellphone:
        user.cellphone = cellphone
    if email:
        user.email = email

    token = str(uuid1())
    user.token = token
    user.timestamp = int(time.time()) + 24 * 60 * 60
    db.session.add(user)
    db.session.commit()
    return jsonify(return_result(0, reason={'token':token}))


@app.route('/user/activity', methods=['GET'])
def activity():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    if current_user.activity == ulordconfig.get('amount'):
        return jsonify({
            'errcode': 60301,
            'reason': "已赠送"
        })
    else:
        credit_result = ulord_helper.paytouser(current_user.wallet)
        for retry in range(2):
            if credit_result.get("errcode") == 0:
                break
            else:
                credit_result = ulord_helper.paytouser(current_user.wallet)

        if credit_result.get("errcode") != 0:
            return jsonify(credit_result)
        else:
            current_user.activity = ulordconfig.get('amount')
            return jsonify({
                "errcode": 0,
                "reason": "success",
                "result":{
                    "amount": ulordconfig.get('amount'),
                    }
            })


@app.route('/user/login',methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    print(username)
    print(password)
    if username is None or password is None:
        # missing arguments
        return jsonify({
            'errcode': 60100,
            'reason': "缺少参数"
        })
    try:
        username = rsahelper.decrypt(rsahelper.privkey, username)
        # print(username)
        password = rsahelper.decrypt(rsahelper.privkey, password)
    except:
        print("frontend doesn's encrypt")
    login_user = User.query.filter_by(username=username).first()
    if not login_user:
        # no user
        return jsonify({
            'errcode': 60002,
            'reason': "用户不存在"
        })
    if not login_user.verify_password(password):
        # error password
        return jsonify({
            'errcode': 60003,
            'reason': "密码错误"
        })
    token = str(uuid1())
    login_user.token = token
    login_user.timestamp = int(time.time()) + 24 * 60 * 60
    db.session.commit()
    return jsonify({
        'errcode':0,
        'reason': "success",
        'result':{
            "token":token
        }
    })


@app.route('/user/logout',methods=['POST','GET'])
def logout():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    current_user.timestamp = int(time.time()) - 1 # auth_login_require check the timestamp
    return jsonify({
        'errcode': 0,
        'reason': "success",
        'result': "success"
    })


@app.route('/blog/publish',methods=['POST'])
def blog_publish():
    current_user = auth_login_required() # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    title = request.json.get('title')
    body = request.json.get('body')
    amount = request.json.get('amount')
    tags = request.json.get('tag')
    description = request.json.get('description')
    if title is None or body is None or amount is None:
        # missing arguments
        return jsonify({
            'errcode': 60100,
            'reason':"缺少参数"
        })
    # TODO upload body to IPFS
    start = time.time()
    try:
        body_txt = os.path.join(os.path.join(os.getcwd(), 'blogs'), '{}.txt'.format(title))
    except:
        print("Doesn't support chinese.Using uuid")
        body_txt = os.path.join(os.path.join(os.getcwd(), 'blogs'), '{}.txt'.format(str(uuid1())))
    if fileHelper.saveFile(body_txt, body):
        end_save = time.time()
        print({
            'start':start,
            'end_save':end_save,
            'total':end_save - start
        })
        file_hash = ulord_helper.upload(body_txt)
        end_upload = time.time()
        print({
            'start':end_save,
            'end_upload':end_upload,
            'total':end_upload - end_save
        })
        try:
            os.remove(body_txt)
            end_remove = time.time()
            print({
                'start':end_upload,
                'end_remove': end_remove,
                'total':end_remove - end_upload
            })
        except:
            print("Error rm {}".format(body_txt))

        # TODO publish
        # init data schema
        data = ulord_helper.ulord_publish_data
        data['author'] = current_user.wallet
        data['title'] = title
        data['tag'] = tags
        data['ipfs_hash'] = file_hash
        data['price'] = amount
        data['pay_password'] = current_user.pay_password
        data['description'] = description
        result = ulord_helper.publish(data)
        end_publish = time.time()
        print({
            'start':end_remove,
            'end_publish':end_publish,
            'total':end_publish - end_remove
        })
        return jsonify(result)
    else:
        return jsonify({
            'errcode': 60200,
            'reason': "上传文件失败"
        })


@app.route('/blog/all/list',methods=['POST'])
def blog_list():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    try:
        page = request.json.get('page')
        num = request.json.get('num')
    except:
        page = 1
        num = 10
    if not page:
        page = 1
    if not num:
        num = 10
    return jsonify(ulord_helper.queryblog(page, num))


@app.route('/blog/isbought',methods=['POST'])
def check_bought():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    claim_ids = request.json.get('claim_ids')
    if claim_ids is None:
        return jsonify({
            'errcode': 60100,
            'reason': '缺少参数'
        })
    # check if has bought
    return jsonify(ulord_helper.checkisbought(current_user.wallet, claim_ids))


@app.route('/blog/views',methods=['POST'])
def add_views():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    dbID = request.json.get('id')
    if dbID is None:
        return jsonify({
            'errcode': 60100,
            'reason': '缺少参数'
        })
    # add blog views
    return jsonify(ulord_helper.addviews(dbID))


@app.route('/pay/blogs',methods=['POST'])
def pay_blogs():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    password = request.json.get('password')
    claim_id = request.json.get('claim_id')
    if password is None or claim_id is None:
        return jsonify({
            'errcode':60100,
            'reason':"缺少参数"
        })
    try:
        print("current password:{}".format(password))
        password = rsahelper.decrypt(rsahelper.privkey, password)
        print("decrypt password:{}".format(password))
    except:
        print("frontend doesn't encrypt")
    if not current_user.verify_password(password):
        return jsonify({
            'errcode': 60003,
            'reason': '密码错误'
        })
    return jsonify(ulord_helper.transaction(current_user.wallet, claim_id, current_user.pay_password))


@app.route('/pay/ads',methods=['POST'])
def pay_ads():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    claim_id = request.json.get('claim_id')
    author = request.json.get('author')
    if claim_id is None or author is None:
        return jsonify({
            'errcode': 60100,
            'reason': "缺少参数"
        })
    author_user = User.query.filter_by(username=author).first()
    if not author_user:
        return jsonify({
            "errcode": 60006,
            "reason": "作者已失效"
        })
    pay_password = author_user.pay_password
    return jsonify(ulord_helper.transaction(current_user.wallet, claim_id, pay_password, True))


@app.route('/user/info',methods=['GET'])
def get_userinfo():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    return jsonify({
        'errcode':0,
        'reason':'success',
        'result':{
    	    "username": current_user.username,
            "cellphone": current_user.cellphone,
            "Email": current_user.email
            }
    })


@app.route('/user/balance',methods=['GET'])
def get_userbalance():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    return jsonify(ulord_helper.querybalance(current_user.wallet, current_user.pay_password))


@app.route('/user/published',methods=['POST'])
def get_userpublished():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    try:
        page = request.json.get('page')
        num = request.json.get('num')
        category = request.json.get('category')
    except:
        page = 1
        num = 10
        category = 2  # 0-blog,1-ads,2-all
    if not page:
        page = 1
    if not num:
        num = 10
    if not category or category!=0 or category!=1 :
        category = 2  # 0-blog,1-ads,2-all
    return jsonify(ulord_helper.queryuserpublished(current_user.wallet, page, num, category))


@app.route('/user/published/num',methods=['GET'])
def get_userpublishednum():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    return jsonify(ulord_helper.querypublishnum(current_user.wallet))


@app.route('/user/bought',methods=['POST'])
def get_userbought():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    try:
        page = request.json.get('page')
        num = request.json.get('num')
        category = request.json.get('category')
    except:
        page = 1
        num = 10
        category = 2  # 0-blog,1-ads,2-all
    if not page:
        page = 1
    if not num:
        num = 10
    if not category or category!=0 or category!=1 :
        category = 2  # 0-blog,1-ads,2-all
    return jsonify(ulord_helper.queryuserbought(current_user.wallet, page, num, category))


@app.route('/user/billings',methods=['GET'])
def get_billings():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    return jsonify(ulord_helper.querybillings(current_user.wallet))


@app.route('/user/billings/details',methods=['POST'])
def get_billingsdetail():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    try:
        page = request.json.get('page')
        num = request.json.get('num')
    except:
        page = 1
        num = 10
    if not page:
        page = 1
    if not num:
        num = 10
    return jsonify(ulord_helper.querybillingsdetail(current_user.wallet, page, num))


@app.route('/user/billings/income',methods=['POST'])
def get_incomebillings():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    try:
        page = request.json.get('page')
        num = request.json.get('num')
    except:
        page = 1
        num = 10
    if not page:
        page = 1
    if not num:
        num = 10
    return jsonify(ulord_helper.queryincomebillings(current_user.wallet, page, num))


@app.route('/user/billings/outgo',methods=['POST'])
def get_expensebillings():
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    try:
        page = request.json.get('page')
        num = request.json.get('num')
    except:
        page = 1
        num = 10
    if not page:
        page = 1
    if not num:
        num = 10
    return jsonify(ulord_helper.queryoutgobillings(current_user.wallet, page, num))


@app.route('/user/modify',methods=['POST'])
def modify_userinfo():
    # Delete modify username.It will make publish error
    current_user = auth_login_required()  # check token
    if type(current_user) is dict:
        return jsonify(current_user)
    # username = request.json.get('username')
    password = request.json.get('password')
    cellphone = request.json.get('cellphone')
    email = request.json.get('email')
    new_password = request.json.get('new_password')
    if not password:
        # missing arguments
        return jsonify({
            'errcode': 60100,
            'reason': '缺少参数'
        })
    else:
        try:
            password = rsahelper.decrypt(rsahelper.privkey, password)
        except:
            print("frontend doesn't encrypt password")
    if not current_user.verify_password(password):
        return jsonify({
            'errcode': 60003,
            'reason': '密码错误'
        })
    # check cellphone and email
    if cellphone:
        try:
            cellphone = rsahelper.decrypt(rsahelper.privkey, cellphone)
        except:
            print("frontend doesn't encrypt cellphone")
        if not checker.isCellphone(cellphone):
            return jsonify({
                'errcode': 60106,
                'reason': '无效的手机号'
            })
    if email:
        try:
            email = rsahelper.decrypt(rsahelper.privkey, email)
        except:
            print("frontend doesn't encrypt email")
        if not checker.isMail(email):
            return jsonify({
                'errcode': 60105,
                'reason': '无效的邮箱'
            })

    # if username:
    #     if (User.query.filter_by(username=username).first() is not None) & (User.query.filter_by(wallet=username).first() is not None):
    #         # existing user
    #         return jsonify({
    #             'errcode': 60000,
    #             'reason': "账户已存在"
    #         })
    #     current_user.username = username
    if new_password:
        try:
            new_password = rsahelper.decrypt(rsahelper.privkey, new_password)
        except:
            print("frontend doesn't encrypt new_password")
        current_user.hash_password(new_password)
    # 不能移动，先判断再提交。否则验证失败可能也会提交
    if cellphone:
        current_user.cellphone = cellphone
    if email:
        current_user.email = email
    db.session.commit()
    return jsonify({
        'errcode': 0,
        'reason': "Success",
        "result":{
            "userid": current_user.id,
            "username":current_user.username,
            "email": current_user.email,
            "cellphone": current_user.cellphone
        }
    })


def start():
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(5000)
    IOLoop.instance().start()
    # app.run(host='0.0.0.0', port=5050)


if __name__ == '__main__':
    start()