import json
import typing
from dataclasses import dataclass
from http import HTTPStatus

import flask
from pydantic import AfterValidator, Field, Strict, ValidationInfo, BaseModel
from pydantic_core import PydanticCustomError

from .authentication import multi_auth
from ..utils import Resource
from ...logic.action_translations import set_action_translation, delete_action_translation
from ...logic.actions import Action as LogicAction
from ...logic.actions import get_action, update_action
from ...logic.languages import Language, get_languages
from ...logic.action_permissions import get_user_action_permissions, get_actions_with_permissions
from ...logic import errors, action_types
from ...logic.schemas.templates import find_invalid_template_paths
from ...logic.schemas.validate_schema import validate_schema
from ...models import Permissions
from .utils.validation import ModelWithDefaultsFromValidationInfo, OptionalNotNone, LanguageCode, populate_missing_or_expect_from_validation_info
from .utils.responses import ErrorDetailsModel, PaginatedSequence, PaginationQueryModel
from .utils.openapi import method


class InsufficientActionPermissionsModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.FORBIDDEN
    TITLE: typing.ClassVar[str] = "The user does not have sufficient permissions for the action."


class ActionModel(BaseModel):
    action_id: int = Field(description="the ID of the action", examples=[1])
    instrument_id: int | None = Field(description="the ID of the instrument the action belongs to", examples=[1])
    user_id: int | None = Field(description="the ID of the user who created the action", examples=[1])
    type: typing.Literal['sample', 'measurement', 'simulation', 'custom'] = Field(description="a string representation of the action type", examples=["sample"], deprecated=True)
    type_id: int | None = Field(description="the ID of the action type", examples=[1])
    name: dict[str, str] | None = Field(description="the name of the action", examples=[{"en": "Example Action"}])
    description: dict[str, str] | None = Field(description="the description of the action", examples=[{"en": "This is an example action."}])
    description_is_markdown: bool | None = Field(description="whether the description is formatted in Markdown", examples=[False])
    short_description: dict[str, str] | None = Field(description="the short description of the action for action lists", examples=[{"en": "This is an example action."}])
    short_description_is_markdown: bool | None = Field(description="whether the short description is formatted in Markdown", examples=[False])
    is_hidden: bool = Field(description="whether the action is hidden from action lists", examples=[False])
    action_schema: dict[str, typing.Any] | None = Field(
        alias='schema',
        description='the schema of the action',
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
    )

    @classmethod
    def from_action(cls, action: LogicAction) -> typing.Self:
        return cls(
            action_id=action.id,
            instrument_id=action.instrument_id if not flask.current_app.config['DISABLE_INSTRUMENTS'] else None,
            user_id=action.user_id,
            type={
                action_types.ActionType.SAMPLE_CREATION: 'sample',
                action_types.ActionType.MEASUREMENT: 'measurement',
                action_types.ActionType.SIMULATION: 'simulation'
            }.get(action.type_id, 'custom') if action.type_id is not None else 'custom',  # type: ignore[arg-type]
            type_id=action.type_id,
            name=action.name,
            description=action.description,
            description_is_markdown=action.description_is_markdown,
            short_description=action.short_description,
            short_description_is_markdown=action.short_description_is_markdown,
            is_hidden=action.is_hidden,
            schema=action.schema
        )


class ActionNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The action does not exist."


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
                flask.abort(
                    flask.Response(
                        json.dumps(
                            ActionNotFoundModel(
                                detail=f"Action #{path.action_id} does not exist."
                            ).model_dump()
                        ),
                        status=404,
                        mimetype='application/problem+json'
                    )
                )
            return cls(action=action, action_type=ActionModel.from_action(action).type)

    class RequestBodyModel(ModelWithDefaultsFromValidationInfo):
        action_id: typing.Annotated[int, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.action.id)] = Field(description="the ID of the action to update, must match the action_id path parameter", examples=[1])
        instrument_id: typing.Annotated[
            int | None,
            Strict(),
            populate_missing_or_expect_from_validation_info(
                lambda i: (
                    None
                    if flask.current_app.config["DISABLE_INSTRUMENTS"]
                    else i.context.action.instrument_id
                )
            ),
        ] = Field(description="the instrument ID of the action to update, must match its current instrument_id", examples=[1])
        user_id: typing.Annotated[int | None, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.action.user_id)] = Field(description="the user ID of the action to update, must match its current user_id", examples=[1])
        type: typing.Annotated[str | None, populate_missing_or_expect_from_validation_info(lambda i: i.context.action_type)] = Field(description="the type string representation of the action to update, must match its current type string", examples=["sample"])
        type_id: typing.Annotated[int | None, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.action.type_id)] = Field(description="the type ID of the action to update, must match its current type_id", examples=[-99])
        name: dict[LanguageCode, typing.Annotated[str, Field(min_length=1, max_length=100)]] = Field(description="the name of the action to update", examples=["Example Action"])
        description: dict[LanguageCode, str] = Field(description="the description of the action to update", examples=[{"en": "This is an example action"}])
        description_is_markdown: bool = Field(description="whether the description is formatted in markdown", examples=[False])
        short_description: dict[LanguageCode, str] = Field(description="the description of the action to update", examples=[{"en": "This is an example action"}])
        short_description_is_markdown: bool = Field(description="whether the description is formatted in markdown", examples=[False])
        is_hidden: OptionalNotNone[bool] = Field(description="whether the action should be set to hidden", examples=[False])
        action_schema: typing.Annotated[
            OptionalNotNone[dict[str, typing.Any]],
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
        def _is_valid_schema(schema: dict[str, typing.Any], info: ValidationInfo[Action.ValidationContext]) -> dict[str, typing.Any]:
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
    def get(self, path: PathModel) -> ActionModel | ActionNotFoundModel | InsufficientActionPermissionsModel:
        """
        Get an action.
        """
        try:
            action = get_action(
                action_id=path.action_id
            )
        except errors.ActionDoesNotExistError:
            return ActionNotFoundModel(
                detail=f"Action #{path.action_id} does not exist."
            )
        if Permissions.READ not in get_user_action_permissions(action_id=path.action_id, user_id=flask.g.user.id):
            return InsufficientActionPermissionsModel(
                detail=f"User #{flask.g.user.id} does not have sufficient permissions for action #{path.action_id}."
            )
        return ActionModel.from_action(action)

    @multi_auth.login_required
    @method(request_body_context_builder=ValidationContext.from_path_model)
    def put(self, path: PathModel, request_body: RequestBodyModel) -> ActionModel | ActionNotFoundModel | InsufficientActionPermissionsModel:
        """
        Update an action.
        """
        try:
            action = get_action(
                action_id=path.action_id
            )
        except errors.ActionDoesNotExistError:
            return ActionNotFoundModel(
                detail=f"Action #{path.action_id} does not exist."
            )
        if action.fed_id is not None or Permissions.WRITE not in get_user_action_permissions(action_id=path.action_id, user_id=flask.g.user.id):
            return InsufficientActionPermissionsModel(
                detail=f"User #{flask.g.user.id} does not have sufficient permissions for action #{path.action_id}."
            )
        update_action(
            action_id=path.action_id,
            schema=action.schema if request_body.action_schema is None else request_body.action_schema,
            description_is_markdown=request_body.description_is_markdown,
            is_hidden=action.is_hidden if request_body.is_hidden is None else request_body.is_hidden,
            short_description_is_markdown=request_body.short_description_is_markdown,
        )
        all_languages = get_languages(only_enabled_for_input=True)
        for language in all_languages:
            if language.id != Language.ENGLISH and not any(translated_text is not None and language.lang_code in translated_text for translated_text in [request_body.name, request_body.description, request_body.short_description]):
                try:
                    delete_action_translation(action_id=path.action_id, language_id=language.id)
                except errors.ActionTranslationDoesNotExistError:
                    pass
            set_action_translation(
                language_id=language.id,
                action_id=path.action_id,
                name=request_body.name.get(language.lang_code, ""),
                description=request_body.description.get(language.lang_code, ""),
                short_description=request_body.short_description.get(language.lang_code, ""),
            )
        action = get_action(action_id=path.action_id)
        return ActionModel.from_action(action)


class Actions(Resource):
    @multi_auth.login_required
    @method()
    def get(self, query: PaginationQueryModel) -> PaginatedSequence[ActionModel]:
        """
        List all actions.

        Get a list of all actions the user has READ permissions for.
        """
        actions = get_actions_with_permissions(user_id=flask.g.user.id, permissions=Permissions.READ)
        # TODO: apply pagination in database
        return PaginatedSequence.apply_pagination(
            items=[
                ActionModel.from_action(action)
                for action in actions
            ],
            query=query,
            id_getter=lambda action: action.action_id,
        )
