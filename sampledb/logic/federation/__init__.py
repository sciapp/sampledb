# coding: utf-8
"""
Logic module handling communication with other components in a SampleDB federation
"""
import base64
from datetime import datetime

import requests
import flask

from ..action_translations import set_action_translation, get_action_translations_for_action
from ..files import create_fed_file, get_file, get_files_for_object, hide_file, File
from ..languages import get_languages, get_language_by_lang_code, get_language
from ..markdown_images import find_referenced_markdown_images, get_markdown_image
from ..object_permissions import set_user_object_permissions, set_group_object_permissions, set_project_object_permissions, set_object_permissions_for_all_users, object_permissions
from ..schemas import validate_schema, validate
from ... import db
from .. import errors, fed_logs, languages, markdown_to_html
from ..actions import get_action, create_action, get_mutable_action
from ..component_authentication import get_own_authentication
from ..comments import get_comment, get_comments_for_object, create_comment, update_comment
from ..components import get_component_by_uuid, get_component
from ..groups import get_group
from ..instruments import get_instrument
from ..locations import create_fed_assignment, get_fed_object_location_assignment, get_location, get_object_location_assignments
from ..objects import get_fed_object, get_object, update_object_version, insert_fed_object_version, get_object_versions
from ..projects import get_project
from ..users import get_user
from ...models import Permissions, ComponentAuthenticationType, Component
from ...models.file_log import FileLogEntry, FileLogEntryType

from .utils import _get_id, _get_uuid, _get_bool, _get_str, _get_dict, _get_list, _get_utc_datetime, _get_translation, _get_permissions
from .components import _get_or_create_component_id
from .users import import_user, parse_import_user, parse_user, _parse_user_ref, _get_or_create_user_id, shared_user_preprocessor
from .location_types import import_location_type, parse_import_location_type, parse_location_type, _parse_location_type_ref, _get_or_create_location_type_id, shared_location_type_preprocessor
from .instruments import import_instrument, parse_instrument, parse_import_instrument, _parse_instrument_ref, _get_or_create_instrument_id, shared_instrument_preprocessor
from .action_types import import_action_type, parse_action_type, parse_import_action_type, _parse_action_type_ref, _get_or_create_action_type_id, shared_action_type_preprocessor
from .locations import import_location, parse_location, parse_import_location, _get_or_create_location_id, _parse_location_ref, shared_location_preprocessor, locations_check_for_cyclic_dependencies
from .markdown_images import parse_markdown_image, import_markdown_image, parse_import_markdown_image

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


def import_object(object_data, component):
    action_id = _get_or_create_action_id(object_data['action'])
    for version in object_data['versions']:
        try:
            object = get_fed_object(object_data['fed_object_id'], component.id, version['fed_version_id'])
        except errors.ObjectDoesNotExistError:
            object = None
        except errors.ObjectVersionDoesNotExistError:
            object = None

        user_id = _get_or_create_user_id(version['user'])

        if object is None:
            object = insert_fed_object_version(
                fed_object_id=object_data['fed_object_id'],
                fed_version_id=version['fed_version_id'],
                component_id=component.id,
                data=version['data'],
                schema=version['schema'],
                user_id=user_id,
                action_id=action_id,
                utc_datetime=version['utc_datetime'],
                allow_disabled_languages=True
            )
            fed_logs.import_object(object.id, component.id)
        elif object.schema != version['schema'] or object.data != version['data'] or object.user_id != user_id or object.action_id != action_id or object.utc_datetime != version['utc_datetime']:
            object = update_object_version(
                object_id=object.object_id,
                version_id=object.version_id,
                data=version['data'],
                schema=version['schema'],
                user_id=user_id,
                action_id=action_id,
                utc_datetime=version['utc_datetime'],
                allow_disabled_languages=True
            )
            fed_logs.update_object(object.id, component.id)

    for comment_data in object_data['comments']:
        import_comment(comment_data, object, component)

    for file_data in object_data['files']:
        import_file(file_data, object, component)

    for assignment_data in object_data['object_location_assignments']:
        import_object_location_assignment(assignment_data, object, component)

    # apply policy permissions as a minimum, but do not reduce existing permissions
    current_permissions_for_users = object_permissions.get_permissions_for_users(resource_id=object.object_id)
    for user_id, permission in object_data['permissions']['users'].items():
        if permission not in current_permissions_for_users.get(user_id, Permissions.NONE):
            set_user_object_permissions(object.object_id, user_id, permission)

    current_permissions_for_groups = object_permissions.get_permissions_for_groups(resource_id=object.object_id)
    for group_id, permission in object_data['permissions']['groups'].items():
        if permission not in current_permissions_for_groups.get(group_id, Permissions.NONE):
            set_group_object_permissions(object.object_id, group_id, permission)

    current_permissions_for_projects = object_permissions.get_permissions_for_projects(resource_id=object.object_id)
    for project_id, permission in object_data['permissions']['projects'].items():
        if permission not in current_permissions_for_projects.get(project_id, Permissions.NONE):
            set_project_object_permissions(object.object_id, project_id, permission)

    current_permissions_for_all_users = object_permissions.get_permissions_for_all_users(resource_id=object.object_id)
    permission = object_data['permissions']['all_users']
    if permission not in current_permissions_for_all_users:
        set_object_permissions_for_all_users(object.object_id, permission)

    return object


