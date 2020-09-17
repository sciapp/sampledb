import pytest
import flask

import sampledb
import sampledb.models

from sampledb.logic.errors import LDAPNotConfiguredError


def test_search_ldap(app):
    user = sampledb.logic.ldap._get_user_dn_and_attributes(app.config['TESTING_LDAP_UNKNOWN_LOGIN'], [app.config['LDAP_MAIL_ATTRIBUTE']])
    assert user is None

    user = sampledb.logic.ldap._get_user_dn_and_attributes(app.config['TESTING_LDAP_LOGIN'], [app.config['LDAP_MAIL_ATTRIBUTE']])
    assert user is not None
    user_dn, mail = user
    assert '@' in mail


def test_user_info(app):
    user = sampledb.logic.ldap.create_user_from_ldap(app.config['TESTING_LDAP_UNKNOWN_LOGIN'])
    assert user is None

    user = sampledb.logic.ldap.create_user_from_ldap(app.config['TESTING_LDAP_LOGIN'])
    assert user is not None


def test_validate_user(app):
    assert sampledb.logic.ldap.validate_user(app.config['TESTING_LDAP_LOGIN'], app.config['TESTING_LDAP_PW'])

    # wrong password
    assert not sampledb.logic.ldap.validate_user(app.config['TESTING_LDAP_LOGIN'], app.config['TESTING_LDAP_WRONG_PASSWORD'])

    # wrong uid
    assert not sampledb.logic.ldap.validate_user(app.config['TESTING_LDAP_UNKNOWN_LOGIN'], app.config['TESTING_LDAP_PW'])


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
