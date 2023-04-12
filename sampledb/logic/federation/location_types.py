import typing

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_bool, _get_translation
from ..locations import get_location_type, create_location_type, update_location_type, LocationType
from ..components import Component
from .. import errors, fed_logs


class LocationTypeRef(typing.TypedDict):
    location_type_id: int
    component_uuid: str


class LocationTypeData(typing.TypedDict):
    fed_id: int
    component_uuid: str
    name: typing.Optional[typing.Dict[str, str]]
    location_name_singular: typing.Optional[typing.Dict[str, str]]
    location_name_plural: typing.Optional[typing.Dict[str, str]]
    admin_only: bool
    enable_parent_location: bool
    enable_sub_locations: bool
    enable_object_assignments: bool
    enable_responsible_users: bool
    show_location_log: bool


class SharedLocationTypeData(typing.TypedDict):
    location_type_id: int
    component_uuid: str
    name: typing.Optional[typing.Dict[str, str]]
    location_name_singular: typing.Optional[typing.Dict[str, str]]
    location_name_plural: typing.Optional[typing.Dict[str, str]]
    admin_only: bool
    enable_parent_location: bool
    enable_sub_locations: bool
    enable_object_assignments: bool
    enable_responsible_users: bool
    show_location_log: bool


def import_location_type(
        location_type_data: LocationTypeData,
        component: Component
) -> LocationType:
    component_id = _get_or_create_component_id(location_type_data['component_uuid'])

    try:
        location_type = get_location_type(location_type_data['fed_id'], component_id)

        ignored_keys = {
            'fed_id',
            'component_uuid'
        }
        if any(
                value != getattr(location_type, key)
                for key, value in location_type_data.items()
                if key not in ignored_keys
        ):
            update_location_type(
                location_type_id=location_type.id,
                name=location_type_data['name'],
                location_name_singular=location_type_data['location_name_singular'],
                location_name_plural=location_type_data['location_name_plural'],
                admin_only=location_type_data['admin_only'],
                enable_parent_location=location_type_data['enable_parent_location'],
                enable_sub_locations=location_type_data['enable_sub_locations'],
                enable_object_assignments=location_type_data['enable_object_assignments'],
                enable_responsible_users=location_type_data['enable_responsible_users'],
                enable_instruments=False,
                enable_capacities=False,
                show_location_log=location_type_data['show_location_log'],
            )
            fed_logs.update_location_type(location_type.id, component.id)
    except errors.LocationTypeDoesNotExistError:
        location_type = create_location_type(
            name=location_type_data['name'],
            location_name_singular=location_type_data['location_name_singular'],
            location_name_plural=location_type_data['location_name_plural'],
            admin_only=location_type_data['admin_only'],
            enable_parent_location=location_type_data['enable_parent_location'],
            enable_sub_locations=location_type_data['enable_sub_locations'],
            enable_object_assignments=location_type_data['enable_object_assignments'],
            enable_responsible_users=location_type_data['enable_responsible_users'],
            enable_instruments=False,
            enable_capacities=False,
            show_location_log=location_type_data['show_location_log'],
            fed_id=location_type_data['fed_id'],
            component_id=component_id,
        )
        fed_logs.import_location_type(location_type.id, component.id)
    return location_type


def parse_import_location_type(
        location_type_data: typing.Dict[str, typing.Any],
        component: Component
) -> LocationType:
    return import_location_type(parse_location_type(location_type_data), component)


def parse_location_type(
        location_type_data: typing.Dict[str, typing.Any]
) -> LocationTypeData:
    fed_id = _get_id(location_type_data.get('location_type_id'), special_values=[LocationType.LOCATION])
    uuid = _get_uuid(location_type_data.get('component_uuid'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError(f'Invalid update for local location type {fed_id}')
    return LocationTypeData(
        fed_id=fed_id,
        component_uuid=uuid,
        name=_get_translation(location_type_data.get('name')),
        location_name_singular=_get_translation(location_type_data.get('location_name_singular')),
        location_name_plural=_get_translation(location_type_data.get('location_name_plural')),
        admin_only=_get_bool(location_type_data.get('admin_only'), default=True),
        enable_parent_location=_get_bool(location_type_data.get('enable_parent_location'), default=False),
        enable_sub_locations=_get_bool(location_type_data.get('enable_sub_locations'), default=False),
        enable_object_assignments=_get_bool(location_type_data.get('enable_object_assignments'), default=False),
        enable_responsible_users=_get_bool(location_type_data.get('enable_responsible_users'), default=False),
        show_location_log=_get_bool(location_type_data.get('show_location_log'), default=False),
    )


def _parse_location_type_ref(
        location_type_data: typing.Optional[typing.Union[LocationTypeRef, typing.Dict[str, typing.Any]]]
) -> typing.Optional[LocationTypeRef]:
    if location_type_data is None:
        return None
    location_type_id = _get_id(location_type_data.get('location_type_id'), special_values=[LocationType.LOCATION])
    component_uuid = _get_uuid(location_type_data.get('component_uuid'))
    return LocationTypeRef(
        location_type_id=location_type_id,
        component_uuid=component_uuid
    )


@typing.overload
def _get_or_create_location_type_id(
        location_type_data: LocationTypeRef
) -> int:
    ...


@typing.overload
def _get_or_create_location_type_id(
        location_type_data: None
) -> None:
    ...


def _get_or_create_location_type_id(
        location_type_data: typing.Optional[LocationTypeRef]
) -> typing.Optional[int]:
    if location_type_data is None:
        return None
    component_id = _get_or_create_component_id(location_type_data['component_uuid'])
    try:
        location_type = get_location_type(location_type_data['location_type_id'], component_id)
    except errors.LocationTypeDoesNotExistError:
        assert component_id is not None
        location_type = create_location_type(
            name=None,
            location_name_singular=None,
            location_name_plural=None,
            admin_only=True,
            enable_sub_locations=False,
            enable_parent_location=False,
            enable_object_assignments=False,
            enable_responsible_users=False,
            enable_instruments=False,
            enable_capacities=False,
            show_location_log=False,
            fed_id=location_type_data['location_type_id'],
            component_id=component_id
        )
        fed_logs.create_ref_location_type(location_type.id, component_id)
    return location_type.id


def shared_location_type_preprocessor(
        location_type_id: int,
        _component: Component,
        _refs: typing.List[typing.Tuple[str, int]],
        _markdown_images: typing.Dict[str, str]
) -> typing.Optional[SharedLocationTypeData]:
    location_type = get_location_type(location_type_id)
    if location_type.component_id is not None:
        return None
    return SharedLocationTypeData(
        location_type_id=location_type.id if location_type.fed_id is None else location_type.fed_id,
        component_uuid=flask.current_app.config['FEDERATION_UUID'] if location_type.component is None else location_type.component.uuid,
        name=location_type.name,
        location_name_singular=location_type.location_name_singular,
        location_name_plural=location_type.location_name_plural,
        admin_only=location_type.admin_only,
        enable_parent_location=location_type.enable_parent_location,
        enable_sub_locations=location_type.enable_sub_locations,
        enable_object_assignments=location_type.enable_object_assignments,
        enable_responsible_users=location_type.enable_responsible_users,
        show_location_log=location_type.show_location_log,
    )
