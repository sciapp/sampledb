import pytest

from sampledb.models import User, UserType

import sampledb
import sampledb.models
import sampledb.logic


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
    user = sampledb.logic.users.get_user(user.id)
    assert 1 == user.id
    assert 'example@fz-juelich.de' == user.email


def test_get_user_failed():
    with pytest.raises(TypeError):
        sampledb.logic.users.get_user(None)

    # user.id 10 doesn't exists in db
    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.users.get_user(10)
