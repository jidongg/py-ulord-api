# coding=utf-8
# @File  : checker.py
# @Author: PuJi
# @Date  : 2018/4/16 0016

import re


class Checker(object):
    def __init__(self):
        self.cellphone = re.compile(r'[1][^1269]\d{9}')
        self.mail = re.compile(r'[^\._][\w\._-]+@(?:[A-Za-z0-9]+\.)+[A-Za-z]+$')

    def isCellphone(self, number):
        res = self.cellphone.match(number)
        if res:
            return True
        else:
            return False

    def isMail(self, mail):
        res = self.mail.match(mail)
        if res:
            return True
        else:
            return False

    def isUdfsHash(self, udfshash):
        # simple check
        # TODO advanced check
        if len(udfshash) == 46 and udfshash.startwith('Qm'):
            return True
        else:
            return False


checker = Checker()


if __name__ == '__main__':
    while True:
        cellphone = raw_input("cellphone:")
        print checker.isCellphone(cellphone)
        mail = raw_input("email:")
        print checker.isMail(mail)