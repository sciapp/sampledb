import typing
from dataclasses import dataclass

import flask
from pydantic import BaseModel, Strict, Field

from ...logic import errors
from ...logic.comments import Comment, create_comment, get_comment_for_object, get_comments_for_object
from ...models import Permissions
from ..utils import Resource, ResponseData
from .authentication import object_permissions_required
from .utils.validation import is_expected_from_validation_info, NonEmptyString, method


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
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])
        comment_id: int = Field(description="the ID of an existing comment for this object", examples=[2])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get a comment.
        """
        try:
            comment = get_comment_for_object(object_id=path.object_id, comment_id=path.comment_id)
        except errors.CommentDoesNotExistError:
            return {
                "message": f"comment {path.comment_id} of object {path.object_id} does not exist"
            }, 404
        return comment_to_json(comment)


class ObjectComments(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(..., title='Object ID', description='The ID of an existing object.', examples=[1])

    @dataclass(frozen=True, slots=True)
    class ValidationContext:
        object_id: int

        @classmethod
        def from_path_model(cls, path: ObjectComments.PathModel) -> typing.Self:
            return cls(
                object_id=path.object_id,
            )

    class RequestBodyModel(BaseModel):
        object_id: typing.Annotated[
            typing.Optional[int],
            Strict(),
            is_expected_from_validation_info(lambda info: info.context.object_id, allow_none=True),
        ] = Field(None, title='Object ID', description='the ID of an existing object, must be the same ID as in the path.', examples=[1])
        content: NonEmptyString = Field(description="the content of the comment to create", examples=["This is the comment."])

    @object_permissions_required(Permissions.WRITE)
    @method(request_body_context_builder=ValidationContext.from_path_model)
    def post(self, path: PathModel, request_body: RequestBodyModel) -> ResponseData:
        """
        Post a new comment for an object.
        """
        comment_id = create_comment(path.object_id, flask.g.user.id, request_body.content)
        comment_url = flask.url_for(
            '.object_comment',
            object_id=path.object_id,
            comment_id=comment_id,
            _external=True
        )
        return flask.redirect(comment_url, code=201)

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get all comments for an object.
        """
        return [
            comment_to_json(comment)
            for comment in get_comments_for_object(path.object_id)
        ]
