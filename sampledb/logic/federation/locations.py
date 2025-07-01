import copy
import typing

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_list, _get_dict, _get_translation
from .location_types import _parse_location_type_ref, _get_or_create_location_type_id, LocationTypeRef
from .users import _parse_user_ref, _get_or_create_user_id, import_user, UserRef, UserData
from ..locations import LocationType, get_location_type, set_location_responsible_users, get_location, get_locations, create_location, update_location, Location
from ..components import Component, get_component, get_component_by_uuid
from .. import errors, fed_logs, location_permissions
from ...models import Permissions


class LocationRef(typing.TypedDict):
    location_id: int
    component_uuid: str


class LocationPermissionsData(typing.TypedDict):
    all_users: typing.Union[typing.Literal['none'], typing.Literal['read']]


class LocationData(typing.TypedDict):
    fed_id: int
    component_uuid: str
    name: typing.Optional[typing.Dict[str, str]]
    description: typing.Optional[typing.Dict[str, str]]
    parent_location: typing.Optional[LocationRef]
    location_type: typing.Optional[LocationTypeRef]
    responsible_users: typing.List[UserRef]
    permissions: typing.Optional[LocationPermissionsData]


class SharedLocationData(typing.TypedDict):
    location_id: int
    component_uuid: str
    name: typing.Optional[typing.Dict[str, str]]
    description: typing.Optional[typing.Dict[str, str]]
    parent_location: typing.Optional[LocationRef]
    location_type: typing.Optional[LocationTypeRef]
    responsible_users: typing.List[UserRef]
    permissions: typing.Optional[LocationPermissionsData]


