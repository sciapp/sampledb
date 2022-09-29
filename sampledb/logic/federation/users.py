import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_str, _get_dict
from ..users import get_mutable_user, create_user, set_user_hidden, UserType, get_user, get_user_alias
from ..components import Component
from .. import errors, fed_logs
from ... import db


def import_user(user_data, component):
    component_id = _get_or_create_component_id(user_data['component_uuid'])
    try:
        user = get_mutable_user(user_data['fed_id'], component_id)
        if user.name != user_data['name'] or user.email != user_data['email'] or user.orcid != user_data['orcid'] or user.affiliation != user_data['affiliation'] or user.role != user_data['role'] or user.extra_fields != user_data['extra_fields']:
            user.name = user_data['name']
            user.email = user_data['email']
            user.orcid = user_data['orcid']
            user.affiliation = user_data['affiliation']
            user.role = user_data['role']
            user.extra_fields = user_data['extra_fields']
            db.session.add(user)
            db.session.commit()
            fed_logs.update_user(user.id, component.id)
    except errors.UserDoesNotExistError:
        user = create_user(
            fed_id=user_data['fed_id'],
            component_id=component_id,
            name=user_data['name'],
            email=user_data['email'],
            orcid=user_data['orcid'],
            affiliation=user_data['affiliation'],
            role=user_data['role'],
            extra_fields=user_data['extra_fields'],
            type=UserType.FEDERATION_USER
        )
        set_user_hidden(user.id, True)
        fed_logs.import_user(user.id, component.id)
    return user


def parse_import_user(user_data, component):
    return import_user(parse_user(user_data, component), component)


def parse_user(user_data, component):
    uuid = _get_uuid(user_data.get('component_uuid'))
    fed_id = _get_id(user_data.get('user_id'))
    if uuid != component.uuid:
        # only accept user data from original source
        raise errors.InvalidDataExportError('User data update for user #{} @ {}'.format(fed_id, uuid))
    return {
        'fed_id': fed_id,
        'component_uuid': uuid,
        'name': _get_str(user_data.get('name')),
        'email': _get_str(user_data.get('email')),
        'orcid': _get_str(user_data.get('orcid')),
        'affiliation': _get_str(user_data.get('affiliation')),
        'role': _get_str(user_data.get('role')),
        'extra_fields': _get_dict(user_data.get('extra_fields'), default={})
    }


def _parse_user_ref(user_data):
    if user_data is None:
        return None
    user_id = _get_id(user_data.get('user_id'))
    component_uuid = _get_uuid(user_data.get('component_uuid'))
    return {'user_id': user_id, 'component_uuid': component_uuid}


def _get_or_create_user_id(user_data):
    if user_data is None:
        return None
    component_id = _get_or_create_component_id(user_data['component_uuid'])
    try:
        user = get_user(user_data['user_id'], component_id)
    except errors.UserDoesNotExistError:
        user = create_user(name=None, email=None, fed_id=user_data['user_id'], component_id=component_id, type=UserType.FEDERATION_USER)
        set_user_hidden(user.id, True)
        fed_logs.create_ref_user(user.id, component_id)
    return user.id


def shared_user_preprocessor(user_id: int, component: Component, _refs: list, _markdown_images):
    user = get_user(user_id)
    if user.component_id is not None:
        return None
    try:
        alias = get_user_alias(user_id, component.id)
        return {
            'user_id': user.id,
            'component_uuid': flask.current_app.config['FEDERATION_UUID'],
            'name': alias.name,
            'email': alias.email,
            'orcid': alias.orcid,
            'affiliation': alias.affiliation,
            'role': alias.role,
            'extra_fields': alias.extra_fields
        }
    except errors.UserAliasDoesNotExistError:
        return {
            'user_id': user.id,
            'component_uuid': flask.current_app.config['FEDERATION_UUID'],
            'name': None, 'email': None, 'orcid': None, 'affiliation': None, 'role': None, 'extra_fields': {}
        }
