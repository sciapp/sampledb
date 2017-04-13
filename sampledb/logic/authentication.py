import bcrypt
import flask
import flask_login
import flask_mail

from .. import mail
from .. import logic
from sampledb.logic.ldap import validate_user, get_user_info, LdapAccountAlreadyExist, LdapAccountOrPasswordWrong
from .. import db
from ..models import Authentication, AuthenticationType, User, UserType


class OnlyOneAuthenticationMethod(Exception):
    pass


class AuthenticationMethodWrong(Exception):
    pass


def validate_user_db(login, password):
    authentication_methods = Authentication.query.filter(Authentication.login['login'].astext == login).all()
    for authentication_method in authentication_methods:
        if authentication_method.confirmed:
            if bcrypt.checkpw(password.encode('utf-8'), authentication_method.login['bcrypt_hash'].encode('utf-8')):
                user = authentication_method.user
                return True
    return False


def insert_user_and_authentication_method_to_db(user, password, login, user_type):
    db.session.add(user)
    db.session.commit()
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    login_data = {
        'login': login,
        'bcrypt_hash': pw_hash
    }
    add_authentication_to_db(login_data, user_type, True, user.id)


def add_authentication_to_db(log, user_type, confirmed, user_id):
    auth = Authentication(log, user_type, confirmed, user_id)
    db.session.add(auth)
    db.session.commit()


def login(login, password):
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

    for authentication_method in authentication_methods:
        # authentificaton method in db is ldap
        if authentication_method.type == AuthenticationType.LDAP:
            result = validate_user(login, password)
        else:
            result = validate_user_db(login, password)
        if result:
            user = authentication_method.user
            return user

    # no authentificaton method in db
    if not authentication_methods and '@' not in login:
        # try to authenticate against ldap, if login is no email
        if not validate_user(login, password):
            return None

        new_user = get_user_info(login)
        assert new_user.type == UserType.PERSON
        user = User.query.filter_by(email=str(new_user.email), type=UserType.PERSON).first()
        if user is None:
            user = new_user
            db.session.add(user)
            db.session.commit()
        add_authentication_to_db({'login': login}, user_type=AuthenticationType.LDAP, confirmed=True, user_id=user.id)
        return user
    return None


def add_login(userid, login, password, authentication_method):
    logins = Authentication.query.filter(Authentication.login['login'].astext == login,
                                         Authentication.user_id == userid).first()
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    log = {
        'login': login,
        'bcrypt_hash': pw_hash
    }
    if authentication_method == AuthenticationType.EMAIL:
        # check if login looks like an email
        if '@' not in login:
            raise AuthenticationMethodWrong('Login must be an email if the authentication_method is email')
        else:
            # send confirm link
            logic.utils.send_confirm_email(login, userid, 'add_login')
            confirmed = False
    elif authentication_method == AuthenticationType.OTHER:
        confirmed = True
    else:
        if logins is not None:
            # authentication-method already exists
            raise LdapAccountAlreadyExist('Ldap-Account already exists')
        if not validate_user(login, password):
            raise LdapAccountOrPasswordWrong('Ldap login or password wrong')
        confirmed = True
    add_authentication_to_db(log, authentication_method, confirmed, userid)
    return True


def remove_authentication_method(user_id, authentication_method_id):
    authentication_methods_count = Authentication.query.filter(Authentication.user_id == user_id).count()
    if authentication_methods_count <= 1:
        raise OnlyOneAuthenticationMethod('one authentication-method must at least exist, delete not possible')
    authentication_methods = Authentication.query.filter(Authentication.id == authentication_method_id).first()
    assert authentication_methods
    db.session.delete(authentication_methods)
    db.session.commit()
    return True
