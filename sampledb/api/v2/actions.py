import json
import typing
from dataclasses import dataclass

import flask
from pydantic import AfterValidator, Field, Strict, ValidationInfo, BaseModel
from pydantic_core import PydanticCustomError

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic.action_translations import set_action_translation
from ...logic.actions import Action as LogicAction
from ...logic.actions import get_action, update_action
from ...logic.languages import Language
from ...logic.action_permissions import get_user_action_permissions, get_actions_with_permissions
from ...logic import errors, utils, action_types
from ...logic.schemas.templates import find_invalid_template_paths
from ...logic.schemas.validate_schema import validate_schema
from ...models import Permissions
from .utils.validation import ModelWithDefaultsFromValidationInfo, OptionalNotNone, populate_missing_or_expect_from_validation_info, method


def action_to_json(action: LogicAction) -> typing.Dict[str, typing.Any]:
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
    class PathModel(BaseModel):
        action_id: int = Field(description='the ID of an existing action', examples=[1])

    @dataclass(frozen=True, slots=True)
    class ValidationContext:
        action: LogicAction
        action_type: str

        @classmethod
        def from_path_model(cls, path: Action.PathModel) -> typing.Self:
            try:
                action = get_action(path.action_id)
            except errors.ActionDoesNotExistError:
                flask.abort(flask.Response(json.dumps({"msg": f"action {path.action_id} does not exist"}), status=404, mimetype='application/json'))
            return cls(action=action, action_type=action_to_json(action)["type"])

    class RequestBodyModel(ModelWithDefaultsFromValidationInfo):
        action_id: typing.Annotated[int, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.action.id)] = Field(description="the ID of the action to update, must match the action_id path parameter", examples=[1])
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
        ] = Field(description="the instrument ID of the action to update, must match its current instrument_id", examples=[1])
        user_id: typing.Annotated[typing.Optional[int], Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.action.user_id)] = Field(description="the user ID of the action to update, must match its current user_id", examples=[1])
        type: typing.Annotated[typing.Optional[str], populate_missing_or_expect_from_validation_info(lambda i: i.context.action_type)] = Field(description="the type string representation of the action to update, must match its current type string", examples=["sample"])
        type_id: typing.Annotated[typing.Optional[int], Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.action.type_id)] = Field(description="the type ID of the action to update, must match its current type_id", examples=[-99])
        name: typing.Annotated[OptionalNotNone[str], Field(min_length=1, max_length=100)] = Field(description="the name of the action to update", examples=["Example Action"])
        description: OptionalNotNone[str] = Field(description="the description of the action to update", examples=["This is an example action"])
        is_hidden: OptionalNotNone[bool] = Field(description="whether the action should be set to hidden", examples=[False])
        action_schema: typing.Annotated[
            OptionalNotNone[typing.Dict[str, typing.Any]],
            AfterValidator(_is_valid_schema),
            Field(
                validation_alias="schema",
                description="the schema of the action to update",
                examples=[{
                    "type": "object",
                    "title": {"en": "Object Information"},
                    "properties": {
                        "name": {
                            "type": "text",
                            "title": {"en": "Name"}
                        },
                    },
                    "required": ["name"]
                }]
            ),
        ]

        @staticmethod
        def _is_valid_schema(schema: typing.Dict[str, typing.Any], info: ValidationInfo[Action.ValidationContext]) -> typing.Dict[str, typing.Any]:
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

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get an action.
        """
        try:
            action = get_action(
                action_id=path.action_id
            )
        except errors.ActionDoesNotExistError:
            return {
                "message": f"action {path.action_id} does not exist"
            }, 404
        if Permissions.READ not in get_user_action_permissions(action_id=path.action_id, user_id=flask.g.user.id):
            return flask.abort(403)
        return action_to_json(action)

    @multi_auth.login_required
    @method(request_body_context_builder=ValidationContext.from_path_model)
    def post(self, path: PathModel, request_body: RequestBodyModel) -> ResponseData:
        """
        Update an action.
        """
        try:
            action = get_action(
                action_id=path.action_id
            )
        except errors.ActionDoesNotExistError:
            return {
                "message": f"action {path.action_id} does not exist"
            }, 404
        if Permissions.WRITE not in get_user_action_permissions(action_id=path.action_id, user_id=flask.g.user.id):
            return flask.abort(403)
        if action.fed_id is not None:
            return flask.abort(403)
        update_action(
            action_id=path.action_id,
            schema=action.schema if request_body.action_schema is None else request_body.action_schema,
            description_is_markdown=action.description_is_markdown,
            is_hidden=action.is_hidden if request_body.is_hidden is None else request_body.is_hidden,
            short_description_is_markdown=action.short_description_is_markdown,
        )
        set_action_translation(
            language_id=Language.ENGLISH,
            action_id=path.action_id,
            name=(action.name.get("en") or "") if request_body.name is None else request_body.name,
            description=(action.description.get("en") or "") if request_body.description is None else request_body.description,
            short_description=action.short_description.get("en") or ""
        )
        action = get_action(action_id=path.action_id)
        return action_to_json(action)


class Actions(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> ResponseData:
        """
        List all actions.

        Get a list of all actions the user has READ permissions for.
        """
        actions = get_actions_with_permissions(user_id=flask.g.user.id, permissions=Permissions.READ)
        return [
            action_to_json(action)
            for action in actions
        ]
