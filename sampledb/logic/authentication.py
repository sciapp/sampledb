import bcrypt
import flask_login
from flask_login import login_user

from sampledb.logic.ldap import validate_user, get_user_info
from .. import db
from ..models import Authentication, AuthenticationType, User


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


def add_authentication_to_db(log,authentication_method,confirmed,id):
    auth = Authentication(log, authentication_method, confirmed, id)
    db.session.add(auth)
    db.session.commit()


def login(login,password):
    # filter email + password or username + password or username (ldap)
    authentication_methods = Authentication.query.filter(
        db.or_(
            db.and_(Authentication.login['login'].astext == login,
                    Authentication.type == AuthenticationType.EMAIL),
            db.and_(Authentication.login['login'].astext == login,
                    Authentication.type == AuthenticationType.LDAP),
            db.and_(Authentication.login['login'].astext == login,
                    Authentication.type == AuthenticationType.OTHER)
        )
    ).all()

    result = False
    for authentication_method in authentication_methods:
        # authentificaton method in db is ldap
        if authentication_method.type == AuthenticationType.LDAP:
            result = validate_user(login, password)
        else:
            result = validate_user_db(login, password)
        if result:
            user = authentication_method.user
            flask_login.login_user(user)
            return result

    # no authentificaton method in db or authentication_method not successfully
    if not authentication_methods:
        if '@' not in login:
            # try to authenticate against ldap, if login is no email
            result = validate_user(login, password)
            if not result:
                #                    flask.abort(403)
                return result
                # if authenticate with ldap insert to db
            else:
                newuser = get_user_info(login)
                # TODO: mehrer user können gleiche mail haben, aber nur einen login
                # ein user kann mehrere logins haben (experiment-account, normaler account z.B. henkel und lido)
                # look , if user in usertable without authentication method or other authentication method
                erg = User.query.filter_by(name=str(newuser.name), email=str(newuser.email)).first()
                # if not, add user to table
                if erg is None:
                    u = User(str(newuser.name), str(newuser.email), newuser.type)
                    db.session.add(u)
                    db.session.commit()
                # add authenticate method to table for user (old or new)
                user = User.query.filter_by(name=str(newuser.name), email=str(newuser.email)).first()
                if user is not None:
                    log = {'login': login}
                    add_authentication_to_db(log, AuthenticationType.LDAP, True, user.id)
                    flask_login.login_user(user)
                    return True
                else:
                    return False
        else:
            return result
    else:
        return result
