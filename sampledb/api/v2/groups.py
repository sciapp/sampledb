import typing

import flask
from pydantic import BaseModel, Field

from ...logic import errors, groups
from ..utils import Resource, ResponseData
from .authentication import multi_auth
from .utils.validation import UserId, method


def group_to_json(group: groups.Group) -> typing.Dict[str, typing.Any]:
    return {
        'group_id': group.id,
        'name': group.name,
        'description': group.description,
        'member_users': [{
            'user_id': user_id,
            'href': flask.url_for('.user', user_id=user_id, _external=True),
        } for user_id in sorted(groups.get_group_member_ids(group_id=group.id))]
    }


class Groups(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> ResponseData:
        """
        List all basic groups.
        """
        return [
            group_to_json(group)
            for group in sorted(groups.get_groups(), key=lambda group: group.id)
        ]


class Group(Resource):
    class PathModel(BaseModel):
        group_id: int = Field(description="the ID of an existing basic group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get a basic group.
        """
        try:
            group = groups.get_group(group_id=path.group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {path.group_id} does not exist"
            }, 404
        return group_to_json(group)


class GroupMemberUsers(Resource):
    class PathModel(BaseModel):
        group_id: int = Field(description="the ID of an existing basic group", examples=[1])

    class RequestBodyModel(BaseModel):
        user_id: UserId = Field(description="the ID of an existing user to add to the basic group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        List all member users of a basic group.
        """
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage groups"
            }, 403
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {path.group_id} does not exist"
            }, 404
        return [{
            'user_id': user_id,
            'href': flask.url_for('.user', user_id=user_id, _external=True),
        } for user_id in sorted(group_member_ids)]

    @multi_auth.login_required
    @method()
    def post(self, path: PathModel, request_body: RequestBodyModel) -> ResponseData:
        """
        Add a user to a basic group.
        """
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage groups"
            }, 403
        if flask.g.user.is_readonly:
            return {
                "message": "Read-only users may not manage groups"
            }, 403
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {path.group_id} does not exist"
            }, 404
        user_id = request_body.user_id
        if user_id in group_member_ids:
            return {
                "message": "user is already a member of this group"
            }, 400
        groups.add_user_to_group(path.group_id, user_id)
        return flask.redirect(flask.url_for('.group_member_user', group_id=path.group_id, user_id=user_id), code=201)


class GroupMemberUser(Resource):
    class PathModel(BaseModel):
        group_id: int = Field(description="the ID of an existing basic group", examples=[1])
        user_id: int = Field(description="the ID of an existing user", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get a member user of a basic group.
        """
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage groups"
            }, 403
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {path.group_id} does not exist"
            }, 404
        if path.user_id not in group_member_ids:
            return {
                "message": "user is not a member of this group"
            }, 404
        return {
            'user_id': path.user_id,
            'href': flask.url_for('.user', user_id=path.user_id, _external=True),
        }

    @multi_auth.login_required
    @method()
    def delete(self, path: PathModel) -> ResponseData:
        """
        Remove a user from a basic group.
        """
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage groups"
            }, 403
        if flask.g.user.is_readonly:
            return {
                "message": "Read-only users may not manage groups"
            }, 403
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {path.group_id} does not exist"
            }, 404
        if path.user_id not in group_member_ids:
            return {
                "message": "user is not a member of this group"
            }, 404
        groups.remove_user_from_group(path.group_id, path.user_id)
        return {
            "message": f"user {path.user_id} has been removed from group {path.group_id}"
        }, 200
