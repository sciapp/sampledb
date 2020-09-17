# coding: utf-8
"""

"""

import pytest
import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def user():
    user = sampledb.models.User(
        name="User",
        email="example1@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return user


def test_get_default_settings(user):
    sampledb.logic.settings.DEFAULT_SETTINGS = {
        "test": True
    }
    assert sampledb.logic.settings.get_user_settings(user.id) == {
        "test": True
    }


def test_set_settings(user):
    sampledb.logic.settings.DEFAULT_SETTINGS = {
        "test": True,
        "other": ""
    }
    sampledb.logic.settings.set_user_settings(user.id, {
        "test": False
    })
    assert sampledb.logic.settings.get_user_settings(user.id) == {
        "test": False,
        "other": ""
    }
    sampledb.logic.settings.set_user_settings(user.id, {
        "other": "test"
    })
    assert sampledb.logic.settings.get_user_settings(user.id) == {
        "test": False,
        "other": "test"
    }


def test_set_invalid_settings(user):
    sampledb.logic.settings.DEFAULT_SETTINGS = {
        "test": True,
        "other": ""
    }
    sampledb.logic.settings.set_user_settings(user.id, {
        "test": "False",
        "other": "test",
        "invalid1": None,
        "invalid2": True
    })
    assert sampledb.logic.settings.get_user_settings(user.id) == {
        "test": True,
        "other": "test"
    }


def test_set_custom_settings(user):
    sampledb.logic.settings.DEFAULT_SETTINGS = {
        "test": True,
        "other": None
    }
    sampledb.logic.settings.set_user_settings(user.id, {
        "test": False,
        "other": "test"
    })
    assert sampledb.logic.settings.get_user_settings(user.id) == {
        "test": False,
        "other": None
    }
