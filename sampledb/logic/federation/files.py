from datetime import datetime

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_utc_datetime, _get_str, _get_dict
from .users import _parse_user_ref, _get_or_create_user_id
from ..files import get_file, create_fed_file, hide_file, File
from .. import errors, fed_logs
from ... import db


def parse_file(file_data):
    uuid = _get_uuid(file_data.get('component_uuid'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError('Invalid update for local data')
    fed_id = _get_id(file_data.get('file_id'), min=0)
    data = _get_dict(file_data.get('data'))

    hidden_data = _get_dict(file_data.get('hidden'), default=None)
    if data is None and hidden_data is None:
        raise errors.InvalidDataExportError('Missing data for file #{} @ {}'.format(fed_id, uuid))

    hide = {}
    if hidden_data is not None:
        hide['user'] = _parse_user_ref(_get_dict(hidden_data.get('user')))
        hide['reason'] = _get_str(hidden_data.get('reason'), default='')
        hide['utc_datetime'] = _get_utc_datetime(hidden_data.get('utc_datetime'), default=datetime.utcnow())

    return {
        'fed_id': fed_id,
        'component_uuid': _get_uuid(file_data.get('component_uuid')),
        'user': _parse_user_ref(_get_dict(file_data.get('user'))),
        'data': data,
        'utc_datetime': _get_utc_datetime(file_data.get('utc_datetime'), mandatory=True),
        'hide': hide
    }


def import_file(file_data, object, component):
    component_id = _get_or_create_component_id(file_data['component_uuid'])
    user_id = _get_or_create_user_id(file_data['user'])

    try:
        db_file = get_file(file_data['fed_id'], object.id, component_id, get_db_file=True)
        if db_file.user_id != user_id or db_file.data != file_data['data'] or db_file.utc_datetime != file_data['utc_datetime']:
            db_file.user_id = user_id
            db_file.data = file_data['data']
            db_file.utc_datetime = file_data['utc_datetime']
            db.session.commit()
            fed_logs.update_file(db_file.id, object.object_id, component.id)

    except errors.FileDoesNotExistError:
        db_file = create_fed_file(object.object_id, user_id, file_data['data'], None, file_data['utc_datetime'], file_data['fed_id'], component_id)
        fed_logs.import_file(db_file.id, db_file.object_id, component.id)

    file = File.from_database(db_file)
    if file_data['hide'] != {} and not file.is_hidden:
        hide_user = _get_or_create_user_id(file_data['hide']['user'])
        hide_file(file.object_id, file.id, hide_user, file_data['hide']['reason'], file_data['hide']['utc_datetime'])
    return file


def parse_import_file(file_data, object, component):
    return import_file(parse_file(file_data), object, component)
