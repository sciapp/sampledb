# coding: utf-8
"""
Settings logic.

This module implements the logic for reading and writing user settings using
the generic Settings model.
In addition to providing the basics for accessing arbitrary JSON-compatible
settings, this module also implements which actual settings exist and that
the user's settings contain the correct data types. These are defined using
the DEFAULT_SETTINGS global variable, which contains the default value for
each setting. If there is no default value for a setting, DEFAULT_SETTINGS
should contain None for it and code for data type verification needs to be
added to `_verify_setting`.
"""

import copy
import typing

from .. import db
from ..models import Settings
from .users import get_user


DEFAULT_SETTINGS = {
    "OBJECTS_PER_PAGE": 25,
    "USE_SCHEMA_EDITOR": True,
    "SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE": None,
    "SHOW_OBJECT_TITLE": None,
    "USE_ADMIN_PERMISSIONS": False,
    "SHOW_INVITATION_LOG": False,
    "INSTRUMENT_LOG_ORDER_ASCENDING": True,
    "INSTRUMENT_LOG_ORDER_ATTRIBUTE": "datetime",
    "DATAVERSE_API_TOKEN": "",
    "AUTO_LC": True,
    "TIMEZONE": "UTC",
    "AUTO_TZ": True,
    "LOCALE": "en"
}


def get_user_settings(user_id: int) -> typing.Dict[str, typing.Any]:
    """
    Get the settings for a user.

    This function will amend the user's settings with the default settings,
    so that code can rely on settings being available.

    :param user_id: the ID of an existing user
    :return: the settings data
    :raise errors.UserDoesNotExistError: if the user does not exist
    """
    # ensure the user exists
    get_user(user_id)
    verified_data = copy.deepcopy(DEFAULT_SETTINGS)
    settings = Settings.query.filter_by(user_id=user_id).first()
    if settings is not None:
        verified_data.update(_verify_settings(settings.data))
    return verified_data


def set_user_settings(user_id: int, data: typing.Dict[str, typing.Any]) -> None:
    """
    Set new settings for a user.

    This function will keep a user's previous settings if not overwritten.

    :param user_id: the ID of an existing user
    :param data: the settings data
    :raise errors.UserDoesNotExistError: if the user does not exist
    """
    # ensure the user exists
    get_user(user_id)
    settings = Settings.query.filter_by(user_id=user_id).first()
    if settings is None:
        verified_data = {}
        settings = Settings(user_id, {})
    else:
        verified_data = _verify_settings(settings.data)
    verified_data.update(_verify_settings(data))
    settings.data = verified_data
    db.session.add(settings)
    db.session.commit()


def _verify_setting(key: str, value: typing.Any) -> bool:
    """
    Verify the value of an individual setting.

    :param key: the name of the setting
    :param value: the value of the setting
    :return: True, if the value is valid, False otherwise
    """
    if key not in DEFAULT_SETTINGS:
        return False
    default_value = DEFAULT_SETTINGS[key]
    if default_value is not None:
        if value is None:
            # settings that accept None must be listed here
            return key in {'OBJECTS_PER_PAGE'}
        return isinstance(value, type(default_value))
    # custom data type verification can be included here
    if key in {'SHOW_OBJECT_TITLE', 'SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE'}:
        return value is None or isinstance(value, bool)
    return False


def _verify_settings(data: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
    """
    Verify a dictionary of settings.

    :param data: the unverified settings data
    :return: the verified settings data, omitting any invalid settings
    """
    verified_data = {}
    for key, value in data.items():
        if _verify_setting(key, value):
            verified_data[key] = copy.deepcopy(value)
    return verified_data
