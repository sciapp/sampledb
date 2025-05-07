import base64
import binascii
import typing

import flask

from .components import _get_or_create_component_id
from ..markdown_images import get_markdown_image
from ..components import Component
from .. import errors
from ...models import MarkdownImage
from ... import db


def parse_markdown_image(
        markdown_image_data: typing.Tuple[str, bytes],
        component: Component
) -> typing.Tuple[str, bytes]:
    filename, data = markdown_image_data
    try:
        md_image_data = base64.b64decode(data)
    except binascii.Error:
        raise errors.InvalidDataExportError(f'Invalid markdown image \'{filename}\'')
    return filename, md_image_data


def import_markdown_image(
        markdown_image_data: typing.Tuple[str, bytes],
        component: Component
) -> None:
    filename, data = markdown_image_data
    component_id: typing.Optional[int] = component.id
    pure_filename = filename
    if '/' in filename:
        component_uuid, pure_filename = filename.split('/')
        if component_uuid == flask.current_app.config['FEDERATION_UUID']:
            component_id = None
        else:
            component_id = _get_or_create_component_id(component_uuid=component_uuid)

    if get_markdown_image(pure_filename, None, component_id) is None:
        md_image = MarkdownImage(pure_filename, data, None, permanent=True, component_id=component_id)
        db.session.add(md_image)
        db.session.commit()


def parse_import_markdown_image(
        markdown_image_data: typing.Tuple[str, bytes],
        component: Component
) -> None:
    return import_markdown_image(parse_markdown_image(markdown_image_data, component), component)
