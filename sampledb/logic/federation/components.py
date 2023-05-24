import typing

import flask

from .. import errors
from ..components import add_component, get_component_by_uuid, Component, ComponentInfo, add_or_update_component_info
from .utils import _get_uuid, _get_str, _get_int, _get_bool
from ..components import validate_address, MAX_COMPONENT_ADDRESS_LENGTH, MAX_COMPONENT_NAME_LENGTH


def _get_or_create_component_id(
        component_uuid: str
) -> typing.Optional[int]:
    if component_uuid == flask.current_app.config['FEDERATION_UUID']:
        return None
    try:
        component = get_component_by_uuid(component_uuid)
    except errors.ComponentDoesNotExistError:
        component = add_component(uuid=component_uuid, description='', name=None, address=None)
    return component.id


class ComponentData(typing.TypedDict):
    uuid: str
    source_uuid: str
    name: typing.Optional[str]
    address: typing.Optional[str]
    discoverable: bool
    distance: int


def parse_component_info(
        component_data: typing.Dict[str, typing.Any],
        component: Component
) -> ComponentData:
    address = _get_str(component_data.get('address'))
    if address is not None:
        try:
            address = validate_address(
                address,
                max_length=MAX_COMPONENT_ADDRESS_LENGTH,
                allow_http=flask.current_app.config['ALLOW_HTTP']
            )
        except Exception:
            address = None
    name = _get_str(component_data.get('name'))
    if name is not None:
        if len(name) > MAX_COMPONENT_NAME_LENGTH:
            name = name[:MAX_COMPONENT_NAME_LENGTH]
    return ComponentData(
        uuid=_get_uuid(component_data.get('uuid')),
        source_uuid=_get_uuid(component_data.get('source_uuid')),
        name=name,
        address=address,
        discoverable=_get_bool(component_data.get('discoverable'), mandatory=True),
        distance=_get_int(component_data.get('distance'), mandatory=True)
    )


def import_component_info(
        component_data: ComponentData,
        component: Component
) -> ComponentInfo:
    return add_or_update_component_info(
        uuid=component_data['uuid'],
        source_uuid=component_data['source_uuid'],
        name=component_data['name'],
        address=component_data['address'],
        discoverable=component_data['discoverable'],
        distance=component_data['distance']
    )


def parse_import_component_info(
        component_data: typing.Dict[str, typing.Any],
        component: Component
) -> ComponentInfo:
    return import_component_info(parse_component_info(component_data, component), component)