def import_comment(comment_data, object, component):
    component_id = _get_or_create_component_id(comment_data['component_uuid'])
    user_id = _get_or_create_user_id(comment_data['user'])
    try:
        comment = get_comment(comment_data['fed_id'], component_id)

        if comment.user_id != user_id or comment.content != comment_data['content'] or comment.utc_datetime != comment_data['utc_datetime']:
            update_comment(
                comment_id=comment.id,
                user_id=user_id,
                content=comment_data['content'],
                utc_datetime=comment_data['utc_datetime']
            )
            fed_logs.update_comment(comment.id, component.id)

    except errors.CommentDoesNotExistError:
        comment = get_comment(create_comment(object.object_id, user_id, comment_data['content'], comment_data['utc_datetime'], comment_data['fed_id'], component_id))
        fed_logs.import_comment(comment.id, component.id)
    return comment


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


def import_object_location_assignment(assignment_data, object, component):
    component_id = _get_or_create_component_id(assignment_data['component_uuid'])
    assignment = get_fed_object_location_assignment(assignment_data['fed_id'], component_id)

    user_id = _get_or_create_user_id(assignment_data['user'])
    responsible_user_id = _get_or_create_user_id(assignment_data['responsible_user'])
    location_id = _get_or_create_location_id(assignment_data['location'])

    if assignment is None:
        assignment = create_fed_assignment(assignment_data['fed_id'], component_id, object.object_id, location_id, responsible_user_id, user_id, assignment_data['description'], assignment_data['utc_datetime'], assignment_data['confirmed'], assignment_data.get('declined', False))
        fed_logs.import_object_location_assignment(assignment.id, component.id)
    elif assignment.location_id != location_id or assignment.user_id != user_id or assignment.responsible_user_id != responsible_user_id or assignment.description != assignment_data['description'] or assignment.object_id != object.object_id or assignment.confirmed != assignment_data['confirmed'] or assignment.utc_datetime != assignment_data['utc_datetime']:
        assignment.location_id = location_id
        assignment.responsible_user_id = responsible_user_id
        assignment.user_id = user_id
        assignment.description = assignment_data['description']
        assignment.object_id = object.object_id
        assignment.confirmed = assignment_data['confirmed']
        assignment.utc_datetime = assignment_data['utc_datetime']
        assignment.declined = assignment_data.get('declined', False)
        db.session.commit()
        fed_logs.update_object_location_assignment(assignment.id, component.id)
    return assignment


def _get_or_create_action_id(action_data):
    if action_data is None:
        return None
    component_id = _get_or_create_component_id(action_data['component_uuid'])
    try:
        action = get_action(action_data['action_id'], component_id)
    except errors.ActionDoesNotExistError:
        action = create_action(action_type_id=None, schema=None, fed_id=action_data['action_id'], component_id=component_id)
        fed_logs.create_ref_action(action.id, component_id)
    return action.id


def import_action(action_data, component):
    def _import_schema(schema, path=[]):
        if schema is None:
            return None
        if schema.get('type') == 'array' and 'items' in schema:
            _import_schema(schema['items'], path + ['[?]'])
        if schema.get('type') == 'object':
            if isinstance(schema.get('properties'), dict):
                for property_name, property_schema in schema['properties'].items():
                    _import_schema(property_schema, path + [property_name])
                    if 'template' in property_schema:
                        try:
                            c = get_component_by_uuid(property_schema['template']['component_uuid'])
                            property_schema['template'] = get_action(property_schema['template']['action_id'], c.id).id
                        except errors.ActionDoesNotExistError:
                            pass
                        except errors.ComponentDoesNotExistError:
                            pass
        return schema

    component_id = _get_or_create_component_id(action_data['component_uuid'])

    action_type_id = _get_or_create_action_type_id(action_data['action_type'])
    instrument_id = _get_or_create_instrument_id(action_data['instrument'])
    user_id = _get_or_create_user_id(action_data['user'])

    schema = _import_schema(action_data['schema'])

    try:
        action = get_mutable_action(action_data['fed_id'], component_id)
        if action.type_id != action_type_id or action.schema != action_data['schema'] or action.instrument_id != instrument_id or action.user_id != user_id or action.description_is_markdown != action_data['description_is_markdown'] or action.is_hidden != action_data['is_hidden'] or action.short_description_is_markdown != action_data['short_description_is_markdown'] or ('admin_only' in action_data and action.admin_only != action_data['admin_only']) or ('disable_create_objects' in action_data and action.disable_create_objects != action_data['disable_create_objects']):
            action.action_type_id = action_type_id
            action.schema = schema
            action.instrument_id = instrument_id
            action.user_id = user_id
            action.description_is_markdown = action_data['description_is_markdown']
            action.is_hidden = action_data['is_hidden']
            action.short_description_is_markdown = action_data['short_description_is_markdown']
            if 'admin_only' in action_data:
                action.admin_only = action_data['admin_only']
            if 'disable_create_objects' in action_data:
                action.disable_create_objects = action_data['disable_create_objects']
            db.session.commit()
            fed_logs.update_action(action.id, component.id)
    except errors.ActionDoesNotExistError:
        action = create_action(
            fed_id=action_data['fed_id'],
            component_id=component_id,
            action_type_id=action_type_id,
            schema=schema,
            instrument_id=instrument_id,
            user_id=user_id,
            description_is_markdown=action_data['description_is_markdown'],
            is_hidden=action_data['is_hidden'],
            short_description_is_markdown=action_data['short_description_is_markdown'],
            admin_only=action_data.get('admin_only', False),
            disable_create_objects=action_data.get('disable_create_objects', False),
        )
        fed_logs.import_action(action.id, component.id)

    for action_translation in action_data['translations']:
        set_action_translation(
            action_id=action.id,
            language_id=action_translation['language_id'],
            name=action_translation['name'],
            description=action_translation['description'],
            short_description=action_translation['short_description']
        )
    return action


