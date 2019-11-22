import pytest
import flask

import sampledb
import sampledb.models

from sampledb.logic.errors import NoEmailInLDAPAccountError, LDAPNotConfiguredError

from ..test_utils import app_context, flask_server, app


def test_search_ldap(app):
    user = sampledb.logic.ldap._get_user_dn_and_attributes('henkel1', ['uid'])
    assert user is None

    user = sampledb.logic.ldap._get_user_dn_and_attributes('henkel', ['uid'])
    assert user is not None
    user_dn, uid = user
    assert uid == 'henkel'


def test_user_info(app):
    user = sampledb.logic.ldap.create_user_from_ldap('henkel1')
    assert user is None

    with pytest.raises(NoEmailInLDAPAccountError) as excinfo:
        sampledb.logic.ldap.create_user_from_ldap('gast')
    # no email exist
    assert 'There is no email set for your LDAP account. Please contact your administrator.' in str(excinfo.value)

    user = sampledb.logic.ldap.create_user_from_ldap('henkel')
    assert user is not None


def test_validate_user(app):
    username = app.config['TESTING_LDAP_LOGIN']
    password = app.config['TESTING_LDAP_PW']
    assert sampledb.logic.ldap.validate_user(username, password)

    # wrong password
    assert not sampledb.logic.ldap.validate_user(username, 'test')

    # wrong uid
    assert not sampledb.logic.ldap.validate_user('doro', password)

    with pytest.raises(NoEmailInLDAPAccountError) as excinfo:
        sampledb.logic.ldap.create_user_from_ldap('gast')
    # no email exist
    assert 'There is no email set for your LDAP account. Please contact your administrator.' in str(excinfo.value)


def test_is_ldap_configured():
    assert sampledb.logic.ldap.is_ldap_configured()
    ldap_server = flask.current_app.config['LDAP_SERVER']
    flask.current_app.config['LDAP_SERVER'] = ''
    assert not sampledb.logic.ldap.is_ldap_configured()
    with pytest.raises(LDAPNotConfiguredError):
        sampledb.logic.ldap.validate_user('', '')
    with pytest.raises(LDAPNotConfiguredError):
        sampledb.logic.ldap.create_user_from_ldap('')
    flask.current_app.config['LDAP_SERVER'] = ldap_server
