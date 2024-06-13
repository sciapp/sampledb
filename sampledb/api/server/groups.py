# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic import errors, groups


def group_to_json(group: groups.Group) -> typing.Dict[str, typing.Any]:
    return {
        'group_id': group.id,
        'name': group.name,
        'description': group.description,
        'member_users': [{
            'user_id': user_id,
            'href': flask.url_for('api.user', user_id=user_id, _external=True),
        } for user_id in sorted(groups.get_group_member_ids(group_id=group.id))]
    }


class Groups(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        return [
            group_to_json(group)
            for group in sorted(groups.get_groups(), key=lambda group: group.id)
        ]


class Group(Resource):
    @multi_auth.login_required
    def get(self, group_id: int) -> ResponseData:
        try:
            group = groups.get_group(group_id=group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {group_id} does not exist"
            }, 404
        return group_to_json(group)
