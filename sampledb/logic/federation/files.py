import typing
import datetime

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_utc_datetime, _get_str, _get_dict
from .users import _parse_user_ref, _get_or_create_user_id, UserRef
from ..files import get_mutable_file, create_fed_file, hide_file, File
from ..components import Component
from .. import errors, fed_logs, object_log
from ..utils import parse_url
from ...models import Object
from ... import db


class FileHideData(typing.TypedDict):
    user: UserRef
    reason: str
    utc_datetime: datetime.datetime


class FileData(typing.TypedDict):
    fed_id: int
    component_uuid: str
    user: typing.Optional[UserRef]
    data: typing.Optional[typing.Dict[str, typing.Any]]
    utc_datetime: datetime.datetime
    hide: typing.Optional[FileHideData]


def parse_file(
        file_data: typing.Dict[str, typing.Any]
) -> FileData:
    uuid = _get_uuid(file_data.get('component_uuid'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError('Invalid update for local data')
    fed_id = _get_id(file_data.get('file_id'), min=0)
    data = _get_dict(file_data.get('data'))

    if data:
        storage = _get_str(data.get('storage'), mandatory=True)
        _get_str(data.get('original_file_name'))
        if storage == 'url':
            for key in data.keys():
                if key not in {'url', 'storage'}:
                    raise errors.InvalidDataExportError(f'Invalid data entry key \'{key}\' for file #{fed_id} @ {uuid}')
            url = _get_str(data.get('url'))
            if url:
                try:
                    parse_url(url)
                except errors.InvalidURLError:
                    raise errors.InvalidDataExportError(f'Invalid URL \'{url}\' for file #{fed_id} @ {uuid}')
                except errors.URLTooLongError:
                    raise errors.InvalidDataExportError(f'URL \'{url}\' is too long for file #{fed_id} @ {uuid}')
                except errors.InvalidIPAddressError:
                    raise errors.InvalidDataExportError(f'Invalid IP-address in URL \'{url}\' for file #{fed_id} @ {uuid}')
                except errors.InvalidPortNumberError:
                    raise errors.InvalidDataExportError(f'Invalid port number in URL \'{url}\' for file #{fed_id} @ {uuid}')
        elif storage == 'federation':
            for key in data.keys():
                if key not in {'original_file_name', 'storage', 'hash'}:
                    raise errors.InvalidDataExportError(f'Invalid data entry key \'{key}\' for file #{fed_id} @ {uuid}')
        else:
            raise errors.InvalidDataExportError(f'Invalid storage type \'{storage}\' for file #{fed_id} @ {uuid}')

    hidden_data = _get_dict(file_data.get('hidden'), default=None)
    if data is None and hidden_data is None:
        raise errors.InvalidDataExportError(f'Missing data for file #{fed_id} @ {uuid}')

    if hidden_data is not None:
        hide = FileHideData(
            user=_parse_user_ref(_get_dict(hidden_data.get('user'), mandatory=True)),
            reason=_get_str(hidden_data.get('reason'), default=''),
            utc_datetime=_get_utc_datetime(hidden_data.get('utc_datetime'), default=datetime.datetime.now(datetime.timezone.utc))
        )
    else:
        hide = None

    return FileData(
        fed_id=fed_id,
        component_uuid=_get_uuid(file_data.get('component_uuid')),
        user=_parse_user_ref(_get_dict(file_data.get('user'))),
        data=data,
        utc_datetime=_get_utc_datetime(file_data.get('utc_datetime'), mandatory=True),
        hide=hide
    )


def import_file(
        file_data: FileData,
        object: Object,
        component: Component
) -> File:
    component_id = _get_or_create_component_id(file_data['component_uuid'])
    user_id = _get_or_create_user_id(file_data['user'])

    try:
        db_file = get_mutable_file(file_data['fed_id'], object.id, component_id)
        if db_file.user_id != user_id or db_file.data != file_data['data'] or db_file.utc_datetime != file_data['utc_datetime']:
            db_file.user_id = user_id
            db_file.data = file_data['data']
            db_file.utc_datetime = file_data['utc_datetime']
            db.session.commit()
            fed_logs.update_file(db_file.id, object.object_id, component.id)
    except errors.FileDoesNotExistError:
        assert component_id is not None
        db_file = create_fed_file(object.object_id, user_id, file_data['data'], None, file_data['utc_datetime'], file_data['fed_id'], component_id)
        fed_logs.import_file(db_file.id, db_file.object_id, component.id)
        if user_id is not None:
            object_log.upload_file(user_id=user_id, object_id=object.object_id, file_id=db_file.id, utc_datetime=file_data['utc_datetime'], is_imported=True)

    file = File.from_database(db_file)
    if file_data['hide'] is not None and not file.is_hidden:
        hide_user = _get_or_create_user_id(file_data['hide']['user'])
        hide_file(
            object_id=file.object_id,
            file_id=file.id,
            user_id=hide_user,
            reason=file_data['hide']['reason'],
            utc_datetime=file_data['hide']['utc_datetime']
        )
    return file


def parse_import_file(
        file_data: typing.Dict[str, typing.Any],
        object: Object,
        component: Component
) -> File:
    return import_file(parse_file(file_data), object, component)
