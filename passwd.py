import hashlib, binascii, os
import random as rnd
import sqlite3 as sql

class PasswordError(Exception):
    def __init__(self, message):
        super(PasswordError, self).__init__(message)
        self.message = message

class User(object):
    def __init__(self,name,passwd):
        global bol
        self.name = name
        self.connect()
        self.cursor.execute("SELECT * FROM users WHERE EXISTS(SELECT * FROM users WHERE name='{}');".format(self.name))
        res = self.cursor.fetchone()
        if res:
            self.passwd = _Pw(passwd,res[3].encode('utf-8'))
            self.passwd.hashcheck(res[2])
        else:
            del res
            self.passwd = _Pw(passwd)
            command = """
            INSERT INTO users (user_id, name, password, salt)
            VALUES (NULL, "{}", "{}", "{}");
            """.format(self.name, str(self.passwd.spw), str(self.passwd.salt))
            self.cursor.execute(command)
            self.connection.commit()
            self.connection.close()
            raise PasswordError('Created User')

        self.connection.commit()
        self.connection.close()

    def connect(self):
        try:
            sqlConnection()
        except:
            pass
        self.connection = sql.connect('assets/chat.db')
        self.cursor = self.connection.cursor()

class _Pw(User):
    def __init__(self,pw,salt='%X' % rnd.SystemRandom().randint(1000000000000,20000000000000)):
        self.salt = salt
        tmp = hashlib.pbkdf2_hmac('sha256', bytes(pw), bytes(self.salt), 100000)
        self.spw = binascii.hexlify(tmp)
        del tmp

    def update(self,oldpw,newpw):
        if self.spw == binascii.hexlify(hashlib.pbkdf2_hmac('sha256', bytes(oldpw), bytes(self.salt), 100000)):
            self.spw = binascii.hexlify(hashlib.pbkdf2_hmac('sha256', bytes(newpw), bytes(self.salt), 100000))
        else:
            raise PasswordError('Wrong Password')

    def check(self,pw,expect=False):
        if self.spw == binascii.hexlify(hashlib.pbkdf2_hmac('sha256', bytes(pw), bytes(self.salt), 100000)):
            return True
        else:
            if expect:
                return False
            else:
                raise PasswordError('Wrong Password')

    def hashcheck(self,hashed,expect=False):
        if str(self.spw) == str(hashed):
            return True
        else:
            if expect:
                return False
            else:
                raise PasswordError('Wrong Password')

def sqlConnection():
    connection = sql.connect('assets/chat.db')
    cursor = connection.cursor()

    command = """
    CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    name VARCHAR(20),
    password VARCHAR(100),
    salt VARCHAR(20));"""

    try:
        cursor.execute(command)
    except:
        pass

    connection.commit()
    connection.close()

if __name__ == '__main__':
    u = User('Michael','asdfg')
