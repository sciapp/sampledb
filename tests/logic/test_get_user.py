import pytest
import bcrypt
from bs4 import BeautifulSoup

from sampledb.models import User, UserType,  Authentication, AuthenticationType

import sampledb
import sampledb.models
import sampledb.logic


from ..test_utils import app_context, flask_server, app

@pytest.fixture
def users():
    names = ['User 1', 'User 2']
    users = [User(name=name, email="example@fz-juelich.de", type=UserType.PERSON) for name in names]
    confirmed = False
    for user in users:
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None

    return users


def test_get_user(users):
    user = users[0]
    user = sampledb.logic.user.get_user(user.id)
    assert 1 == user.id
    assert 'example@fz-juelich.de' == user.email


def test_get_user_failed(users):
    user = users[0]
    user = sampledb.logic.user.get_user(None)
    assert user is None

    user = sampledb.logic.user.get_user(0)
    assert user is None

    # user.id 10 doesn't exists in db
    user = sampledb.logic.user.get_user(10)
    assert user is None