import typing
from dataclasses import dataclass

import flask
from pydantic import BaseModel, Strict

from ...logic import errors
from ...logic.comments import (Comment, create_comment, get_comment_for_object,
                               get_comments_for_object)
from ...models import Permissions
from ..utils import Resource, ResponseData
from .authentication import object_permissions_required
from .validation_utils import is_expected_from_validation_info, validate, NonEmptyString, ValidatingError


@dataclass(frozen=True, slots=True)
class _ValidationContext:
    object_id: int


class _Comment(BaseModel):
    object_id: typing.Annotated[
        typing.Optional[int],
        Strict(),
        is_expected_from_validation_info(lambda info: info.context.object_id, allow_none=True),
    ] = None
    content: NonEmptyString


def comment_to_json(comment: Comment) -> typing.Dict[str, typing.Any]:
    comment_json = {
        'object_id': comment.object_id,
        'comment_id': comment.id,
        'user_id': comment.user_id,
        'utc_datetime': comment.utc_datetime.replace(tzinfo=None).isoformat(timespec='microseconds') if comment.utc_datetime is not None else None,
        'content': comment.content
    }
    return comment_json


class ObjectComment(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, comment_id: int) -> ResponseData:
        try:
            comment = get_comment_for_object(object_id=object_id, comment_id=comment_id)
        except errors.CommentDoesNotExistError:
            return {
                "message": f"comment {comment_id} of object {object_id} does not exist"
            }, 404
        return comment_to_json(comment)


class ObjectComments(Resource):
    @object_permissions_required(Permissions.WRITE)
    def post(self, object_id: int) -> ResponseData:
        request_json = flask.request.get_json(force=True)
        try:
            request_data = validate(
                _Comment,
                request_json,
                context=_ValidationContext(object_id),
            )
        except ValidatingError as e:
            return e.response
        comment_id = create_comment(object_id, flask.g.user.id, request_data.content)

        comment_url = flask.url_for(
            'api.object_comment',
            object_id=object_id,
            comment_id=comment_id,
            _external=True
        )
        return flask.redirect(comment_url, code=201)

    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        return [
            comment_to_json(comment)
            for comment in get_comments_for_object(object_id)
        ]
