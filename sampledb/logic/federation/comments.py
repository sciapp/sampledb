from datetime import datetime
import typing

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_utc_datetime, _get_str, _get_dict
from .users import _parse_user_ref, _get_or_create_user_id, UserRef
from ..comments import get_comment, create_comment, update_comment, Comment
from ..components import Component
from .. import errors, fed_logs, object_log
from ...models import Object


class CommentData(typing.TypedDict):
    fed_id: int
    component_uuid: str
    user: typing.Optional[UserRef]
    content: str
    utc_datetime: datetime


def parse_comment(
        comment_data: typing.Dict[str, typing.Any]
) -> CommentData:
    uuid = _get_uuid(comment_data.get('component_uuid'))
    fed_id = _get_id(comment_data.get('comment_id'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError(f'Invalid update for local comment #{fed_id}')
    return CommentData(
        fed_id=fed_id,
        component_uuid=uuid,
        user=_parse_user_ref(_get_dict(comment_data.get('user'))),
        content=_get_str(comment_data.get('content'), mandatory=True, allow_empty=False),
        utc_datetime=_get_utc_datetime(comment_data.get('utc_datetime'), mandatory=True)
    )


def import_comment(
        comment_data: CommentData,
        object: Object,
        component: Component
) -> Comment:
    component_id = _get_or_create_component_id(comment_data['component_uuid'])
    assert component_id is not None
    # component_id will only be None if this would import a local comment

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
        assert component_id is not None
        comment = get_comment(create_comment(
            object_id=object.object_id,
            user_id=user_id,
            content=comment_data['content'],
            utc_datetime=comment_data['utc_datetime'],
            fed_id=comment_data['fed_id'],
            component_id=component_id
        ))
        fed_logs.import_comment(comment.id, component.id)
        if user_id is not None:
            object_log.post_comment(user_id=user_id, object_id=comment.object_id, comment_id=comment.id, utc_datetime=comment_data['utc_datetime'], is_imported=True)
    return comment


def parse_import_comment(
        comment_data: typing.Dict[str, typing.Any],
        object: Object,
        component: Component
) -> Comment:
    return import_comment(parse_comment(comment_data), object, component)
