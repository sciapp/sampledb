# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic import errors, groups, users


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


class GroupMemberUsers(Resource):
    @multi_auth.login_required
    def get(self, group_id: int) -> ResponseData:
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage groups"
            }, 403
        try:
            group_member_ids = groups.get_group_member_ids(group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {group_id} does not exist"
            }, 404
        return [{
            'user_id': user_id,
            'href': flask.url_for('api.user', user_id=user_id, _external=True),
        } for user_id in sorted(group_member_ids)]

    @multi_auth.login_required
    def post(self, group_id: int) -> ResponseData:
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage groups"
            }, 403
        if flask.g.user.is_readonly:
            return {
                "message": "Read-only users may not manage groups"
            }, 403
        try:
            group_member_ids = groups.get_group_member_ids(group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {group_id} does not exist"
            }, 404

        request_json = flask.request.get_json(force=True)
        user_id = request_json.get('user_id')
        if type(user_id) is not int:
            return {
                "message": "user_id must be int"
            }, 400
        if user_id in group_member_ids:
            return {
                "message": "user is already a member of this group"
            }, 400
        try:
            users.check_user_exists(user_id)
        except errors.UserDoesNotExistError:
            return {
                "message": "user does not exist"
            }, 400
        groups.add_user_to_group(group_id, user_id)
        return flask.redirect(flask.url_for('.group_member_user', group_id=group_id, user_id=user_id), code=201)


class GroupMemberUser(Resource):
    @multi_auth.login_required
    def get(self, group_id: int, user_id: int) -> ResponseData:
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage groups"
            }, 403
        try:
            group_member_ids = groups.get_group_member_ids(group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {group_id} does not exist"
            }, 404
        if user_id not in group_member_ids:
            return {
                "message": "user is not a member of this group"
            }, 404
        return {
            'user_id': user_id,
            'href': flask.url_for('api.user', user_id=user_id, _external=True),
        }

    @multi_auth.login_required
    def delete(self, group_id: int, user_id: int) -> ResponseData:
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage groups"
            }, 403
        if flask.g.user.is_readonly:
            return {
                "message": "Read-only users may not manage groups"
            }, 403
        try:
            group_member_ids = groups.get_group_member_ids(group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {group_id} does not exist"
            }, 404
        if user_id not in group_member_ids:
            return {
                "message": "user is not a member of this group"
            }, 404
        groups.remove_user_from_group(group_id, user_id)
        return {
            "message": f"user {user_id} has been removed from group {group_id}"
        }, 200
