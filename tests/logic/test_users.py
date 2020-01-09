
import pytest

import sampledb.models
import sampledb.logic
from sampledb import db

from ..test_utils import app_context


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
