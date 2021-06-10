# coding: utf-8
"""
RESTful API for SampleDB
"""

import flask
from flask_restful import Resource

from .authentication import multi_auth
from ...logic import errors, users

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def user_to_json(user: users.User):
    user_json = {
        'user_id': user.id,
        'name': user.name,
        'orcid': user.orcid if user.orcid else None,
        'affiliation': user.affiliation if user.affiliation else None,
        'role': user.role if user.role else None
    }
    if flask.g.user.is_admin:
        user_json['email'] = user.email
    return user_json


class User(Resource):
    @multi_auth.login_required
    def get(self, user_id: int):
        try:
            user = users.get_user(user_id=user_id)
        except errors.UserDoesNotExistError:
            return {
                "message": "user {} does not exist".format(user_id)
            }, 404
        return user_to_json(user)


class CurrentUser(Resource):
    @multi_auth.login_required
    def get(self):
        return user_to_json(flask.g.user)


class Users(Resource):
    @multi_auth.login_required
    def get(self):
        return [user_to_json(user) for user in users.get_users()]
