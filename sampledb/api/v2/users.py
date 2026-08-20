# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask
from pydantic import BaseModel, Field

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic import errors, users
from .utils.validation import method

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def user_to_json(user: users.User) -> typing.Dict[str, typing.Any]:
    user_json = {
        'user_id': user.id,
        'name': user.name,
        'orcid': user.orcid if user.orcid else None,
        'affiliation': user.affiliation if user.affiliation else None,
        'role': user.role if user.role else None
    }
    if flask.g.user.is_admin:
        user_json['email'] = user.email
        user_json['is_hidden'] = user.is_hidden
        user_json['is_active'] = user.is_active
        user_json['is_readonly'] = user.is_readonly
    return user_json


class User(Resource):
    class PathModel(BaseModel):
        user_id: int = Field(description="the ID of an existing user", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get a user.
        """
        try:
            user = users.get_user(user_id=path.user_id)
        except errors.UserDoesNotExistError:
            return {
                "message": f"user {path.user_id} does not exist"
            }, 404
        return user_to_json(user)


class CurrentUser(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> ResponseData:
        """
        Get the currently authenticated user.
        """
        return user_to_json(flask.g.user)


class Users(Resource):
    class QueryModel(BaseModel):
        filter_hidden: typing.Optional[bool] = Field(None, description="whether to filter for only hidden or only non-hidden users", examples=[False])
        filter_active: typing.Optional[bool] = Field(None, description="whether to filter for only active or only non-active users", examples=[True])
        filter_readonly: typing.Optional[bool] = Field(None, description="whether to filter for only readonly or only non-readonly users", examples=[False])

    @multi_auth.login_required
    @method()
    def get(self, query: QueryModel) -> ResponseData:
        """
        List all users.
        """
        filtered_users = users.get_users()
        if flask.g.user.is_admin:
            for filter_value, filter_attr in [
                (query.filter_hidden, 'is_hidden'),
                (query.filter_active, 'is_active'),
                (query.filter_readonly, 'is_readonly'),
            ]:
                if filter_value is None:
                    continue
                filtered_users = [
                    user
                    for user in filtered_users
                    if getattr(user, filter_attr) == filter_value
                ]
        return [
            user_to_json(user)
            for user in filtered_users
        ]
