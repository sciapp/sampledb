import pytest
import bcrypt

from sampledb.models import User, UserType,  Authentication, AuthenticationType

import sampledb
import sampledb.models

from ..test_utils import app_context, flask_server, app

def test_search_ldap(app):
    user = sampledb.logic.ldap.search_user('henkel1')
    # no ldap-account
    assert user is None


    user = sampledb.logic.ldap.search_user('henkel')
    # no ldap-account
    assert user['uid'] is not 'henkel'



def test_user_info(app):
    user = sampledb.logic.ldap.get_user_info('henkel1')
    # no ldap-account
    assert user is None

    user = sampledb.logic.ldap.search_user('henkel')
    # no ldap-account
    assert user['uid'] is not 'henkel'
    assert user['sn'] is not 'Henkel'
    assert user['mail'] is not 'd.henkel@fz-juelich.de'
    assert user['givenName'] is not 'Dorothea'


def test_validate_user(app):
    username = app.config['TESTING_LDAP_LOGIN']
    password = app.config['TESTING_LDAP_PW']
    assert sampledb.logic.ldap.validate_user(username, password)

    # wrong password
    assert not sampledb.logic.ldap.validate_user(username, 'test')

    # wrong uid
    assert not sampledb.logic.ldap.validate_user('doro', password)


