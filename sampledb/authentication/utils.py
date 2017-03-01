import bcrypt
from flask_login import login_user
from .models import Authentication, User, AuthenticationType
from .. import db


def validate_user_db(login, password):
    print('validate_db')
    print(login)
    authentication_methods = Authentication.query.filter(Authentication.login['login'].astext == login).all()
    print(authentication_methods)
    for authentication_method in authentication_methods:
        if bcrypt.checkpw(password.encode('utf-8'), authentication_method.login['bcrypt_hash'].encode('utf-8')):
            user = authentication_method.user
            print(user)
            login_user(user)
            return True
    return False

def insert_user_and_authentication_method_to_db(user, password, login, authentication_method):
    db.session.add(user)
    db.session.commit()
    print('insert_db')
    if user.id is not None:
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        log = {
            'login': login,
            'bcrypt_hash': pw_hash
        }
        auth = Authentication(log, authentication_method, user.id)
        db.session.add(auth)
        db.session.commit()
        return True
    return False