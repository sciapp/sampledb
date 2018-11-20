# coding: utf-8
"""
RESTful API for iffSamples
"""

from flask_restful import Resource

from sampledb.api.server.authentication import http_basic_auth
from sampledb.logic.actions import get_action, get_actions, ActionType
from sampledb.logic import errors

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def action_to_json(action):
    return {
        'action_id': action.id,
        'instrument_id': action.instrument_id,
        'type': {
            ActionType.SAMPLE_CREATION: 'sample',
            ActionType.MEASUREMENT: 'measurement',
            ActionType.SIMULATION: 'simulation',
        }.get(action.type, 'unknown'),
        'name': action.name,
        'description': action.description,
        'schema': action.schema
    }


class Action(Resource):
    @http_basic_auth.login_required
    def get(self, action_id: int):
        try:
            action = get_action(action_id=action_id)
        except errors.ActionDoesNotExistError:
            return {
                "message": "action {} does not exist".format(action_id)
            }, 404
        return action_to_json(action)


class Actions(Resource):
    @http_basic_auth.login_required
    def get(self):
        actions = get_actions()
        return [action_to_json(action) for action in actions]
