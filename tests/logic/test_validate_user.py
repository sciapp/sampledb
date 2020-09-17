import pytest
import bcrypt

from sampledb.models import User, UserType,  Authentication, AuthenticationType

import sampledb
import sampledb.models
import sampledb.logic


@pytest.fixture
def users():
    names = ['User 1', 'User 2']
    users = [User(name=name, email="example@fz-juelich.de", type=UserType.PERSON) for name in names]
    password = 'test123'
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    log = {
        'login': 'example@fz-juelich.de',
        'bcrypt_hash': pw_hash
    }
    log1 = {
        'login': 'example1@fz-juelich.de',
        'bcrypt_hash': pw_hash
    }
    confirmed = False
    for user in users:
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
        if not confirmed:
            auth = Authentication(log, AuthenticationType.EMAIL, confirmed, user.id)
        else:
            auth = Authentication(log1, AuthenticationType.EMAIL, confirmed, user.id)
        confirmed = True
        sampledb.db.session.add(auth)
        sampledb.db.session.commit()
        assert Authentication.id is not None

    user = User(name='Experiment 1', email="example@fz-juelich.de", type=UserType.OTHER)
    users.append(user)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    log = {
        'login': 'ombe',
        'bcrypt_hash': pw_hash
    }
    # force attribute refresh

    auth = Authentication(log, AuthenticationType.OTHER, True, user.id)
    sampledb.db.session.add(auth)
    sampledb.db.session.commit()

    user = User(name='Mustermann', email="mustermann@fz-juelich.de", type=UserType.PERSON)
    users.append(user)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    return users


def test_validate_user_db(users):
    # user is not confirmed
    user = sampledb.logic.authentication.login('example@fz-juelich.de', 'test123')
    assert not user

    # user has no authentication method
    user = sampledb.logic.authentication.login('mustermann@fz-juelich.de', 'test123')
    assert not user

    # user is correct
    user = sampledb.logic.authentication.login('ombe', 'test123')
    assert user

    # password wrong
    user = sampledb.logic.authentication.login('ombe', 'test456')
    assert not user
