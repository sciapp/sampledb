# coding: utf-8
"""

"""
import copy

import pytest
import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def user():
    user = sampledb.models.User(
        name="User",
        email="example1@example.com",
        type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return user

@pytest.fixture
def default_settings():
    default_settings = copy.deepcopy(sampledb.logic.settings.DEFAULT_SETTINGS)
    yield sampledb.logic.settings.DEFAULT_SETTINGS
    sampledb.logic.settings.DEFAULT_SETTINGS = default_settings


def test_get_default_settings(user, default_settings):
    sampledb.logic.settings.DEFAULT_SETTINGS = {
        "test": True
    }
    assert sampledb.logic.settings.get_user_settings(user.id) == {
        "test": True
    }


def test_set_settings(user, default_settings):
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


def test_set_invalid_settings(user, default_settings):
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


def test_set_custom_settings(user, default_settings):
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


def test_get_user_settings(user, default_settings):
    sampledb.logic.settings.DEFAULT_SETTINGS = {
        "test": True
    }
    assert sampledb.logic.settings.get_user_setting(user.id, "test")
    sampledb.logic.settings.set_user_settings(user.id, {
        "test": False
    })
    assert not sampledb.logic.settings.get_user_setting(user.id, "test")
    assert sampledb.logic.settings.get_user_setting(user.id, "other") is None
