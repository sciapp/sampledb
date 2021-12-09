# coding: utf-8
"""
RESTful API for SampleDB
"""

import flask
from flask_restful import Resource

from .authentication import multi_auth
from ...logic.action_translations import get_action_with_translation_in_language
from ...logic.action_permissions import get_user_action_permissions, get_actions_with_permissions, Permissions
from ...logic.languages import Language
from ...logic import errors
from ...models.actions import ActionType

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def action_to_json(action):
    return {
        'action_id': action.id,
        'instrument_id': action.instrument_id,
        'user_id': action.user_id,
        'type': {
            ActionType.SAMPLE_CREATION: 'sample',
            ActionType.MEASUREMENT: 'measurement',
            ActionType.SIMULATION: 'simulation'
        }.get(action.type_id, 'custom'),
        'type_id': action.type_id,
        'name': action.translation.name,
        'description': action.translation.description,
        'is_hidden': action.is_hidden,
        'schema': action.schema
    }


class Action(Resource):
    @multi_auth.login_required
    def get(self, action_id: int):
        try:
            action = get_action_with_translation_in_language(
                action_id=action_id,
                language_id=Language.ENGLISH
            )
        except errors.ActionDoesNotExistError:
            return {
                "message": "action {} does not exist".format(action_id)
            }, 404
        if Permissions.READ not in get_user_action_permissions(action_id=action_id, user_id=flask.g.user.id):
            return {
                "message": "insufficient permissions to access action {}".format(action_id)
            }, 403
        return action_to_json(action)


class Actions(Resource):
    @multi_auth.login_required
    def get(self):
        actions = get_actions_with_permissions(user_id=flask.g.user.id, permissions=Permissions.READ)
        return [
            action_to_json(get_action_with_translation_in_language(
                action_id=action.id,
                language_id=Language.ENGLISH
            )) for action in actions
        ]