def _parse_action_ref(action_data):
    if action_data is None:
        return None
    action_id = _get_id(action_data.get('action_id'))
    component_uuid = _get_uuid(action_data.get('component_uuid'))
    return {'action_id': action_id, 'component_uuid': component_uuid}


def _parse_schema(schema, path=[]):
    if schema is None:
        return
    all_language_codes = {
        language.lang_code
        for language in get_languages()
    }
    for key in ['title', 'placeholder', 'default', 'note']:
        if key in schema and isinstance(schema[key], dict):
            for lang_code in list(schema[key].keys()):
                if lang_code not in all_language_codes:
                    del schema[key][lang_code]

    if 'languages' in schema and schema['languages'] != 'all':
        if not isinstance(schema['languages'], list):
            raise errors.InvalidDataExportError('Invalid schema')
        for language in schema['languages']:
            if language not in all_language_codes:
                schema['languages'].remove(language)

    if 'choices' in schema:
        for i, choice in enumerate(schema['choices']):
            if isinstance(choice, dict):
                for lang_code in list(choice.keys()):
                    if lang_code not in all_language_codes:
                        del choice[lang_code]
    if schema.get('type') == 'array' and 'items' in schema:
        _parse_schema(schema['items'], path + ['[?]'])
    if schema.get('type') == 'object':
        if isinstance(schema.get('properties'), dict):
            for property_name, property_schema in schema['properties'].items():
                _parse_schema(property_schema, path + [property_name])
                template = _get_dict(property_schema.get('template'))
                if template:
                    template_action = _parse_action_ref(template)
                    property_schema['template'] = template_action


