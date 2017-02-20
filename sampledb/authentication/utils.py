import bcrypt
from flask_login import login_user
from .models import Authentication


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
