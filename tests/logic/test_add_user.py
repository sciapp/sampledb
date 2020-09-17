

import sampledb
import sampledb.models
from sampledb.models import UserType
import sampledb.logic



def test_add_user(flask_server):
    with flask_server.app.app_context():
        assert len(sampledb.models.User.query.all()) == 0
        user = sampledb.logic.users.create_user(name='Experiment 1', email="user@example.com", type=UserType.OTHER)
        sampledb.logic.authentication.add_other_authentication(user.id, 'username', 'password')
        assert len(sampledb.models.User.query.all()) == 1
        assert user.id is not None

        assert len(sampledb.models.User.query.all()) == 1
        user = sampledb.logic.users.create_user(name='Mustermann', email="user@example.com", type=UserType.PERSON)
        sampledb.logic.authentication.add_email_authentication(user.id, 'user@example.com', 'password')
        assert len(sampledb.models.User.query.all()) == 2
        assert user.id is not None


def test_add_user_ldap(flask_server, app):
    with flask_server.app.app_context():
        username = app.config['TESTING_LDAP_LOGIN']
        password = app.config['TESTING_LDAP_PW']
        assert len(sampledb.models.User.query.all()) == 0
        user = sampledb.logic.users.create_user(name=username, email="user@example.com", type=UserType.PERSON)
        sampledb.logic.authentication.add_ldap_authentication(user.id, username, password)
        assert len(sampledb.models.User.query.all()) == 1
        assert user.id is not None
