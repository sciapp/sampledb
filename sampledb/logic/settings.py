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
from . import users


DEFAULT_SETTINGS: typing.Dict[str, typing.Any] = {
    "OBJECTS_PER_PAGE": 25,
    "USE_SCHEMA_EDITOR": True,
    "SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE": None,
    "SHOW_OBJECT_TITLE": None,
    "FULL_WIDTH_OBJECTS_TABLE": None,
    "WORKFLOW_VIEW_MODALS": None,
    "WORKFLOW_VIEW_COLLAPSED": None,
    "USE_ADMIN_PERMISSIONS": False,
    "SHOW_INVITATION_LOG": False,
    "SHOW_HIDDEN_USERS_AS_ADMIN": True,
    "INSTRUMENT_LOG_ORDER_ASCENDING": True,
    "INSTRUMENT_LOG_ORDER_ATTRIBUTE": "datetime",
    "DATAVERSE_API_TOKEN": "",
    "SCICAT_API_TOKEN": "",
    "DEFAULT_INSTRUMENT_LIST_FILTERS": {},
    "DEFAULT_ACTION_LIST_FILTERS": {},
    "DEFAULT_OBJECT_LIST_FILTERS": {},
    "DEFAULT_OBJECT_LIST_OPTIONS": {},
    "DEFAULT_LOCATION_LIST_FILTERS": {},
    "AUTO_LC": True,
    "TIMEZONE": "UTC",
    "AUTO_TZ": True,
    "LOCALE": "en"
}


def get_user_settings(
        user_id: typing.Optional[int]
) -> typing.Dict[str, typing.Any]:
    """
    Get the settings for a user.

    This function will amend the user's settings with the default settings,
    so that code can rely on settings being available.

    :param user_id: the ID of an existing user, or None
    :return: the settings data
    :raise errors.UserDoesNotExistError: if the user does not exist
    """
    verified_data = copy.deepcopy(DEFAULT_SETTINGS)
    if user_id is None:
        return verified_data
    # ensure the user exists
    users.check_user_exists(user_id)
    settings = Settings.query.filter_by(user_id=user_id).first()
    if settings is not None:
        verified_data.update(_verify_settings(settings.data))
    return verified_data


def get_user_setting(
        user_id: typing.Optional[int],
        setting_name: str
) -> typing.Any:
    """
    Get a specific setting for a user.

    This function will return the default value for the setting, if the user's
    settings do not include it.

    :param user_id: the ID of an existing user, or None
    :param setting_name: the name of a setting
    :return: the settings data
    :raise errors.UserDoesNotExistError: if the user does not exist
    """
    default_value = copy.deepcopy(DEFAULT_SETTINGS.get(setting_name))
    if user_id is None:
        return default_value
    # ensure the user exists
    users.get_user(user_id)
    row: typing.Optional[typing.Tuple[typing.Any]] = db.session.query(Settings.data[setting_name]).filter(Settings.user_id == user_id).first()
    if row is not None and _verify_setting(setting_name, row[0]):
        return row[0]
    return default_value


def set_user_settings(user_id: int, data: typing.Dict[str, typing.Any]) -> None:
    """
    Set new settings for a user.

    This function will keep a user's previous settings if not overwritten.

    :param user_id: the ID of an existing user
    :param data: the settings data
    :raise errors.UserDoesNotExistError: if the user does not exist
    """
    # ensure the user exists
    users.check_user_exists(user_id)
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
    if key in {'SHOW_OBJECT_TITLE', 'SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE', 'FULL_WIDTH_OBJECTS_TABLE', 'WORKFLOW_VIEW_MODALS', 'WORKFLOW_VIEW_COLLAPSED'}:
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
