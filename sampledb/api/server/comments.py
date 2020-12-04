# coding: utf-8
"""
RESTful API for SampleDB
"""

import flask

from flask_restful import Resource

from .authentication import object_permissions_required, Permissions
from ...logic.comments import Comment, create_comment, get_comments_for_object, get_comment_for_object
from ...logic import errors

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def comment_to_json(comment: Comment):
    comment_json = {
        'object_id': comment.object_id,
        'comment_id': comment.id,
        'user_id': comment.user_id,
        'utc_datetime': comment.utc_datetime.isoformat(),
        'content': comment.content
    }
    return comment_json


class ObjectComment(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, comment_id: int):
        try:
            comment = get_comment_for_object(object_id=object_id, comment_id=comment_id)
        except errors.CommentDoesNotExistError:
            return {
                "message": "comment {} of object {} does not exist".format(comment_id, object_id)
            }, 404
        return comment_to_json(comment)


class ObjectComments(Resource):
    @object_permissions_required(Permissions.WRITE)
    def post(self, object_id: int):
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, dict):
            return {
                "message": "JSON object body required"
            }, 400
        if 'object_id' in request_json:
            if request_json['object_id'] != object_id:
                return {
                    "message": "object_id must be {}".format(object_id)
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
            comment_id=comment_id
        )
        return flask.redirect(comment_url, code=201)

    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int):
        return [
            comment_to_json(comment)
            for comment in get_comments_for_object(object_id)
        ]
