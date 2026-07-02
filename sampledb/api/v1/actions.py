# coding: utf-8
"""
RESTful API for SampleDB
"""
import json
import typing

import flask

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic.actions import get_action, update_action
from ...logic.action_translations import set_action_translation
from ...logic.languages import Language
from ...logic.action_permissions import get_user_action_permissions, get_actions_with_permissions
from ...logic import errors, utils, actions, action_types
from ...logic.schemas.templates import find_invalid_template_paths
from ...logic.schemas.validate_schema import validate_schema
from ...models import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def action_to_json(action: actions.Action) -> typing.Dict[str, typing.Any]:
    return {
        'action_id': action.id,
        'instrument_id': action.instrument_id if not flask.current_app.config['DISABLE_INSTRUMENTS'] else None,
        'user_id': action.user_id,
        'type': {
            action_types.ActionType.SAMPLE_CREATION: 'sample',
            action_types.ActionType.MEASUREMENT: 'measurement',
            action_types.ActionType.SIMULATION: 'simulation'
        }.get(action.type_id, 'custom') if action.type_id is not None else 'custom',
        'type_id': action.type_id,
        'name': utils.get_translated_text(
            action.name,
            language_code='en'
        ) or None,
        'description': utils.get_translated_text(
            action.description,
            language_code='en'
        ) or None,
        'is_hidden': action.is_hidden,
        'schema': action.schema
    }


class Action(Resource):
    @multi_auth.login_required
    def get(self, action_id: int) -> ResponseData:
        try:
            action = get_action(
                action_id=action_id
            )
        except errors.ActionDoesNotExistError:
            return {
                "message": f"action {action_id} does not exist"
            }, 404
        if Permissions.READ not in get_user_action_permissions(action_id=action_id, user_id=flask.g.user.id):
            return flask.abort(403)
        return action_to_json(action)

    @multi_auth.login_required
    def post(self, action_id: int) -> ResponseData:
        try:
            action = get_action(
                action_id=action_id
            )
        except errors.ActionDoesNotExistError:
            return {
                "message": f"action {action_id} does not exist"
            }, 404
        if Permissions.WRITE not in get_user_action_permissions(action_id=action_id, user_id=flask.g.user.id):
            return flask.abort(403)
        if action.fed_id is not None:
            return flask.abort(403)
        action_json = action_to_json(action)
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, dict):
            return {
                "message": "JSON object body required"
            }, 400
        name = action.name.get('en')
        description = action.description.get('en')
        short_description = action.short_description.get('en')
        schema = action.schema
        is_hidden = action.is_hidden
        for key in request_json:
            if key not in action_json:
                return {
                    "message": f"invalid key '{key}'"
                }, 400
            if isinstance(request_json[key], str) and '\0' in request_json[key]:
                return {
                    "message": f"{key} must not contain NULL"
                }, 400
            if key == 'name':
                if not isinstance(request_json['name'], str):
                    return {
                        "message": "name must be string"
                    }, 400
                if len(request_json['name']) < 1 or len(request_json['name']) > 100:
                    return {
                        "message": "name must be between 1 and 100 characters long"
                    }, 400
                name = request_json['name']
            elif key == 'description':
                if not isinstance(request_json['description'], str):
                    return {
                        "message": "description must be string"
                    }, 400
                description = request_json['description']
            elif key == 'is_hidden':
                if not isinstance(request_json['is_hidden'], bool):
                    return {
                        "message": "is_hidden must be boolean"
                    }, 400
                is_hidden = request_json['is_hidden']
            elif key == 'schema':
                if not isinstance(request_json['schema'], dict):
                    return {
                        "message": "schema must be dict"
                    }, 400
                schema = request_json['schema']
                error_message = None
                try:
                    invalid_template_paths = find_invalid_template_paths(schema, flask.g.user.id)
                    if invalid_template_paths:
                        raise errors.ValidationError('insufficient permissions for template action', invalid_template_paths[0])
                    validate_schema(schema, invalid_template_action_ids=[] if action is None else [action.id], strict=True)
                except errors.ValidationError as e:
                    error_message = e.message
                except Exception as e:
                    error_message = str(e)
                if error_message is not None:
                    return {
                        "message": error_message
                    }, 400
            else:
                if action_json[key] != request_json[key]:
                    return {
                        "message": f"{key} must be {json.dumps(action_json[key])}"
                    }, 400
        update_action(
            action_id=action_id,
            schema=schema,
            description_is_markdown=action.description_is_markdown,
            is_hidden=is_hidden,
            short_description_is_markdown=action.short_description_is_markdown,
        )
        set_action_translation(
            language_id=Language.ENGLISH,
            action_id=action_id,
            name=name or '',
            description=description or '',
            short_description=short_description or ''
        )
        action = get_action(action_id=action_id)
        return action_to_json(action)


class Actions(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        actions = get_actions_with_permissions(user_id=flask.g.user.id, permissions=Permissions.READ)
        return [
            action_to_json(action)
            for action in actions
        ]
