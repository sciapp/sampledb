# coding: utf-8
"""
Logic module handling communication with other components in a SampleDB federation
"""
from datetime import datetime

import requests
import flask

from .. import errors
from ..component_authentication import get_own_authentication
from ...models import ComponentAuthenticationType

from .utils import _get_id, _get_uuid, _get_bool, _get_str, _get_dict, _get_list, _get_utc_datetime, _get_translation, _get_permissions
from .components import _get_or_create_component_id
from .users import import_user, parse_import_user, parse_user, _parse_user_ref, _get_or_create_user_id, shared_user_preprocessor
from .location_types import import_location_type, parse_import_location_type, parse_location_type, _parse_location_type_ref, _get_or_create_location_type_id, shared_location_type_preprocessor
from .instruments import import_instrument, parse_instrument, parse_import_instrument, _parse_instrument_ref, _get_or_create_instrument_id, shared_instrument_preprocessor
from .action_types import import_action_type, parse_action_type, parse_import_action_type, _parse_action_type_ref, _get_or_create_action_type_id, shared_action_type_preprocessor
from .locations import import_location, parse_location, parse_import_location, _get_or_create_location_id, _parse_location_ref, shared_location_preprocessor, locations_check_for_cyclic_dependencies
from .markdown_images import parse_markdown_image, import_markdown_image, parse_import_markdown_image
from .actions import import_action, parse_action, parse_import_action, _parse_action_ref, _get_or_create_action_id, shared_action_preprocessor, schema_entry_preprocessor, _parse_schema
from .comments import import_comment, parse_comment, parse_import_comment
from .files import import_file, parse_file, parse_import_file
from .object_location_assignments import import_object_location_assignment, parse_object_location_assignment, parse_import_object_location_assignment
from .objects import import_object, parse_object, parse_import_object


PROTOCOL_VERSION_MAJOR = 0
PROTOCOL_VERSION_MINOR = 1


def post(endpoint, component, payload=None, headers=None):
    if component.address is None:
        raise errors.MissingComponentAddressError()
    if headers is None:
        headers = {}
    auth = get_own_authentication(component.id, ComponentAuthenticationType.TOKEN)

    if auth:
        headers['Authorization'] = 'Bearer ' + auth.login['token']
    requests.post(component.address.rstrip('/') + endpoint, data=payload, headers=headers)


def get(endpoint, component, headers=None):
    if component.address is None:
        raise errors.MissingComponentAddressError()
    if headers is None:
        headers = {}
    auth = get_own_authentication(component.id, ComponentAuthenticationType.TOKEN)

    if auth:
        headers['Authorization'] = 'Bearer ' + auth.login['token']

    parameters = {}
    if component.last_sync_timestamp is not None:
        parameters['last_sync_timestamp'] = component.last_sync_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
    req = requests.get(component.address.rstrip('/') + endpoint, headers=headers, params=parameters)
    if req.status_code == 401:
        # 401 Unauthorized
        raise errors.UnauthorizedRequestError()
    if req.status_code in [500, 501, 502, 503, 504]:
        raise errors.RequestServerError()
    try:
        return req.json()
    except ValueError:
        raise errors.InvalidJSONError()


def update_poke_component(component):
    post('/federation/v1/hooks/update/', component)


def _validate_header(header, component):
    if header is not None:
        if header.get('db_uuid') != component.uuid:
            raise errors.InvalidDataExportError('UUID of exporting database ({}) does not match expected UUID ({}).'.format(header.get('db_uuid'), component.uuid))
        if header.get('protocol_version') is not None:
            if header.get('protocol_version').get('major') is None or header.get('protocol_version').get('minor') is None:
                raise errors.InvalidDataExportError('Invalid protocol version \'{}\''.format(header.get('protocol_version')))
            try:
                major, minor = int(header.get('protocol_version').get('major')), int(header.get('protocol_version').get('minor'))
                if major > PROTOCOL_VERSION_MAJOR or (major <= PROTOCOL_VERSION_MAJOR and minor > PROTOCOL_VERSION_MINOR):
                    raise errors.InvalidDataExportError('Unsupported protocol version {}'.format(header.get('protocol_version')))
            except ValueError:
                raise errors.InvalidDataExportError('Invalid protocol version {}'.format(header.get('protocol_version')))
        else:
            raise errors.InvalidDataExportError('Missing protocol_version.')