def parse_location(
        location_data: typing.Dict[str, typing.Any]
) -> LocationData:
    fed_id = _get_id(location_data.get('location_id'))
    uuid = _get_uuid(location_data.get('component_uuid'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError(f'Invalid update for local location {fed_id}')
    responsible_users = []
    for responsible_user_data in _get_list(location_data.get('responsible_users'), default=[]):
        responsible_user_ref = _parse_user_ref(_get_dict(responsible_user_data))
        if responsible_user_ref is not None:
            responsible_users.append(responsible_user_ref)
    return LocationData(
        fed_id=fed_id,
        component_uuid=uuid,
        name=_get_translation(location_data.get('name')),
        description=_get_translation(location_data.get('description')),
        parent_location=_parse_location_ref(_get_dict(location_data.get('parent_location'))),
        location_type=_parse_location_type_ref(_get_dict(location_data.get('location_type'))),
        responsible_users=responsible_users,
        permissions=_parse_location_permissions(_get_dict(location_data.get('permissions'))),
    )


def import_location(
        location_data: LocationData,
        component: Component,
        locations: typing.Dict[typing.Tuple[int, str], LocationData],
        users: typing.List[UserData]
) -> Location:
    component_id = _get_or_create_component_id(location_data['component_uuid'])
    # component_id will only be None if this would import a local location
    assert component_id is not None

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
        location_type_id = _get_or_create_location_type_id(location_type)
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
                type_id=location_type_id,
                is_hidden=location.is_hidden,
                enable_object_assignments=location.enable_object_assignments
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
    location_permissions_data = location_data.get('permissions')
    if location_permissions_data is not None and location_permissions_data.get('all_users') == 'read':
        location_permissions.set_location_permissions_for_all_users(location.id, Permissions.READ)
    return location


def parse_import_location(
        location_data: typing.Dict[str, typing.Any],
        component: Component
) -> Location:
    parsed_location_data = parse_location(location_data)
    locations = {
        (parsed_location_data['fed_id'], parsed_location_data['component_uuid']): parsed_location_data
    }
    locations_check_for_cyclic_dependencies(locations)
    return import_location(parsed_location_data, component, locations, [])


def _parse_location_ref(
        location_data: typing.Optional[typing.Union[LocationRef, typing.Dict[str, typing.Any]]]
) -> typing.Optional[LocationRef]:
    if location_data is None:
        return None
    location_id = _get_id(location_data.get('location_id'))
    component_uuid = _get_uuid(location_data.get('component_uuid'))
    return LocationRef(
        location_id=location_id,
        component_uuid=component_uuid
    )


def _parse_location_permissions(
        location_permissions_data: typing.Optional[typing.Dict[str, typing.Any]]
) -> typing.Optional[LocationPermissionsData]:
    if location_permissions_data is None:
        return None
    all_users_permissions = location_permissions_data.get('all_users')
    if all_users_permissions not in ('none', 'read'):
        return None
    return LocationPermissionsData(
        all_users=all_users_permissions,
    )


def _get_or_create_location_id(
        location_data: typing.Optional[LocationRef]
) -> typing.Optional[int]:
    if location_data is None:
        return None
    component_id = _get_or_create_component_id(location_data['component_uuid'])
    try:
        location = get_location(location_data['location_id'], component_id)
    except errors.LocationDoesNotExistError:
        assert component_id is not None
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


def shared_location_preprocessor(
        location_id: int,
        _component: Component,
        refs: typing.List[typing.Tuple[str, int]],
        _markdown_images: typing.Dict[str, str]
) -> typing.Optional[SharedLocationData]:
    location = get_location(location_id)
    if location.component_id is not None:
        return None
    if location.parent_location_id is not None:
        if ('locations', location.parent_location_id) not in refs:
            refs.append(('locations', location.parent_location_id))
        parent = get_location(location.parent_location_id)
        if parent.component is None or parent.fed_id is None:
            parent_location = LocationRef(
                location_id=parent.id,
                component_uuid=flask.current_app.config['FEDERATION_UUID']
            )
        else:
            comp = get_component(parent.component.id)
            parent_location = LocationRef(
                location_id=parent.fed_id,
                component_uuid=comp.uuid
            )
    else:
        parent_location = None
    if location.type_id is not None:
        if ('location_types', location.type_id) not in refs:
            refs.append(('location_types', location.type_id))
        location_type = get_location_type(location.type_id)
        if location_type.component is None or location_type.fed_id is None:
            location_type_ref = LocationTypeRef(
                location_type_id=location_type.id,
                component_uuid=flask.current_app.config['FEDERATION_UUID']
            )
        else:
            location_type_ref = LocationTypeRef(
                location_type_id=location_type.fed_id,
                component_uuid=location_type.component.uuid
            )
    else:
        location_type_ref = None
    responsible_users: typing.List[UserRef] = []
    if location.responsible_users:
        for responsible_user in location.responsible_users:
            if ('users', responsible_user.id) not in refs:
                refs.append(('users', responsible_user.id))
            if responsible_user.component is None or responsible_user.fed_id is None:
                responsible_user_ref = UserRef(
                    user_id=responsible_user.id,
                    component_uuid=flask.current_app.config['FEDERATION_UUID']
                )
            else:
                responsible_user_ref = UserRef(
                    user_id=responsible_user.fed_id,
                    component_uuid=responsible_user.component.uuid
                )
            responsible_users.append(responsible_user_ref)

    location_permissions_data = LocationPermissionsData(
        all_users='read' if location_permissions.location_is_public(location.id) else 'none'
    )
    return SharedLocationData(
        location_id=location.id if location.fed_id is None else location.fed_id,
        component_uuid=flask.current_app.config['FEDERATION_UUID'] if location.component is None else location.component.uuid,
        name=location.name,
        description=location.description,
        parent_location=parent_location,
        location_type=location_type_ref,
        responsible_users=responsible_users,
        permissions=location_permissions_data
    )


def locations_check_for_cyclic_dependencies(
        locations_data: typing.Dict[typing.Tuple[int, str], LocationData]
) -> None:
    def _location_check_for_cyclic_dependencies(
            location_data: LocationData,
            locations: typing.Dict[typing.Tuple[int, str], LocationData],
            path: typing.List[typing.Tuple[int, str]]
    ) -> None:
        if (location_data['fed_id'], location_data['component_uuid']) in path:
            # cyclic parent-location-chain
            raise errors.InvalidDataExportError(f'Cyclic parent location chain. Location: #{location_data["fed_id"]} @ {location_data["component_uuid"]} Path: {path}')
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
        if location.component is not None and location.fed_id is not None:
            if (location.fed_id, location.component.uuid) in data.keys():
                continue
            if location.parent_location_id is None:
                data[(location.fed_id, location.component.uuid)] = LocationData(
                    fed_id=location.fed_id,
                    component_uuid=location.component.uuid,
                    parent_location=None,
                    name=None,
                    description=None,
                    location_type=None,
                    responsible_users=[],
                    permissions={'all_users': 'none'},
                )
            else:
                parent_location = get_location(location.parent_location_id)
                if parent_location.component is not None and parent_location.fed_id is not None:
                    data[(location.fed_id, location.component.uuid)] = LocationData(
                        fed_id=location.fed_id,
                        component_uuid=location.component.uuid,
                        parent_location=LocationRef(
                            location_id=parent_location.fed_id,
                            component_uuid=parent_location.component.uuid
                        ),
                        name=None,
                        description=None,
                        location_type=None,
                        responsible_users=[],
                        permissions={'all_users': 'none'},
                    )
                else:
                    data[(location.fed_id, location.component.uuid)] = LocationData(
                        fed_id=location.fed_id,
                        component_uuid=location.component.uuid,
                        parent_location=LocationRef(
                            location_id=parent_location.id,
                            component_uuid=flask.current_app.config['FEDERATION_UUID']
                        ),
                        name=None,
                        description=None,
                        location_type=None,
                        responsible_users=[],
                        permissions={'all_users': 'none'},
                    )

        else:
            if location.parent_location_id is None:
                data[(location.id, flask.current_app.config['FEDERATION_UUID'])] = LocationData(
                    fed_id=location.id,
                    component_uuid=flask.current_app.config['FEDERATION_UUID'],
                    parent_location=None,
                    name=None,
                    description=None,
                    location_type=None,
                    responsible_users=[],
                    permissions={'all_users': 'none'},
                )
            else:
                parent_location = get_location(location.parent_location_id)
                if parent_location.component is not None and parent_location.fed_id is not None:
                    data[(location.id, flask.current_app.config['FEDERATION_UUID'])] = LocationData(
                        fed_id=location.id,
                        component_uuid=flask.current_app.config['FEDERATION_UUID'],
                        parent_location=LocationRef(
                            location_id=parent_location.fed_id,
                            component_uuid=parent_location.component.uuid
                        ),
                        name=None,
                        description=None,
                        location_type=None,
                        responsible_users=[],
                        permissions={'all_users': 'none'},
                    )
                else:
                    data[(location.id, flask.current_app.config['FEDERATION_UUID'])] = LocationData(
                        fed_id=location.id,
                        component_uuid=flask.current_app.config['FEDERATION_UUID'],
                        parent_location=LocationRef(
                            location_id=parent_location.id,
                            component_uuid=flask.current_app.config['FEDERATION_UUID']
                        ),
                        name=None,
                        description=None,
                        location_type=None,
                        responsible_users=[],
                        permissions={'all_users': 'none'},
                    )

    for _, location_data in data.items():
        _location_check_for_cyclic_dependencies(location_data, data, [])
