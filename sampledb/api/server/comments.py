# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask

from .authentication import object_permissions_required
from ..utils import Resource, ResponseData
from ...logic.comments import Comment, create_comment, get_comments_for_object, get_comment_for_object
from ...logic import errors
from ...models import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


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
        if not isinstance(request_json, dict):
            return {
                "message": "JSON object body required"
            }, 400
        if 'object_id' in request_json:
            if request_json['object_id'] != object_id:
                return {
                    "message": f"object_id must be {object_id}"
                }, 400
        if 'content' not in request_json:
            return {
                "message": "content must be set"
            }, 400
        content = request_json['content']
        if not isinstance(content, str):
            return {
                "message": "content must be a string"
            }, 400
        if not content:
            return {
                "message": "content must not be empty"
            }, 400
        comment_id = create_comment(object_id, flask.g.user.id, content)

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
