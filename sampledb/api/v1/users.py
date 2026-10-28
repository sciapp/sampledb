# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic import errors, users
from ...utils import text_to_bool

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
    @multi_auth.login_required
    def get(self, user_id: int) -> ResponseData:
        try:
            user = users.get_user(user_id=user_id)
        except errors.UserDoesNotExistError:
            return {
                "message": f"user {user_id} does not exist"
            }, 404
        return user_to_json(user)


class CurrentUser(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        return user_to_json(flask.g.user)


class Users(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        filtered_users = users.get_users()
        if flask.g.user.is_admin:
            for filter_param, filter_attr in [
                ('filter_hidden', 'is_hidden'),
                ('filter_active', 'is_active'),
                ('filter_readonly', 'is_readonly'),
            ]:
                if filter_param not in flask.request.args:
                    continue
                filter_value = text_to_bool(flask.request.args.get(filter_param, ''))
                filtered_users = [
                    user
                    for user in filtered_users
                    if getattr(user, filter_attr) == filter_value
                ]
        return [
            user_to_json(user)
            for user in filtered_users
        ]
