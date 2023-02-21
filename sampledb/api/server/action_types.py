# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic.action_types import get_action_types, get_action_type
from ...logic import errors, utils, action_types

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def action_type_to_json(action_type: action_types.ActionType) -> typing.Dict[str, typing.Any]:
    return {
        'type_id': action_type.id,
        'name': utils.get_translated_text(
            action_type.name,
            language_code='en',
            default='Unnamed Action Type'
        ),
        'object_name': utils.get_translated_text(
            action_type.object_name,
            language_code='en',
            default='Object'
        ),
        'admin_only': action_type.admin_only
    }


class ActionType(Resource):
    @multi_auth.login_required
    def get(self, type_id: int) -> ResponseData:
        try:
            action_type = get_action_type(
                action_type_id=type_id
            )
        except errors.ActionTypeDoesNotExistError:
            return {
                "message": f"action type {type_id} does not exist"
            }, 404
        return action_type_to_json(action_type)


class ActionTypes(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        action_types = get_action_types()
        return [
            action_type_to_json(action_type)
            for action_type in action_types
        ]