def import_updates(component):
    if flask.current_app.config['FEDERATION_UUID'] is None:
        raise errors.ComponentNotConfiguredForFederationError()
    timestamp = datetime.utcnow()
    try:
        users = get('/federation/v1/shares/users/', component)
    except errors.InvalidJSONError:
        raise errors.InvalidDataExportError('Received an invalid JSON string.')
    except errors.RequestServerError:
        pass
    except errors.UnauthorizedRequestError:
        pass
    try:
        updates = get('/federation/v1/shares/objects/', component)
    except errors.InvalidJSONError:
        raise errors.InvalidDataExportError('Received an invalid JSON string.')
    update_users(component, users)
    update_shares(component, updates)
    component.update_last_sync_timestamp(timestamp)


def update_users(component, updates):
    _get_dict(updates, mandatory=True)
    _validate_header(updates.get('header'), component)

    users = []
    user_data_list = _get_list(updates.get('users'), default=[])
    for user_data in user_data_list:
        users.append(parse_user(user_data, component))
    for user_data in users:
        import_user(user_data, component)


def update_shares(component, updates):
    # parse and validate
    _get_dict(updates, mandatory=True)
    _validate_header(updates.get('header'), component)

    markdown_images = []
    markdown_images_data_dict = _get_dict(updates.get('markdown_images'), default={})
    for markdown_image_data in markdown_images_data_dict.items():
        markdown_images.append(parse_markdown_image(markdown_image_data, component))

    users = []
    user_data_list = _get_list(updates.get('users'), default=[])
    for user_data in user_data_list:
        users.append(parse_user(user_data, component))

    instruments = []
    instrument_data_list = _get_list(updates.get('instruments'), default=[])
    for instrument_data in instrument_data_list:
        instruments.append(parse_instrument(instrument_data))

    action_types = []
    action_type_data_list = _get_list(updates.get('action_types'), default=[])
    for action_type_data in action_type_data_list:
        action_types.append(parse_action_type(action_type_data))

    actions = []
    action_data_list = _get_list(updates.get('actions'), default=[])
    for action_data in action_data_list:
        actions.append(parse_action(action_data))

    location_types = []
    location_type_data_list = _get_list(updates.get('location_types'), default=[])
    for location_type_data in location_type_data_list:
        location_types.append(parse_location_type(location_type_data))

    locations = {}
    location_data_list = _get_list(updates.get('locations'), default=[])
    for location_data in location_data_list:
        location = parse_location(location_data)
        locations[(location['fed_id'], location['component_uuid'])] = location

    locations_check_for_cyclic_dependencies(locations)

    objects = []
    object_data_list = _get_list(updates.get('objects'), default=[])
    for object_data in object_data_list:
        objects.append(parse_object(object_data, component))

    # apply
    for markdown_image_data in markdown_images:
        import_markdown_image(markdown_image_data, component)

    for user_data in users:
        import_user(user_data, component)

    for instrument_data in instruments:
        import_instrument(instrument_data, component)

    for action_type_data in action_types:
        import_action_type(action_type_data, component)

    for action_data in actions:
        import_action(action_data, component)

    for location_type_data in location_types:
        import_location_type(location_type_data, component)

    while len(locations) > 0:
        key = list(locations)[0]
        import_location(locations[key], component, locations, users)
        if key in locations:
            locations.pop(key)

    for object_data in objects:
        import_object(object_data, component)
