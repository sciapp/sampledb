from datetime import datetime, timedelta
import typing

import flask
from uuid import UUID

from .. import errors


def _get_id(id, min=1, special_values: typing.Optional[typing.List[int]] = None, convert=True, default=None, mandatory=True) -> typing.Optional[int]:
    if id is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing ID')
        return default
    if type(id) is not int:
        if convert:
            try:
                id = int(id)
            except ValueError:
                raise errors.InvalidDataExportError('ID "{}" could not be converted to an integer'.format(id))
        else:
            raise errors.InvalidDataExportError('ID "{}" is not an integer'.format(id))
    if min is not None and id < min:
        if special_values is not None and id in special_values:
            return id
        raise errors.InvalidDataExportError('Invalid ID "{}". Has to be greater than {}. Allowed special values: {}'.format(id, min, special_values))
    return id


def _get_uuid(uuid, default=None, mandatory=True) -> typing.Optional[str]:
    if uuid is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing UUID')
        return default
    if type(uuid) is not str:
        raise errors.InvalidDataExportError('UUID "{}" is not a string'.format(uuid))
    try:
        uuid_obj = UUID(uuid)
        return str(uuid_obj)
    except ValueError:
        raise errors.InvalidDataExportError('Invalid UUID "{}"'.format(uuid))
    except TypeError:
        raise errors.InvalidDataExportError('Invalid UUID "{}"'.format(uuid))


def _get_bool(bool_in, default=None, mandatory=False) -> typing.Optional[bool]:
    if bool_in is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing boolean')
        return default
    if type(bool_in) is not bool:
        raise errors.InvalidDataExportError('Invalid boolean "{}"'.format(bool_in))
    return bool_in


def _get_translation(translation, default=None, mandatory=False):
    if translation is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing text')
        return default
    if isinstance(translation, dict):
        for key, item in translation.items():
            if type(key) is not str or type(item) is not str or key == '':
                raise errors.InvalidDataExportError('Invalid translation dict "{}"'.format(translation))
        return translation
    if type(translation) is not str:
        raise errors.InvalidDataExportError('Text is neither a dictionary nor string "{}"'.format(translation))
    return {'en': translation}


def _get_dict(dict_in, default=None, mandatory=False) -> typing.Optional[dict]:
    if dict_in is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing dict')
        return default
    if not isinstance(dict_in, dict):
        raise errors.InvalidDataExportError('Invalid dict "{}"'.format(dict_in))
    return dict_in


def _get_permissions(permissions, default=None):
    if permissions is None:
        return default
    _get_dict(permissions)
    users = _get_dict(permissions.get('users'), default={})
    groups = _get_dict(permissions.get('groups'), default={})
    projects = _get_dict(permissions.get('projects'), default={})
    _get_str(permissions.get('all_users'), default='none')
    for id, perm in users.items():
        _get_id(id, mandatory=True)
        _get_str(perm, mandatory=True)
    for id, perm in groups.items():
        _get_id(id, mandatory=True)
        _get_str(perm, mandatory=True)
    for id, perm in projects.items():
        _get_id(id, mandatory=True)
        _get_str(perm, mandatory=True)
    return permissions


def _get_list(list_in, default=None, mandatory=False) -> typing.Optional[list]:
    if list_in is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing list')
        return default
    if not isinstance(list_in, list):
        raise errors.InvalidDataExportError('Invalid list "{}"'.format(list_in))
    return list_in


def _get_str(str_in, default=None, mandatory=False, allow_empty=True, convert=False) -> typing.Optional[str]:
    if str_in is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing string')
        return default
    if type(str_in) is not str:
        if not convert:
            raise errors.InvalidDataExportError('"{}" is not a string'.format(str_in))
        try:
            str_in = str(str_in)
        except ValueError:
            raise errors.InvalidDataExportError('Cannot convert "{}" to string'.format(str_in))
    if not allow_empty and str_in == '':
        raise errors.InvalidDataExportError('Empty string')
    return str_in


def _get_utc_datetime(utc_datetime_str, default=None, mandatory=False) -> typing.Optional[datetime]:
    if utc_datetime_str is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing timestamp')
        return default
    try:
        dt = datetime.strptime(utc_datetime_str, '%Y-%m-%d %H:%M:%S.%f')
        if dt > datetime.utcnow() + timedelta(seconds=flask.current_app.config['VALID_TIME_DELTA']):
            raise errors.InvalidDataExportError('Timestamp is in the future "{}"'.format(dt))
        return dt
    except ValueError:
        raise errors.InvalidDataExportError('Invalid timestamp "{}"'.format(utc_datetime_str))
    except TypeError:
        raise errors.InvalidDataExportError('Invalid timestamp "{}"'.format(utc_datetime_str))
