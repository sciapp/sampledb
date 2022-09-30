import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_utc_datetime, _get_str, _get_dict
from .users import _parse_user_ref, _get_or_create_user_id
from ..comments import get_comment, create_comment, update_comment
from .. import errors, fed_logs


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


def parse_import_comment(comment_data, object, component):
    return import_comment(parse_comment(comment_data), object, component)
