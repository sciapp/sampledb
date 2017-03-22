import pytest

from sampledb.models import User, UserType,  Authentication, AuthenticationType

import sampledb
import sampledb.models

from ..test_utils import app_context, flask_server, app

def test_add_user(flask_server):
    with flask_server.app.app_context():
        assert len(sampledb.models.User.query.all()) == 0
        user = User(name='Experiment 1', email="example@fz-juelich.de", type=UserType.OTHER)
        result = sampledb.logic.authentication.insert_user_and_authentication_method_to_db(user, 'test123',
                                                    'example@fz-juelich.de', sampledb.models.AuthenticationType.OTHER)
        assert len(sampledb.models.User.query.all()) == 1
        if result:
            user =  sampledb.models.query.get(1)
        assert user.id is not None

        assert len(sampledb.models.User.query.all()) == 1
        user = User(name='Mustermann', email="example@fz-juelich.de", type=UserType.PERSON)
        result = sampledb.logic.authentication.insert_user_and_authentication_method_to_db(user, 'test123',
                                                    'example@fz-juelich.de', sampledb.models.AuthenticationType.EMAIL)
        assert len(sampledb.models.User.query.all()) == 2
        if result:
            user = sampledb.models.query.get(2)
        assert user.id is not None

def test_add_user_LDAP(flask_server,app):
    with flask_server.app.app_context():
        username = app.config['TESTING_LDAP_LOGIN']
        password = app.config['TESTING_LDAP_PW']
        assert len(sampledb.models.User.query.all()) == 0
        user = User(name=username, email="d.henkel@fz-juelich.de", type=UserType.PERSON)
        result = sampledb.logic.authentication.insert_user_and_authentication_method_to_db(user, password, 'd.henkel@fz-juelich.de', sampledb.models.AuthenticationType.LDAP)
        assert len(sampledb.models.User.query.all()) == 1
        if result:
            user =  sampledb.models.query.get(1)
        assert user.id is not None

