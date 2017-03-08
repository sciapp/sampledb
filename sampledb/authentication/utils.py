import bcrypt
from flask_login import login_user
from .models import Authentication, User, AuthenticationType
from .. import db


def validate_user_db(login, password):
    authentication_methods = Authentication.query.filter(Authentication.login['login'].astext == login).all()
    for authentication_method in authentication_methods:
        if(authentication_method.confirmed):
            if bcrypt.checkpw(password.encode('utf-8'), authentication_method.login['bcrypt_hash'].encode('utf-8')):
                user = authentication_method.user
                login_user(user)
                return True
    return False

def insert_user_and_authentication_method_to_db(user, password, login, authentication_method):
    db.session.add(user)
    db.session.commit()
    if user.id is not None:
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        log = {
            'login': login,
            'bcrypt_hash': pw_hash
        }
        confirmed = True
        auth = Authentication(log, authentication_method, confirmed , user.id)
        db.session.add(auth)
        db.session.commit()
        return True
    return False