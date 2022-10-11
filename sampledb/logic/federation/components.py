import typing

import flask

from .. import errors
from ..components import add_component, get_component_by_uuid


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
