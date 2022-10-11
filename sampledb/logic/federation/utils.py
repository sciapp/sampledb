from datetime import datetime, timedelta
import typing

import flask
from uuid import UUID

from .. import errors


@typing.overload
def _get_id(
        id: typing.Any,
        *,
        min: int = 1,
        special_values: typing.Optional[typing.List[int]] = None,
        convert: bool = True,
        default: int,
        mandatory: bool = True,
) -> int:
    ...


@typing.overload
def _get_id(
        id: typing.Any,
        *,
        min: int = 1,
        special_values: typing.Optional[typing.List[int]] = None,
        convert: bool = True,
        default: typing.Optional[int] = None,
        mandatory: typing.Literal[True] = True
) -> int:
    ...


@typing.overload
def _get_id(
        id: typing.Any,
        *,
        min: int = 1,
        special_values: typing.Optional[typing.List[int]] = None,
        convert: bool = True,
        default: typing.Optional[int] = None,
        mandatory: bool = True
) -> typing.Optional[int]:
    ...


def _get_id(
        id: typing.Any,
        *,
        min: int = 1,
        special_values: typing.Optional[typing.List[int]] = None,
        convert: bool = True,
        default: typing.Optional[int] = None,
        mandatory: bool = True
) -> typing.Optional[int]:
    if id is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing ID')
        return default
    if type(id) is not int:
        if convert:
            try:
                id = int(id)
                # mypy type narrowing
                assert type(id) is int
            except ValueError:
                raise errors.InvalidDataExportError('ID "{}" could not be converted to an integer'.format(id))
        else:
            raise errors.InvalidDataExportError('ID "{}" is not an integer'.format(id))
    if min is not None and id < min:
        if special_values is not None and id in special_values:
            return id
        raise errors.InvalidDataExportError('Invalid ID "{}". Has to be greater than {}. Allowed special values: {}'.format(id, min, special_values))
    return id


@typing.overload
def _get_uuid(
        uuid: typing.Any,
        *,
        default: str,
        mandatory: bool = True
) -> str:
    ...


@typing.overload
def _get_uuid(
        uuid: typing.Any,
        *,
        default: typing.Optional[str] = None,
        mandatory: typing.Literal[True] = True
) -> str:
    ...


@typing.overload
def _get_uuid(
        uuid: typing.Any,
        *,
        default: typing.Optional[str] = None,
        mandatory: bool = True
) -> typing.Optional[str]:
    ...


def _get_uuid(
        uuid: typing.Any,
        *,
        default: typing.Optional[str] = None,
        mandatory: bool = True
) -> typing.Optional[str]:
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


@typing.overload
def _get_bool(
        bool_in: typing.Any,
        *,
        default: bool,
        mandatory: bool = False
) -> bool:
    ...


@typing.overload
def _get_bool(
        bool_in: typing.Any,
        *,
        default: typing.Optional[bool] = None,
        mandatory: typing.Literal[True]
) -> bool:
    ...


@typing.overload
def _get_bool(
        bool_in: typing.Any,
        *,
        default: typing.Optional[bool] = None,
        mandatory: bool = False
) -> typing.Optional[bool]:
    ...


def _get_bool(
        bool_in: typing.Any,
        *,
        default: typing.Optional[bool] = None,
        mandatory: bool = False
) -> typing.Optional[bool]:
    if bool_in is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing boolean')
        return default
    if type(bool_in) is not bool:
        raise errors.InvalidDataExportError('Invalid boolean "{}"'.format(bool_in))
    return bool_in


def _get_translation(
        translation: typing.Any,
        *,
        default: typing.Optional[typing.Dict[str, str]] = None,
        mandatory: bool = False
) -> typing.Optional[typing.Dict[str, str]]:
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


@typing.overload
def _get_dict(
        dict_in: typing.Any,
        *,
        default: typing.Dict[typing.Any, typing.Any],
        mandatory: bool = False
) -> typing.Dict[typing.Any, typing.Any]:
    ...


@typing.overload
def _get_dict(
        dict_in: typing.Any,
        *,
        default: None = None,
        mandatory: typing.Literal[True] = True
) -> typing.Dict[typing.Any, typing.Any]:
    ...


