import base64
import binascii
import typing

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
    if get_markdown_image(filename, None, component.id) is None:
        md_image = MarkdownImage(filename, data, None, permanent=True, component_id=component.id)
        db.session.add(md_image)
        db.session.commit()


def parse_import_markdown_image(
        markdown_image_data: typing.Tuple[str, bytes],
        component: Component
) -> None:
    return import_markdown_image(parse_markdown_image(markdown_image_data, component), component)
