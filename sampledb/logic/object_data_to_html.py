import typing

import flask
import flask_login

from ..models import Object, Permissions
from .object_permissions import get_object_if_user_has_permissions


def _get_object_if_current_user_has_read_permissions(object_id: int, component_uuid: typing.Optional[str] = None) -> typing.Optional[Object]:
    return get_object_if_user_has_permissions(
        user_id=flask_login.current_user.id,
        permissions=Permissions.READ,
        object_id=object_id,
        component_uuid=component_uuid,
    )


def object_data_to_html(
        *,
        object_id: int,
        metadata_language: typing.Optional[str],
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any],
        files: typing.List[typing.Any],
        id_prefix_root: str,
        workflow_display_mode: bool = False
) -> str:
    """
    Render the object data to HTML.

    :param object_id: the ID of the object being rendered
    :param metadata_language: the metadata language code
    :param data: the object data
    :param schema: the object schema
    :param files: the files for the object
    :param id_prefix_root: the ID prefix root
    :param workflow_display_mode: whether the object is in workflow display mode
    :return: the rendered HTML
    """
    html = flask.render_template(
        'objects/view/standalone_object_metadata.html',
        object_id=object_id,
        data=data,
        schema=schema,
        metadata_language=metadata_language,
        diff=None,
        previous_schema=None,
        indent_level=0,
        show_indent_border=False,
        property_path=(),
        get_object_if_current_user_has_read_permissions=_get_object_if_current_user_has_read_permissions,
        id_prefix_root=id_prefix_root,
        id_prefix=id_prefix_root + '_',
        workflow_display_mode=workflow_display_mode,
        files=files,
    )
    return html