@typing.overload
def _get_dict(
        dict_in: typing.Any,
        *,
        default: None = None,
        mandatory: bool = False
) -> typing.Optional[typing.Dict[typing.Any, typing.Any]]:
    ...


def _get_dict(
        dict_in: typing.Any,
        *,
        default: typing.Optional[typing.Dict[typing.Any, typing.Any]] = None,
        mandatory: bool = False
) -> typing.Optional[typing.Dict[typing.Any, typing.Any]]:
    if dict_in is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing dict')
        return default
    if not isinstance(dict_in, dict):
        raise errors.InvalidDataExportError('Invalid dict "{}"'.format(dict_in))
    return dict_in


def _get_permissions(
        permissions_in: typing.Any,
        *,
        default: typing.Optional[typing.Dict[str, typing.Union[str, typing.Dict[int, str]]]] = None
) -> typing.Optional[typing.Dict[str, typing.Union[str, typing.Dict[int, str]]]]:
    if permissions_in is None:
        return default
    permissions = _get_dict(permissions_in, mandatory=True)
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


@typing.overload
def _get_list(
        list_in: typing.Any,
        *,
        default: typing.List[typing.Any],
        mandatory: bool = False
) -> typing.List[typing.Any]:
    ...


@typing.overload
def _get_list(
        list_in: typing.Any,
        *,
        default: typing.Optional[typing.List[typing.Any]] = None,
        mandatory: typing.Literal[True]
) -> typing.List[typing.Any]:
    ...


@typing.overload
def _get_list(
        list_in: typing.Any,
        *,
        default: typing.Optional[typing.List[typing.Any]] = None,
        mandatory: bool = False
) -> typing.Optional[typing.List[typing.Any]]:
    ...


def _get_list(
        list_in: typing.Any,
        *,
        default: typing.Optional[typing.List[typing.Any]] = None,
        mandatory: bool = False
) -> typing.Optional[typing.List[typing.Any]]:
    if list_in is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing list')
        return default
    if not isinstance(list_in, list):
        raise errors.InvalidDataExportError('Invalid list "{}"'.format(list_in))
    return list_in


@typing.overload
def _get_str(
        str_in: typing.Any,
        *,
        default: str,
        mandatory: bool = False,
        allow_empty: bool = True,
        convert: bool = False
) -> str:
    ...


@typing.overload
def _get_str(
        str_in: typing.Any,
        *,
        default: typing.Optional[str] = None,
        mandatory: typing.Literal[True],
        allow_empty: bool = True,
        convert: bool = False
) -> str:
    ...


@typing.overload
def _get_str(
        str_in: typing.Any,
        *,
        default: typing.Optional[str] = None,
        mandatory: bool = False,
        allow_empty: bool = True,
        convert: bool = False
) -> typing.Optional[str]:
    ...


def _get_str(
        str_in: typing.Any,
        *,
        default: typing.Optional[str] = None,
        mandatory: bool = False,
        allow_empty: bool = True,
        convert: bool = False
) -> typing.Optional[str]:
    if str_in is None:
        if mandatory:
            raise errors.InvalidDataExportError('Missing string')
        return default
    if type(str_in) is not str:
        if not convert:
            raise errors.InvalidDataExportError('"{}" is not a string'.format(str_in))
        try:
            str_in = str(str_in)
            # mypy type narrowing
            assert type(str_in) is str
        except ValueError:
            raise errors.InvalidDataExportError('Cannot convert "{}" to string'.format(str_in))
    if not allow_empty and str_in == '':
        raise errors.InvalidDataExportError('Empty string')
    return str_in


@typing.overload
def _get_utc_datetime(
        utc_datetime_str: typing.Any,
        *,
        default: datetime,
        mandatory: bool = False
) -> datetime:
    ...


@typing.overload
def _get_utc_datetime(
        utc_datetime_str: typing.Any,
        *,
        default: typing.Optional[datetime] = None,
        mandatory: typing.Literal[True]
) -> datetime:
    ...


@typing.overload
def _get_utc_datetime(
        utc_datetime_str: typing.Any,
        *,
        default: typing.Optional[datetime] = None,
        mandatory: bool = False
) -> typing.Optional[datetime]:
    ...


def _get_utc_datetime(
        utc_datetime_str: typing.Any,
        *,
        default: typing.Optional[datetime] = None,
        mandatory: bool = False
) -> typing.Optional[datetime]:
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