def parse_action(action_data):
    schema = _get_dict(action_data.get('schema'))
    _parse_schema(schema)
    fed_id = _get_id(action_data.get('action_id'))
    uuid = _get_uuid(action_data.get('component_uuid'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError('Invalid update for local action {}'.format(fed_id))
    if schema is not None:
        try:
            validate_schema(schema, strict=True)
        except errors.ValidationError as e:
            raise errors.InvalidDataExportError('Invalid schema in action #{} @ {} ({})'.format(fed_id, uuid, e))

    result = {
        'fed_id': fed_id,
        'component_uuid': uuid,
        'action_type': _parse_action_type_ref(_get_dict(action_data.get('action_type'), mandatory=True)),
        'schema': schema,
        'instrument': _parse_instrument_ref(_get_dict(action_data.get('instrument'))),
        'user': _parse_user_ref(_get_dict(action_data.get('user'))),
        'description_is_markdown': _get_bool(action_data.get('description_is_markdown'), default=False),
        'is_hidden': _get_bool(action_data.get('is_hidden'), default=False),
        'short_description_is_markdown': _get_bool(action_data.get('short_description_is_markdown'), default=False),
        'translations': []
    }
    admin_only = _get_bool(action_data.get('admin_only'))
    if admin_only is not None:
        result['admin_only'] = admin_only
    disable_create_objects = _get_bool(action_data.get('disable_create_objects'))
    if disable_create_objects is not None:
        result['disable_create_objects'] = disable_create_objects

    allowed_language_ids = [language.id for language in get_languages(only_enabled_for_input=False)]

    translation_data = _get_dict(action_data.get('translations'))
    if translation_data is not None:
        for lang_code, translation in translation_data.items():
            try:
                language = get_language_by_lang_code(lang_code.lower())
            except errors.LanguageDoesNotExistError:
                continue
            language_id = language.id
            if language_id not in allowed_language_ids:
                continue

            result['translations'].append({
                'language_id': language_id,
                'name': _get_str(translation.get('name')),
                'description': _get_str(translation.get('description')),
                'short_description': _get_str(translation.get('short_description'))
            })
    return result


def parse_comment(comment_data):
    uuid = _get_uuid(comment_data.get('component_uuid'))
    fed_id = _get_id(comment_data.get('comment_id'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError('Invalid update for local comment #{}'.format(fed_id))
    return {
        'fed_id': fed_id,
        'component_uuid': uuid,
        'user': _parse_user_ref(_get_dict(comment_data.get('user'))),
        'content': _get_str(comment_data.get('content'), mandatory=True, allow_empty=False),
        'utc_datetime': _get_utc_datetime(comment_data.get('utc_datetime'), mandatory=True)
    }


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


def parse_object_location_assignment(assignment_data):
    uuid = _get_uuid(assignment_data.get('component_uuid'))
    fed_id = _get_id(assignment_data.get('id'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError('Invalid update for local object location assignment {} @ {}'.format(fed_id, uuid))

    responsible_user_data = _get_dict(assignment_data.get('responsible_user'))
    location_data = _get_dict(assignment_data.get('location'))
    description = _get_translation(assignment_data.get('description'))
    if responsible_user_data is None and location_data is None and description is None:
        raise errors.InvalidDataExportError('Empty object location assignment {} @ {}'.format(fed_id, uuid))

    return {
        'fed_id': fed_id,
        'component_uuid': uuid,
        'location': _parse_location_ref(location_data),
        'responsible_user': _parse_user_ref(responsible_user_data),
        'user': _parse_user_ref(_get_dict(assignment_data.get('user'))),
        'description': description,
        'utc_datetime': _get_utc_datetime(assignment_data.get('utc_datetime'), mandatory=True),
        'confirmed': _get_bool(assignment_data.get('confirmed'), default=False)
    }


def parse_entry(entry_data, component):
    if type(entry_data) == list:
        for entry in entry_data:
            parse_entry(entry, component)
    elif type(entry_data) == dict:
        if '_type' not in entry_data.keys():
            for key in entry_data:
                parse_entry(entry_data[key], component)
        else:
            if entry_data.get('_type') == 'user':
                user_id = _get_id(entry_data.get('user_id'), mandatory=False)
                if user_id is None:
                    return
                data_component_uuid = _get_uuid(entry_data.get('component_uuid'))
                if data_component_uuid == flask.current_app.config['FEDERATION_UUID']:
                    try:
                        user = get_user(user_id)
                    except errors.UserDoesNotExistError:
                        raise errors.InvalidDataExportError('Local user #{} does not exist'.format(user_id))
                    del entry_data['component_uuid']
                    entry_data['user_id'] = user.id
                else:
                    try:
                        data_component = get_component_by_uuid(_get_uuid(entry_data.get('component_uuid')))
                        try:
                            user = get_user(_get_id(entry_data.get('user_id')), data_component.id)
                            del entry_data['component_uuid']
                            entry_data['user_id'] = user.id
                        except errors.UserDoesNotExistError:
                            pass
                    except errors.ComponentDoesNotExistError:
                        pass

            if entry_data.get('_type') in ('sample', 'object_reference', 'measurement'):
                data_obj_id = _get_id(entry_data.get('object_id'), mandatory=False)
                if data_obj_id is None:
                    return
                data_component_uuid = _get_uuid(entry_data.get('component_uuid'), mandatory=False)
                if data_component_uuid == flask.current_app.config['FEDERATION_UUID']:
                    try:
                        obj = get_object(data_obj_id)
                    except errors.ObjectDoesNotExistError:
                        raise errors.InvalidDataExportError('Local object #{} does not exist'.format(data_obj_id))
                    del entry_data['component_uuid']
                    entry_data['object_id'] = obj.id
                else:
                    try:
                        data_component = get_component_by_uuid(_get_uuid(entry_data.get('component_uuid')))
                        obj = get_fed_object(data_obj_id, data_component.id)
                        if obj is not None:
                            del entry_data['component_uuid']
                            entry_data['object_id'] = obj.object_id
                    except errors.ComponentDoesNotExistError:
                        pass
                    except errors.ObjectDoesNotExistError:
                        pass
            all_lang_codes = [lang.lang_code for lang in languages.get_languages()]

            if entry_data.get('_type') == 'text':
                if entry_data.get('text') and isinstance(entry_data.get('text'), dict):
                    for lang_code in list(entry_data.get('text').keys()):
                        if lang_code not in all_lang_codes:
                            del entry_data['text'][lang_code]


def parse_object(object_data, component):
    fed_object_id = _get_id(object_data.get('object_id'))
    versions = _get_list(object_data.get('versions'), mandatory=True)
    parsed_versions = []
    for version in versions:
        fed_version_id = _get_id(version.get('version_id'), mandatory=True, min=0)
        data = _get_dict(version.get('data'))
        if data is not None:
            parse_entry(data, component)
        schema = _get_dict(version.get('schema'))
        _parse_schema(schema)
        try:
            if schema is not None:
                validate_schema(schema, strict=True)
                if data is not None:
                    validate(data, schema, allow_disabled_languages=True, strict=False)
        except errors.ValidationError:
            raise errors.InvalidDataExportError('Invalid data or schema in version {} of object #{} @ {}'.format(fed_version_id, fed_object_id, component.uuid))
        parsed_versions.append({
            'fed_version_id': fed_version_id,
            'data': data,
            'schema': schema,
            'user': _parse_user_ref(_get_dict(version.get('user'))),
            'utc_datetime': _get_utc_datetime(version.get('utc_datetime'), default=None),
        })

    result = {
        'fed_object_id': fed_object_id,
        'component_id': component.id,
        'versions': parsed_versions,
        'action': _parse_action_ref(_get_dict(object_data.get('action'))),
        'comments': [],
        'files': [],
        'object_location_assignments': [],
        'permissions': {'users': {}, 'groups': {}, 'projects': {}, 'all_users': Permissions.NONE}
    }

    comments = _get_list(object_data.get('comments'))
    if comments is not None:
        for comment in comments:
            result['comments'].append(parse_comment(comment))

    files = _get_list(object_data.get('files'))
    if files is not None:
        for file in files:
            result['files'].append(parse_file(file))

    assignments = _get_list(object_data.get('object_location_assignments'))
    if assignments is not None:
        for assignment in assignments:
            result['object_location_assignments'].append(parse_object_location_assignment(assignment))

    policy = _get_dict(object_data.get('policy'), mandatory=True)

    permissions = _get_permissions(policy.get('permissions'))
    if permissions is not None:
        users = _get_dict(permissions.get('users'))
        if users is not None:
            for user_id, permission in users.items():
                user_id = _get_id(user_id, convert=True)
                try:
                    get_user(user_id)
                except errors.UserDoesNotExistError:
                    continue
                try:
                    result['permissions']['users'][user_id] = Permissions.from_name(permission)
                except ValueError:
                    raise errors.InvalidDataExportError('Unknown permission "{}"'.format(permission))
        groups = _get_dict(permissions.get('groups'))
        if groups is not None:
            for group_id, permission in groups.items():
                group_id = _get_id(group_id, convert=True)
                try:
                    get_group(group_id)
                except errors.GroupDoesNotExistError:
                    continue
                try:
                    result['permissions']['groups'][group_id] = Permissions.from_name(permission)
                except ValueError:
                    raise errors.InvalidDataExportError('Unknown permission "{}"'.format(permission))
        projects = _get_dict(permissions.get('projects'))
        if projects is not None:
            for project_id, permission in projects.items():
                project_id = _get_id(project_id, convert=True)
                try:
                    get_project(project_id)
                except errors.ProjectDoesNotExistError:
                    continue
                try:
                    result['permissions']['projects'][project_id] = Permissions.from_name(permission)
                except ValueError:
                    raise errors.InvalidDataExportError('Unknown permission "{}"'.format(permission))
        all_users = _get_str(permissions.get('all_users'))
        if all_users is not None:
            permission = all_users
            try:
                result['permissions']['all_users'] = Permissions.from_name(permission)
            except ValueError:
                raise errors.InvalidDataExportError('Unknown permission "{}"'.format(permission))
    return result


def entry_preprocessor(data, refs, markdown_images):
    if type(data) == list:
        for entry in data:
            entry_preprocessor(entry, refs, markdown_images)
    elif type(data) == dict:
        if '_type' not in data.keys():
            for key in data:
                entry_preprocessor(data[key], refs, markdown_images)
        else:
            if data['_type'] in ['sample', 'object_reference', 'measurement']:
                if data.get('component_uuid') is None or data.get('component_uuid') == flask.current_app.config['FEDERATION_UUID']:
                    o = get_object(data['object_id'])
                    if o.component_id is not None:
                        c = get_component(o.component_id)
                        data['object_id'] = o.fed_object_id
                        data['component_uuid'] = c.uuid
                    else:
                        data['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
            if data['_type'] == 'user':
                if data.get('component_uuid') is None or data.get('component_uuid') == flask.current_app.config['FEDERATION_UUID']:
                    try:
                        u = get_user(data.get('user_id'))
                        if u.component_id is not None:
                            c = get_component(u.component_id)
                            data['user_id'] = u.fed_id
                            data['component_uuid'] = c.uuid
                        else:
                            data['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
                    except errors.UserDoesNotExistError:
                        pass

            if data['_type'] == 'text' and data.get('is_markdown'):
                if isinstance(data.get('text'), str):
                    markdown_as_html = markdown_to_html.markdown_to_safe_html(data['text'])
                    for file_name in find_referenced_markdown_images(markdown_as_html):
                        markdown_image_b = get_markdown_image(file_name, None)
                        data['text'] = data['text'].replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
                        if markdown_image_b is not None and file_name not in markdown_images:
                            markdown_images[file_name] = base64.b64encode(markdown_image_b).decode('utf-8')
                elif isinstance(data.get('text'), dict):
                    for lang in data['text'].keys():
                        markdown_as_html = markdown_to_html.markdown_to_safe_html(data['text'][lang])
                        for file_name in find_referenced_markdown_images(markdown_as_html):
                            markdown_image_b = get_markdown_image(file_name, None)
                            data['text'][lang] = data['text'][lang].replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
                            if markdown_image_b is not None and file_name not in markdown_images:
                                markdown_images[file_name] = base64.b64encode(markdown_image_b).decode('utf-8')


def schema_entry_preprocessor(schema, refs):
    if type(schema) == list:
        for entry in schema:
            schema_entry_preprocessor(entry, refs)
    elif type(schema) == dict:
        if 'type' not in schema.keys():
            for key in schema:
                schema_entry_preprocessor(schema[key], refs)
        if schema.get('type') == 'object':
            if schema.get('template'):
                if ('actions', schema.get('template')) not in refs:
                    refs.append(('actions', schema.get('template')))
                action = get_action(schema.get('template'))
                if action.component_id is not None:
                    comp = action.component
                    schema['template'] = {
                        'action_id': action.fed_id,
                        'component_uuid': comp.uuid
                    }
                else:
                    schema['template'] = {
                        'action_id': action.id,
                        'component_uuid': flask.current_app.config['FEDERATION_UUID']
                    }
            for property in schema.get('properties'):
                schema_entry_preprocessor(schema['properties'][property], refs)


def shared_object_preprocessor(object_id, policy, refs, markdown_images):
    result = {
        'object_id': object_id,
        'versions': [],
        'component_uuid': flask.current_app.config['FEDERATION_UUID'],
        'action': None,
        'comments': [], 'object_location_assignments': [], 'files': [],
        'policy': policy
    }
    object = get_object(object_id)
    object_versions = get_object_versions(object_id)
    if 'access' in policy:
        if 'action' in policy['access'] and policy['access']['action']:
            if ('actions', object.action_id) not in refs:
                refs.append(('actions', object.action_id))
            action = get_action(object.action_id)
            if action.component_id is not None:
                comp = action.component
                result['action'] = {
                    'action_id': action.fed_id,
                    'component_uuid': comp.uuid
                }
            else:
                result['action'] = {
                    'action_id': action.id,
                    'component_uuid': flask.current_app.config['FEDERATION_UUID']
                }
        if 'comments' in policy['access'] and policy['access']['comments']:
            comments = get_comments_for_object(object_id)
            result['comments'] = []
            for comment in comments:
                if comment.component_id is None:
                    res_comment = {
                        'comment_id': comment.id,
                        'component_uuid': flask.current_app.config['FEDERATION_UUID']
                    }
                else:
                    comp = comment.component
                    res_comment = {
                        'comment_id': comment.fed_id,
                        'component_uuid': comp.uuid
                    }
                res_comment['content'] = comment.content
                res_comment['utc_datetime'] = comment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                if 'users' in policy['access'] and policy['access']['users']:
                    if ('users', comment.user_id) not in refs:
                        refs.append(('users', comment.user_id))
                    user = get_user(comment.user_id)
                    if user.fed_id is not None:
                        comp = user.component
                        res_comment['user'] = {
                            'user_id': user.fed_id,
                            'component_uuid': comp.uuid
                        }
                    else:
                        res_comment['user'] = {
                            'user_id': comment.user_id,
                            'component_uuid': flask.current_app.config['FEDERATION_UUID']
                        }
                result['comments'].append(res_comment)
        if 'files' in policy['access'] and policy['access']['files']:
            files = get_files_for_object(object_id)
            result['files'] = []
            for file in files:
                if file.storage != 'url':
                    continue
                if file.component_id is None:
                    res_file = {
                        'file_id': file.id,
                        'component_uuid': flask.current_app.config['FEDERATION_UUID']
                    }
                else:
                    comp = get_component(file.component_id)
                    res_file = {
                        'file_id': file.fed_id,
                        'component_uuid': comp.uuid
                    }
                res_file['utc_datetime'] = file.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                if 'users' in policy['access'] and policy['access']['users']:
                    if ('users', file.user_id) not in refs:
                        refs.append(('users', file.user_id))
                    user = get_user(file.user_id)
                    if user.fed_id is not None:
                        comp = user.component
                        res_file['user'] = {
                            'user_id': user.fed_id,
                            'component_uuid': comp.uuid
                        }
                    else:
                        res_file['user'] = {
                            'user_id': file.user_id,
                            'component_uuid': flask.current_app.config['FEDERATION_UUID']
                        }
                if file.is_hidden:
                    log_entry = FileLogEntry.query.filter_by(
                        object_id=file.object_id,
                        file_id=file.id,
                        type=FileLogEntryType.HIDE_FILE
                    ).order_by(FileLogEntry.utc_datetime.desc()).first()
                    res_file['hidden'] = {
                        'reason': file.hide_reason,
                        'utc_datetime': log_entry.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                    }
                    if ('users', log_entry.user_id) not in refs:
                        refs.append(('users', log_entry.user_id))
                    user = get_user(file.user_id)
                    if user.fed_id is not None:
                        comp = user.component
                        res_file['hidden']['user'] = {
                            'user_id': user.fed_id,
                            'component_uuid': comp.uuid
                        }
                    else:
                        res_file['hidden']['user'] = {
                            'user_id': file.user_id,
                            'component_uuid': flask.current_app.config['FEDERATION_UUID']
                        }
                else:
                    res_file['data'] = file.data
                result['files'].append(res_file)
        if 'object_location_assignments' in policy['access'] and policy['access']['object_location_assignments']:
            olas = get_object_location_assignments(object_id)
            for ola in olas:
                if ola.location_id is not None and ('locations', ola.location_id) not in refs:
                    refs.append(('locations', ola.location_id))
                if ola.user_id is not None and ('users', ola.user_id) not in refs:
                    refs.append(('users', ola.user_id))
                if ola.responsible_user_id is not None and ('users', ola.responsible_user_id) not in refs:
                    refs.append(('users', ola.responsible_user_id))
                if ola.location_id is not None:
                    location = get_location(ola.location_id)
                    if location.component is not None:
                        comp = location.component
                        loc = {
                            'location_id': location.fed_id,
                            'component_uuid': comp.uuid
                        }
                    else:
                        loc = {
                            'location_id': location.id,
                            'component_uuid': flask.current_app.config['FEDERATION_UUID']
                        }
                else:
                    loc = None
                if ola.responsible_user_id is not None:
                    responsible_user = get_user(ola.responsible_user_id)
                    if responsible_user.component_id is not None:
                        comp = responsible_user.component
                        r_user = {
                            'user_id': responsible_user.fed_id,
                            'component_uuid': comp.uuid
                        }
                    else:
                        r_user = {
                            'user_id': responsible_user.id,
                            'component_uuid': flask.current_app.config['FEDERATION_UUID']
                        }
                else:
                    r_user = None
                ola_user = get_user(ola.user_id)
                if ola_user.component_id is not None:
                    comp = ola_user.component
                    c_user = {
                        'user_id': ola_user.fed_id,
                        'component_uuid': comp.uuid
                    }
                else:
                    c_user = {
                        'user_id': ola_user.id,
                        'component_uuid': flask.current_app.config['FEDERATION_UUID']
                    }
                if ola.component_id is None:
                    component_uuid = flask.current_app.config['FEDERATION_UUID']
                else:
                    comp = get_component(ola.component_id)
                    component_uuid = comp.uuid
                result['object_location_assignments'].append({
                    'id': ola.id,
                    'component_uuid': component_uuid,
                    'location': loc,
                    'responsible_user': r_user,
                    'user': c_user,
                    'description': ola.description,
                    'utc_datetime': ola.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'confirmed': ola.confirmed,
                })
    for version in object_versions:
        result['versions'].append({
            'version_id': version.version_id, 'schema': None, 'data': None, 'user': None,
            'utc_datetime': version.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
        })
        if 'access' in policy:
            if 'data' not in policy['access'] or ('data' in policy['access'] and policy['access']['data']):
                result['versions'][-1]['data'] = version.data.copy()
                result['versions'][-1]['schema'] = version.schema.copy()
                entry_preprocessor(result['versions'][-1]['data'], refs, markdown_images)
                schema_entry_preprocessor(result['versions'][-1]['schema'], refs)
            if 'users' in policy['access'] and policy['access']['users']:
                if ('users', version.user_id) not in refs:
                    refs.append(('users', version.user_id))
                user = get_user(version.user_id)
                if user.component_id is not None:
                    comp = user.component
                    result['versions'][-1]['user'] = {
                        'user_id': user.fed_id,
                        'component_uuid': comp.uuid
                    }
                else:
                    result['versions'][-1]['user'] = {
                        'user_id': user.id,
                        'component_uuid': flask.current_app.config['FEDERATION_UUID']
                    }
        else:
            result['versions'][-1]['data'] = object.data.copy()
            result['versions'][-1]['schema'] = object.schema.copy()
            entry_preprocessor(result['versions'][-1]['data'], refs, markdown_images)
            schema_entry_preprocessor(result['versions'][-1]['schema'], refs)
        if 'modification' in policy:
            modification = policy['modification']
            if 'insert' in modification:
                if 'data' in modification['insert']:
                    for key in modification['insert']['data']:
                        result['versions'][-1]['data'][key] = modification['insert']['data'][key]
                if 'schema' in modification['insert']:
                    for key in modification['insert']['schema']:
                        result['versions'][-1]['schema']['properties'][key] = modification['insert']['schema'][key]

            if 'update' in modification:
                if 'data' in modification['update']:
                    for key in modification['update']['data']:
                        if key not in result['versions'][-1]['data']:
                            pass
                        for k in modification['update']['data'][key]:
                            result['versions'][-1]['data'][key][k] = modification['update']['data'][key][k]
                if 'schema' in modification['update']:
                    for key in modification['update']['schema']:
                        if key not in result['versions'][-1]['schema']['properties']:
                            pass
                        result['versions'][-1]['schema']['properties'][key] = {}
                        for k in modification['update']['schema'][key]:
                            result['versions'][-1]['schema']['properties'][key][k] = modification['update']['schema'][key][k]
    return result


def shared_action_preprocessor(action_id: int, _component: Component, refs: list, markdown_images: dict):
    action = get_action(action_id)
    if action.component_id is not None:
        return None
    translations_data = {}

    try:
        translations = get_action_translations_for_action(action_id)
        for translation in translations:
            description = translation.description
            markdown_as_html = markdown_to_html.markdown_to_safe_html(description)
            for file_name in find_referenced_markdown_images(markdown_as_html):
                markdown_image_b = get_markdown_image(file_name, None)
                description = description.replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
                if markdown_image_b is not None and file_name not in markdown_images:
                    markdown_images[file_name] = base64.b64encode(markdown_image_b).decode('utf-8')

            short_description = translation.short_description
            markdown_as_html = markdown_to_html.markdown_to_safe_html(short_description)
            for file_name in find_referenced_markdown_images(markdown_as_html):
                markdown_image_b = get_markdown_image(file_name, None)
                short_description = short_description.replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
                if markdown_image_b is not None and file_name not in markdown_images:
                    markdown_images[file_name] = base64.b64encode(markdown_image_b).decode('utf-8')

            lang_code = get_language(translation.language_id).lang_code
            translations_data[lang_code] = {
                'name': translation.name,
                'description': description,
                'short_description': short_description
            }
    except errors.ActionTranslationDoesNotExistError:
        translations_data = None

    if action.instrument_id is not None and ('instruments', action.instrument_id) not in refs:
        refs.append(('instruments', action.instrument_id))
    if action.user_id is not None and ('users', action.user_id) not in refs:
        refs.append(('users', action.user_id))
    if action.instrument_id is None:
        instrument = None
    else:
        i = get_instrument(action.instrument_id)
        if i.component_id is None:
            instrument = {
                'instrument_id': i.id,
                'component_uuid': flask.current_app.config['FEDERATION_UUID']
            }
        else:
            comp = i.component
            instrument = {
                'instrument_id': i.fed_id,
                'component_uuid': comp.uuid
            }
    if action.type.component_id is None:
        action_type = {
            'action_type_id': action.type.id,
            'component_uuid': flask.current_app.config['FEDERATION_UUID']
        }
    else:
        comp = get_component(action.type.component_id)
        action_type = {
            'action_type_id': action.type.fed_id,
            'component_uuid': comp.uuid
        }
    if ('action_types', action.type_id) not in refs:
        refs.append(('action_types', action.type_id))
    if action.user_id is None:
        user = None
    else:
        u = get_user(action.user_id)
        if u.component_id is None:
            user = {
                'user_id': u.id,
                'component_uuid': flask.current_app.config['FEDERATION_UUID']
            }
        else:
            comp = u.component
            user = {
                'user_id': u.fed_id,
                'component_uuid': comp.uuid
            }
    schema = action.schema.copy()
    schema_entry_preprocessor(schema, refs)
    return {
        'action_id': action.id if action.fed_id is None else action.fed_id,
        'component_uuid': flask.current_app.config['FEDERATION_UUID'] if action.component_id is None else action.component.uuid,
        'action_type': action_type,
        'instrument': instrument,
        'schema': schema,
        'user': user,
        'description_is_markdown': action.description_is_markdown,
        'is_hidden': action.is_hidden,
        'short_description_is_markdown': action.short_description_is_markdown,
        'translations': translations_data,
        'admin_only': action.admin_only,
        'disable_create_objects': action.disable_create_objects,
    }


def parse_import_action(action_data, component):
    return import_action(parse_action(action_data), component)


def parse_import_comment(comment_data, object, component):
    return import_comment(parse_comment(comment_data), object, component)


def parse_import_file(file_data, object, component):
    return import_file(parse_file(file_data), object, component)


def parse_import_object_location_assignment(assignment_data, object, component):
    return import_object_location_assignment(parse_object_location_assignment(assignment_data), object, component)


def parse_import_object(object_data, component):
    return import_object(parse_object(object_data, component), component)
