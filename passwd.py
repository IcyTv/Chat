import hashlib, binascii, os
import random as rnd
import sqlite3 as sql
import getpass
from base64 import b64encode
import logging as log


#log.basicConfig(level=log.DEBUG, format='[%(levelname)s] %(message)s')

def path_to_temp(relative_path):
    try:
        base_path = os.path.dirname(__file__)
    except Exception:
        base_path = os.path.abspath(".")

    path = os.path.join(base_path, relative_path)
    return path

class PasswordError(Exception):
    def __init__(self, message):
        super(PasswordError, self).__init__(message)
        self.message = message

class User(object):
    def __init__(self,name,passwd):
        global bol
        self.name = name
        self.connect()
        self.check()
        self.cursor.execute("""SELECT * FROM users WHERE name="{}";""".format(self.name))
        res = self.cursor.fetchone()
        if res:
            self.passwd = _Pw(passwd,res[3].encode('utf-8'))
            self.passwd.hashcheck(res[2])
        else:
            del res
            self.passwd = _Pw(passwd)
            command = """
            INSERT INTO users (user_id, name, password, salt, os_user)
            VALUES (NULL, "{}", "{}", "{}","{}");
            """.format(self.name, str(self.passwd.spw), str(self.passwd.salt),getpass.getuser())
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
        self.connection = sql.connect(path_to_temp('./assets/chat.db'))
        self.cursor = self.connection.cursor()

    def check(self):
        self.cursor.execute("""SELECT name FROM users WHERE os_user="{}";""".format(getpass.getuser()))
        res = self.cursor.fetchone()
        if res and self.name != res[0]:
            raise PasswordError('Only one user allowed!')

    @staticmethod
    def delete():
        connection = sql.connect(path_to_temp('./assets/chat.db'))
        cursor = connection.cursor()
        cursor.execute("""DELETE FROM users WHERE os_user="{}";""".format(getpass.getuser()))
        connection.commit()

class _Pw(User):
    def __init__(self,pw,salt=b64encode(os.urandom(64)).decode('utf-8')):
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
    connection = sql.connect(path_to_temp('./assets/chat.db'))
    cursor = connection.cursor()

    command = """
    CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    name VARCHAR(20),
    password VARCHAR(100),
    salt VARCHAR(20),
    os_user VARCHAR(20));"""

    try:
        cursor.execute(command)
    except:
        pass

    connection.commit()
    connection.close()

if __name__ == '__main__':
    u = User('Michael','asdfg')
