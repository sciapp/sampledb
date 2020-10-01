# coding: utf-8
"""
RESTful API for SampleDB
"""

from flask_restful import Resource

from .authentication import multi_auth
from ...logic.actions import get_action_types, get_action_type
from ...logic import errors

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def action_type_to_json(action_type):
    return {
        'type_id': action_type.id,
        'name': action_type.name,
        'object_name': action_type.object_name,
        'admin_only': action_type.admin_only
    }


class ActionType(Resource):
    @multi_auth.login_required
    def get(self, type_id: int):
        try:
            action_type = get_action_type(action_type_id=type_id)
        except errors.ActionTypeDoesNotExistError:
            return {
                "message": "action type {} does not exist".format(type_id)
            }, 404
        return action_type_to_json(action_type)


class ActionTypes(Resource):
    @multi_auth.login_required
    def get(self):
        action_types = get_action_types()
        return [action_type_to_json(action_type) for action_type in action_types]
