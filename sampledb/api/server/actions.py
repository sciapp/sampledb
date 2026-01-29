import typing
from dataclasses import dataclass

import flask
from pydantic import AfterValidator, Field, Strict, ValidationInfo
from pydantic_core import PydanticCustomError

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic.action_translations import set_action_translation
from ...logic.actions import Action as LogicAction
from ...logic.actions import get_action, update_action
from ...logic.languages import Language
from ...logic.action_permissions import get_user_action_permissions, get_actions_with_permissions
from ...logic import errors, utils, actions, action_types
from ...logic.schemas.templates import find_invalid_template_paths
from ...logic.schemas.validate_schema import validate_schema
from ...models import Permissions
from .validation_utils import (ModelWithDefaultsFromValidationInfo,
                               OptionalNotNone, ValidatingError,
                               populate_missing_or_expect_from_validation_info,
                               validate)


@dataclass
class _ValidationContext:
    action: LogicAction
    action_type: str


def _is_valid_schema(schema: typing.Dict[str, typing.Any], info: ValidationInfo[_ValidationContext]) -> typing.Dict[str, typing.Any]:
    try:
        invalid_template_paths = find_invalid_template_paths(schema, flask.g.user.id)
        if invalid_template_paths:
            raise errors.ValidationError('insufficient permissions for template action', invalid_template_paths[0])
        validate_schema(schema, invalid_template_action_ids=[info.context.action.id], strict=True)
        return schema
    except errors.ValidationError as e:
        raise PydanticCustomError("action_parsing", e.message)
    except Exception as e:
        raise PydanticCustomError("action_parsing", str(e))


class _Action(ModelWithDefaultsFromValidationInfo):
    action_id: typing.Annotated[int, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.action.id)]
    instrument_id: typing.Annotated[
        typing.Optional[int],
        Strict(),
        populate_missing_or_expect_from_validation_info(
            lambda i: (
                None
                if flask.current_app.config["DISABLE_INSTRUMENTS"]
                else i.context.action.instrument_id
            )
        ),
    ]
    user_id: typing.Annotated[typing.Optional[int], Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.action.user_id)]
    type: typing.Annotated[typing.Optional[str], populate_missing_or_expect_from_validation_info(lambda i: i.context.action_type)]
    type_id: typing.Annotated[typing.Optional[int], Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.action.type_id)]
    name: typing.Annotated[OptionalNotNone[str], Field(min_length=1, max_length=100)]
    description: OptionalNotNone[str]
    is_hidden: OptionalNotNone[bool]
    action_schema: typing.Annotated[
        OptionalNotNone[typing.Dict[str, typing.Any]],
        AfterValidator(_is_valid_schema),
        Field(validation_alias="schema"),
    ]


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
        try:
            request_data = validate(_Action, request_json, context=_ValidationContext(action, action_json["type"]))
        except ValidatingError as e:
            return e.response
        update_action(
            action_id=action_id,
            schema=action.schema if request_data.action_schema is None else request_data.action_schema,
            description_is_markdown=action.description_is_markdown,
            is_hidden=action.is_hidden if request_data.is_hidden is None else request_data.is_hidden,
            short_description_is_markdown=action.short_description_is_markdown,
        )
        set_action_translation(
            language_id=Language.ENGLISH,
            action_id=action_id,
            name=(action.name.get("en") or "") if request_data.name is None else request_data.name,
            description=(action.description.get("en") or "") if request_data.description is None else request_data.description,
            short_description=action.short_description.get("en") or ""
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
