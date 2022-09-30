import copy

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_list, _get_dict, _get_translation
from .location_types import _parse_location_type_ref, _get_or_create_location_type_id
from .users import _parse_user_ref, _get_or_create_user_id, import_user
from ..locations import LocationType, get_location_type, set_location_responsible_users, get_location, get_locations, create_location, update_location
from ..components import Component, get_component, get_component_by_uuid
from .. import errors, fed_logs


def parse_location(location_data):
    fed_id = _get_id(location_data.get('location_id'))
    uuid = _get_uuid(location_data.get('component_uuid'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError('Invalid update for local location {}'.format(fed_id))
    responsible_users = _get_list(location_data.get('responsible_users'))
    return {
        'fed_id': fed_id,
        'component_uuid': uuid,
        'name': _get_translation(location_data.get('name')),
        'description': _get_translation(location_data.get('description')),
        'parent_location': _parse_location_ref(_get_dict(location_data.get('parent_location'))),
        'location_type': _parse_location_type_ref(_get_dict(location_data.get('location_type'))),
        'responsible_users': [
            _parse_user_ref(_get_dict(responsible_user))
            for responsible_user in responsible_users
        ] if responsible_users is not None else [],
    }


def import_location(location_data, component, locations, users):
    component_id = _get_or_create_component_id(location_data['component_uuid'])

    parent = _parse_location_ref(location_data.get('parent_location'))
    if parent is None:
        parent_location_id = None
    else:
        if (parent['location_id'], parent['component_uuid']) in locations.keys():
            parent_location_id = import_location(locations[(parent['location_id'], parent['component_uuid'])], component, locations, users).id
            locations.pop((location_data['fed_id'], location_data['component_uuid']))
        else:
            parent_location_id = _get_or_create_location_id(location_data['parent_location'])
    location_type = _parse_location_type_ref(location_data.get('location_type'))
    if location_type is None:
        location_type_id = LocationType.LOCATION
    else:
        location_type_id = _get_or_create_location_type_id(location_data['location_type'])
    responsible_user_ids = []
    if location_data.get('responsible_users'):
        users_by_ids = {
            (user['fed_id'], user['component_uuid']): user
            for user in users
        }
        for responsible_user_data in location_data['responsible_users']:
            responsible_user = _parse_user_ref(responsible_user_data)
            if responsible_user is None:
                responsible_user_id = None
            else:
                if (responsible_user['user_id'], responsible_user['component_uuid']) in users_by_ids.keys():
                    responsible_user_id = import_user(users_by_ids[(responsible_user['user_id'], responsible_user['component_uuid'])], component).id
                else:
                    responsible_user_id = _get_or_create_user_id(responsible_user_data)
            if responsible_user_id is not None:
                responsible_user_ids.append(responsible_user_id)
    try:
        location = get_location(location_data['fed_id'], component_id)
        if location.name != location_data['name'] or location.description != location_data['description'] or location.parent_location_id != parent_location_id:
            update_location(
                location_id=location.id,
                name=location_data['name'],
                description=location_data['description'],
                parent_location_id=parent_location_id,
                user_id=None,
                type_id=location_type_id
            )
            set_location_responsible_users(
                location_id=location.id,
                responsible_user_ids=responsible_user_ids
            )
            fed_logs.update_location(location.id, component.id)
    except errors.LocationDoesNotExistError:
        location = create_location(
            fed_id=location_data['fed_id'],
            component_id=component_id,
            name=location_data['name'],
            description=location_data['description'],
            parent_location_id=parent_location_id,
            user_id=None,
            type_id=location_type_id
        )
        set_location_responsible_users(
            location_id=location.id,
            responsible_user_ids=responsible_user_ids
        )
        fed_logs.import_location(location.id, component.id)
    return location


def parse_import_location(location_data, component):
    location_data = parse_location(location_data)
    locations = {(location_data['fed_id'], location_data['component_uuid']): location_data}
    locations_check_for_cyclic_dependencies(locations)
    return import_location(location_data, component, locations, [])


def _parse_location_ref(location_data):
    if location_data is None:
        return None
    location_id = _get_id(location_data.get('location_id'))
    component_uuid = _get_uuid(location_data.get('component_uuid'))
    return {'location_id': location_id, 'component_uuid': component_uuid}


def _get_or_create_location_id(location_data):
    if location_data is None:
        return None
    component_id = _get_or_create_component_id(location_data['component_uuid'])
    try:
        location = get_location(location_data['location_id'], component_id)
    except errors.LocationDoesNotExistError:
        location = create_location(
            name=None,
            description=None,
            parent_location_id=None,
            user_id=None,
            type_id=LocationType.LOCATION,
            fed_id=location_data['location_id'],
            component_id=component_id
        )
        fed_logs.create_ref_location(location.id, component_id)
    return location.id


def shared_location_preprocessor(location_id: int, _component: Component, refs: list, _markdown_images):
    location = get_location(location_id)
    if location.component is not None:
        return None
    if location.parent_location_id is not None:
        if ('locations', location.parent_location_id) not in refs:
            refs.append(('locations', location.parent_location_id))
        parent = get_location(location.parent_location_id)
        if parent.component is None:
            parent_location = {
                'location_id': parent.id,
                'component_uuid': flask.current_app.config['FEDERATION_UUID']
            }
        else:
            comp = get_component(parent.component.id)
            parent_location = {
                'location_id': parent.fed_id,
                'component_uuid': comp.uuid
            }
    else:
        parent_location = None
    if location.type_id is not None:
        if ('location_types', location.type_id) not in refs:
            refs.append(('location_types', location.type_id))
        location_type = get_location_type(location.type_id)
        if location_type.component_id is None:
            location_type = {
                'location_type_id': location_type.id,
                'component_uuid': flask.current_app.config['FEDERATION_UUID']
            }
        else:
            location_type = {
                'location_type_id': location_type.fed_id,
                'component_uuid': location_type.component.uuid
            }
    else:
        location_type = None
    responsible_users = []
    if location.responsible_users:
        for responsible_user in location.responsible_users:
            if ('users', responsible_user.id) not in refs:
                refs.append(('users', responsible_user.id))
            if responsible_user.component_id is None:
                responsible_user = {
                    'user_id': responsible_user.id,
                    'component_uuid': flask.current_app.config['FEDERATION_UUID']
                }
            else:
                responsible_user = {
                    'user_id': responsible_user.fed_id,
                    'component_uuid': responsible_user.component.uuid
                }
            responsible_users.append(responsible_user)
    return {
        'location_id': location.id if location.fed_id is None else location.fed_id,
        'component_uuid': flask.current_app.config['FEDERATION_UUID'] if location.component is None else location.component.uuid,
        'name': location.name,
        'description': location.description,
        'parent_location': parent_location,
        'location_type': location_type,
        'responsible_users': responsible_users,
    }


def locations_check_for_cyclic_dependencies(locations_data):
    def _location_check_for_cyclic_dependencies(location_data, locations, path):
        if (location_data['fed_id'], location_data['component_uuid']) in path:
            # cyclic parent-location-chain
            raise errors.InvalidDataExportError('Cyclic parent location chain. Location: #{} @ {} Path: {}'.format(location_data['fed_id'], location_data['component_uuid'], path))
        if location_data['parent_location'] is not None:
            if (location_data['parent_location']['location_id'], location_data['parent_location']['component_uuid']) in locations.keys():
                _location_check_for_cyclic_dependencies(
                    locations[(location_data['parent_location']['location_id'], location_data['parent_location']['component_uuid'])],
                    locations, path + [(location_data['fed_id'], location_data['component_uuid'])]
                )
            else:
                try:
                    component = get_component_by_uuid(location_data['component_uuid'])
                except errors.ComponentDoesNotExistError:
                    return
                try:
                    get_location(location_data['fed_id'], component.id)
                except errors.LocationDoesNotExistError:
                    return

    data = copy.deepcopy(locations_data)
    local_locations = get_locations()
    for location in local_locations:
        if location.component is not None:
            if (location.fed_id, location.component.uuid) in data.keys():
                continue
            if location.parent_location_id is None:
                data[(location.fed_id, location.component.uuid)] = {"fed_id": location.fed_id, "component_uuid": location.component.uuid, "parent_location": None}
            else:
                parent_location = get_location(location.parent_location_id)
                if parent_location.component is not None:
                    data[(location.fed_id, location.component.uuid)] = {"fed_id": location.fed_id, "component_uuid": location.component.uuid, "parent_location": {"location_id": parent_location.fed_id, "component_uuid": parent_location.component.uuid}}
                else:
                    data[(location.fed_id, location.component.uuid)] = {"fed_id": location.fed_id, "component_uuid": location.component.uuid, "parent_location": {"location_id": parent_location.id, "component_uuid": flask.current_app.config['FEDERATION_UUID']}}

        else:
            if location.parent_location_id is None:
                data[(location.id, flask.current_app.config['FEDERATION_UUID'])] = {"fed_id": location.id, "component_uuid": flask.current_app.config['FEDERATION_UUID'], "parent_location": None}
            else:
                parent_location = get_location(location.parent_location_id)
                if parent_location.component is not None:
                    data[(location.id, flask.current_app.config['FEDERATION_UUID'])] = {"fed_id": location.id, "component_uuid": flask.current_app.config['FEDERATION_UUID'], "parent_location": {"location_id": parent_location.fed_id, "component_uuid": parent_location.component.uuid}}
                else:
                    data[(location.id, flask.current_app.config['FEDERATION_UUID'])] = {"fed_id": location.id, "component_uuid": flask.current_app.config['FEDERATION_UUID'], "parent_location": {"location_id": parent_location.id, "component_uuid": flask.current_app.config['FEDERATION_UUID']}}

    for _, location_data in data.items():
        _location_check_for_cyclic_dependencies(location_data, data, [])
