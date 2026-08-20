# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

from pydantic import BaseModel, Field

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic.action_types import get_action_types, get_action_type
from ...logic import errors, utils, action_types
from .utils.validation import method

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
    class PathModel(BaseModel):
        type_id: int = Field(description="the ID of an existing action type", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get an action type.
        """
        try:
            action_type = get_action_type(
                action_type_id=path.type_id
            )
        except errors.ActionTypeDoesNotExistError:
            return {
                "message": f"action type {path.type_id} does not exist"
            }, 404
        return action_type_to_json(action_type)


class ActionTypes(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> ResponseData:
        """
        List all action types.
        """
        action_types = get_action_types()
        return [
            action_type_to_json(action_type)
            for action_type in action_types
        ]
