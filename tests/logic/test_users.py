import pytest

import sampledb.models
import sampledb.logic
from sampledb import db


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user

def test_get_users_by_name():
    user1 = sampledb.models.User(
        name="User",
        email="example@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    db.session.add(user1)
    db.session.commit()
    user2 = sampledb.models.User(
        name="User",
        email="example@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    db.session.add(user2)
    db.session.commit()

    users = sampledb.logic.users.get_users_by_name("User")
    assert len(users) == 2
    assert user1 in users
    assert user2 in users

    user2.name = "Test-User"
    db.session.add(user2)
    db.session.commit()

    users = sampledb.logic.users.get_users_by_name("User")
    assert len(users) == 1
    assert user1 in users
    assert user2 not in users


def test_get_users_exclude_hidden():
    user1 = sampledb.models.User(
        name="User",
        email="example@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    db.session.add(user1)
    db.session.commit()
    user2 = sampledb.models.User(
        name="User",
        email="example@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    db.session.add(user2)
    db.session.commit()

    users = sampledb.logic.users.get_users()
    users.sort(key=lambda u: u.id)
    assert users == [user1, user2]

    sampledb.logic.users.set_user_hidden(user1.id, True)

    users = sampledb.logic.users.get_users()
    users.sort(key=lambda u: u.id)
    assert users == [user1, user2]

    users = sampledb.logic.users.get_users(exclude_hidden=True)
    users.sort(key=lambda u: u.id)
    assert users == [user2]


def test_set_user_hidden(user):
    user = sampledb.logic.users.get_user(user.id)
    assert not user.is_hidden
    sampledb.logic.users.set_user_hidden(user.id, True)
    assert user.is_hidden
    sampledb.logic.users.set_user_hidden(user.id, False)
    assert not user.is_hidden


def test_set_user_readonly(user):
    user = sampledb.logic.users.get_user(user.id)
    assert not user.is_readonly
    sampledb.logic.users.set_user_readonly(user.id, True)
    assert user.is_readonly
    sampledb.logic.users.set_user_readonly(user.id, False)
    assert not user.is_readonly


def test_set_user_administrator(user):
    user = sampledb.logic.users.get_user(user.id)
    assert not user.is_admin
    sampledb.logic.users.set_user_administrator(user.id, True)
    assert user.is_admin
    sampledb.logic.users.set_user_administrator(user.id, False)
    assert not user.is_admin
