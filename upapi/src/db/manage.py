# coding=utf-8
# @File  : manage.py
# @Author: PuJi
# @Date  : 2018/4/20 0020
# @Description: this ia used for creating database and create db model

import os, sys

from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from passlib.apps import custom_app_context as pwd_context
from flask_cors import CORS
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

sys.path.append('../')
from upapi.config import DevConfig

# initialization
app = Flask(__name__)

app.config.from_object(DevConfig)

# cors = CORS(app, resources={r"/*": {"origins": "*"}})
db = SQLAlchemy(app)


resources_tags = db.Table('baseresources_tags',
                        db.Column('baseresources_id', db.String(45), db.ForeignKey('BaseResources.id')),
                        db.Column('tag_id', db.Integer, db.ForeignKey('tags.id')))


users_resources = db.Table('users_resources',
                        db.Column('user_id',db.Integer, db.ForeignKey('users.id')),
                        db.Column('resource_id', db.Integer, db.ForeignKey('BaseResources.id')))


class User(db.Model):

    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(32), index = True)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(32))
    cellphone = db.Column(db.String(12))
    token = db.Column(db.String(128), index=True)
    timestamp = db.Column(db.String(10))
    balance = db.Column(db.Float)
    wallet = db.Column(db.String(34))
    pay_password = db.Column(db.String(128))
    boughts = db.relationship(
        'Resource',
        secondary=users_resources,
        backref=db.backref('resources', lazy='dynamic')
    )

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)


class BaseResource(db.Model):
    __tablename__ = 'BaseResources'
    id = db.Column(db.String(45), primary_key=True)
    title = db.Column(db.String(32), index=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.id'))
    body = db.Column(db.String(46))
    amount = db.Column(db.Float, index=True)
    tags = db.relationship(
        'Tag',
        secondary=resources_tags,
        backref=db.backref('resources', lazy='dynamic'))
    description = db.Column(db.String(128))
    views = db.Column(db.Integer)
    date = db.Column(db.Integer)
    claimID = db.Column(db.String(40))


# class Resource():
#     __tablename__ = 'resources'
#     id = db.Column(db.String(45), primary_key=True)
#     title = db.Column(db.String(32), index=True)
#     userid = db.Column(db.Integer, db.ForeignKey('users.id'))
#     body = db.Column(db.String(46))
#     amount = db.Column(db.Float, index=True)
#     tags = db.relationship(
#         'Tag',
#         secondary=resources_tags,
#         backref=db.backref('resources', lazy='dynamic'))
#     description = db.Column(db.String(128))
#     views = db.Column(db.Integer)
#     date = db.Column(db.Integer)
#     claimID = db.Column(db.String(40))

# class Ads():
#     __tablename__ = 'ads'
#     id = db.Column(db.String(45), primary_key=True)
#     title = db.Column(db.String(32), index=True)
#     userid = db.Column(db.Integer, db.ForeignKey('users.id'))
#     body = db.Column(db.String(46))
#     amount = db.Column(db.Float, index=True)
#     tags = db.relationship(
#         'Tag',
#         secondary=resources_tags,
#         backref=db.backref('resources', lazy='dynamic'))
#     description = db.Column(db.String(128))
#     views = db.Column(db.Integer)
#     date = db.Column(db.Integer)
#     claimID = db.Column(db.String(40))

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    tagname = db.Column(db.String(32), index=True)
    # Reserved field
    pre1 = db.Column(db.String())
    pre2 = db.Column(db.String())

    def __init__(self, name):
        self.tagname = name


class Billing(db.Model):
    __tablename__ = 'billings'
    id = db.Column(db.Integer, primary_key=True)
    payer = db.Column(db.Integer, index=True)
    amount = db.Column(db.Float)
    payee = db.Column(db.Integer, index=True)
    titleid = db.Column(db.String, db.ForeignKey('BaseResources.id')) # title_id foreign key

    # Reserved field
    pre1 = db.Column(db.String())
    pre2 = db.Column(db.String())


if __name__ == '__main__':
    # db.create_all(bind=['resources_tags', 'users_resources', 'User', 'Resource', 'Ads', 'Tag', 'Billing'])
    db.create_all()