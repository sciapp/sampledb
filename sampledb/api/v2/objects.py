import json
import typing
from dataclasses import dataclass
from functools import cached_property

import flask
from pydantic import (AfterValidator, AliasChoices, BaseModel, BeforeValidator,
                      Field, Strict, ValidationInfo, model_validator)
from pydantic_core import PydanticCustomError

from ... import models
from .authentication import multi_auth, object_permissions_required
from ...logic import errors, user_log, users
from ...logic.action_permissions import get_user_action_permissions
from ...logic.action_types import check_action_type_exists
from ...logic.actions import Action, check_action_exists, get_action
from ...logic.object_permissions import get_objects_with_permissions
from ...logic.object_relationships import get_referencing_object_ids, get_related_object_ids, ObjectRef
from ...logic.object_search import generate_filter_func, wrap_filter_func
from ...logic.objects import create_object, get_object, update_object
from ...logic.schemas.data_diffs import apply_diff, calculate_diff
from ...models import Permissions
from ...utils import text_to_bool
from ..utils import Resource
from .actions import ActionModel
from .users import UserModel
from .utils.validation import ModelWithDefaultsFromValidationInfo, OptionalNotNone, populate_missing_or_expect_from_validation_info, generate_example
from .utils.responses import BadRequestErrorModel, CreatedResponseModel, FoundResponseModel, NotFoundErrorModel
from .utils.openapi import method


class ObjectReferenceModel(BaseModel):
    object_id: int = Field(description="the ID of the referenced object", examples=[1])
    component_uuid: typing.Optional[str] = Field(None, description="the UUID of the federation component the referenced object belongs to", examples=["59b4f08d-f2e6-4343-a155-9880e988cead"])
    eln_source_url: typing.Optional[str] = Field(None, description="the URL of the source ELN of the referenced object", examples=["https://example.com"])
    eln_object_url: typing.Optional[str] = Field(None, description="the URL of the referenced object in its source ELN", examples=["https://example.com/objects/A"])

    @classmethod
    def from_object_ref(cls, object_ref: ObjectRef) -> typing.Self:
        return cls(
            object_id=object_ref.object_id,
            component_uuid=object_ref.component_uuid,
            eln_source_url=object_ref.eln_source_url,
            eln_object_url=object_ref.eln_object_url
        )


class _ObjectModel(BaseModel):
    object_id: int = Field(description="the ID of the object", examples=[1])
    version_id: int = Field(description="the ID of the current object version", examples=[0])
    action_id: typing.Optional[int] = Field(description="the ID of the action the object was created with", examples=[1])
    user_id: typing.Optional[int] = Field(description="the ID of the user who created this object version", examples=[1])
    utc_datetime: typing.Optional[str] = Field(description="the datetime in UTC when the current object version was created, formatted as YYYY-MM-DD HH:MM:SS", examples=["2026-01-02 03:04:05"])
    schema_: typing.Optional[typing.Dict[str, typing.Any]] = Field(
        alias="schema",
        description="the schema of the current object version",
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
    data: typing.Optional[typing.Dict[str, typing.Any]] = Field(
        description="the data of the current object version",
        examples=[{
            "name": {
                "_type": "text",
                "text": {
                    "en": "Example Object"
                }
            }
        }]
    )
    fed_object_id: typing.Optional[int] = Field(description="the federated object ID of the object", examples=[1])
    fed_version_id: typing.Optional[int] = Field(description="the federated object version ID for the current object version", examples=[1])
    component_id: typing.Optional[int] = Field(description="the federation component ID of the object", examples=[1])
    referencing_objects: typing.Optional[typing.List[ObjectReferenceModel]] = Field(description="the list of referencing objects", examples=[generate_example(ObjectReferenceModel)])


class ObjectVersionModel(BaseModel):
    object_id: int = Field(description="the ID of the object the version belongs to", examples=[1])
    version_id: int = Field(description="the ID of the object version", examples=[0])
    action_id: typing.Optional[int] = Field(description="the ID of the action the object was created with", examples=[1])
    user_id: typing.Optional[int] = Field(description="the ID of the user who created this object version", examples=[1])
    utc_datetime: typing.Optional[str] = Field(description="the datetime in UTC when the object version was created, formatted as YYYY-MM-DD HH:MM:SS", examples=["2026-01-02 03:04:05"])
    schema_: typing.Optional[typing.Dict[str, typing.Any]] = Field(
        alias="schema",
        description="the schema of the object version",
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
    data: typing.Optional[typing.Dict[str, typing.Any]] = Field(
        description="the data of the object version",
        examples=[{
            "name": {
                "_type": "text",
                "text": {
                    "en": "Example Object"
                }
            }
        }]
    )
    fed_object_id: typing.Optional[int] = Field(description="the federated object ID of the object the version belongs to", examples=[1])
    fed_version_id: typing.Optional[int] = Field(description="the federated object version ID for this object version", examples=[1])
    component_id: typing.Optional[int] = Field(description="the federation component ID of the object this version belongs to", examples=[1])
    user: typing.Optional[UserModel] = Field(description="the user who created this object version, as if queried via their ID", examples=[generate_example(UserModel)])
    action: typing.Optional[ActionModel] = Field(description="the action the object was created with, as if queried via its ID", examples=[generate_example(ActionModel)])
    data_diff: typing.Optional[typing.Any] = Field(
        description="the data diff between the previous object version and this one",
        examples=[{
            "name": {
                "_before": {
                    "_type": "text",
                    "text": {"en": "Previous Example Object"}
                },
                "_after": {
                    "_type": "text",
                    "text": {"en": "Example Object"}
                }
            }
        }]
    )


class ObjectVersion(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])
        version_id: int = Field(description="the ID of an existing object version", examples=[0])

    class QueryModel(BaseModel):
        embed_action: bool = Field(False, description="whether to embed the action in the response", examples=[False])
        embed_user: bool = Field(False, description="whether to embed the user in the response", examples=[False])
        include_diff: bool = Field(False, description="whether to include the diff to the previous version in the response", examples=[False])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel, query: QueryModel) -> ObjectVersionModel | NotFoundErrorModel:
        """
        Get an object version.
        """
        try:
            object = get_object(object_id=path.object_id, version_id=path.version_id)
        except errors.ObjectVersionDoesNotExistError:
            return NotFoundErrorModel(
                error="NotFound",
                message=f"version {path.version_id} of object {path.object_id} does not exist"
            )
        object_version = ObjectVersionModel(
            object_id=object.object_id,
            version_id=object.version_id,
            action_id=object.action_id,
            user_id=object.user_id,
            utc_datetime=object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S") if object.utc_datetime else None,
            schema=object.schema,
            data=object.data,
            fed_object_id=object.fed_object_id,
            fed_version_id=object.fed_version_id,
            component_id=object.component_id,
            action=None,
            user=None,
            data_diff=None,
        )
        if query.embed_action:
            object_version.action = None
            if object.action_id is not None:
                try:
                    if Permissions.READ in get_user_action_permissions(action_id=object.action_id, user_id=flask.g.user.id):
                        action = get_action(
                            action_id=object.action_id
                        )
                        object_version.action = ActionModel.from_action(action)
                except errors.ActionDoesNotExistError:
                    pass
        if query.embed_user:
            object_version.user = None
            if object.user_id is not None:
                try:
                    user = users.get_user(object.user_id)
                    object_version.user = UserModel.from_user(user)
                except errors.UserDoesNotExistError:
                    pass
        if query.include_diff and object.version_id > 0:
            previous_object_version = get_object(object_id=object.object_id, version_id=object.version_id - 1)
            data_diff = calculate_diff(previous_object_version.data, object.data)
            object_version.data_diff = data_diff
        return object_version


class ObjectVersions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    @dataclass(frozen=True, slots=True)
    class ValidationContext:
        object: models.Object

        @classmethod
        def from_path(cls, path: ObjectVersions.PathModel) -> typing.Self:
            return cls(
                object=get_object(object_id=path.object_id)
            )

    class RequestBodyModel(ModelWithDefaultsFromValidationInfo):
        object_id: typing.Annotated[int, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.object_id)] = Field(description="the ID of the object to update, must match the object_id path parameter", examples=[1])
        fed_object_id: typing.Annotated[typing.Optional[int], Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.fed_object_id)] = Field(description="the federated object ID of the object to update, must match its current fed_object_id", examples=[1])
        fed_version_id: typing.Annotated[typing.Optional[int], Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.fed_version_id)] = Field(description="the federated version ID of the object to update, must match its current fed_object_id", examples=[1])
        component_id: typing.Annotated[typing.Optional[int], Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.component_id)] = Field(description="the federation component ID of the object to update, must match its current component_id", examples=[1])
        version_id: typing.Annotated[int, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.version_id + 1)] = Field(description="the ID of the new object version to create, must match its current version_id + 1", examples=[1])
        action_id: typing.Annotated[int, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.action_id)] = Field(description="the action ID of the object to update, must match its current action_id", examples=[1])
        action_schema: typing.Annotated[
            OptionalNotNone[typing.Dict[str, typing.Any]],
            Field(
                validation_alias="schema",
                description="the schema for the object, must be the same as its current schema or the schema of the action used",
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
        data: OptionalNotNone[typing.Dict[str, typing.Any]] = Field(
            description="the data for the object",
            examples=[{
                "name": {
                    "_type": "text",
                    "text": {"en": "New Object Version"}
                }
            }]
        )
        data_diff: OptionalNotNone[typing.Dict[str, typing.Any]] = Field(
            description="the data diff between the previous object version and the one to create",
            examples=[{
                "name": {
                    "_before": {
                        "_type": "text",
                        "text": {"en": "Example Object"}
                    },
                    "_after": {
                        "_type": "text",
                        "text": {"en": "New Object Version"}
                    }
                }
            }]
        )

        @cached_property
        def action(self) -> Action:
            try:
                return get_action(action_id=self.action_id)
            except errors.ActionDoesNotExistError:
                raise PydanticCustomError("no_such_action", "Action should exist (action_id)")

        @model_validator(mode="after")
        def check_action_and_schema(self, info: ValidationInfo[ObjectVersions.ValidationContext]) -> typing.Self:
            if self.action_schema not in (None, info.context.object.schema, self.action.schema):
                raise PydanticCustomError(
                    "unexpected",
                    f"Schema should be {json.dumps(info.context.object.schema, indent=4)} or {json.dumps(self.action.schema, indent=4)}",
                    {"expected": self.action.schema},
                )
            return self

        @model_validator(mode="after")
        def check_data_specified(self) -> typing.Self:
            if (self.data, self.data_diff) == (None, None):
                raise PydanticCustomError("missing", "At least one required: data, data_diff")
            return self

    @object_permissions_required(Permissions.WRITE)
    @method(request_body_context_builder=ValidationContext.from_path)
    def post(self, path: PathModel, request_body: RequestBodyModel) -> CreatedResponseModel | BadRequestErrorModel:
        """
        Create a new object version.
        """
        object = get_object(object_id=path.object_id)
        if object.action_id is None:
            return BadRequestErrorModel(
                error="LogicError",
                message="editing this object is not supported"
            )
        schema = object.schema if request_body.action_schema is None else request_body.action_schema

        data = request_body.data
        data_diff = request_body.data_diff
        try:
            if data_diff is not None:
                if object.data is None or object.schema is None:
                    return BadRequestErrorModel(
                        error="LogicError",
                        message="previous object version must contain data and schema"
                    )
                data_from_diff = apply_diff(object.data, data_diff, object.schema)
                if data is None:
                    data = data_from_diff
                elif data_from_diff != data:
                    return BadRequestErrorModel(
                        error="Bad Request",
                        message="data and data_diff are conflicting"
                    )

            update_object(
                object_id=object.id,
                data=data,
                user_id=flask.g.user.id,
                schema=schema
            )

        except errors.ValidationError as e:
            messages = e.message.splitlines()
            return BadRequestErrorModel(
                error="Validation Error",
                message="validation failed:\n - " + "\n - ".join(messages),
                error_details={
                    "paths": e.paths
                }
            )
        except errors.DiffMismatchError:
            return BadRequestErrorModel(
                error="Bad Request",
                message="failed to apply diff"
            )
        except Exception:
            return BadRequestErrorModel(
                error="LogicError",
                message="failed to update object"
            )

        object_version_url = flask.url_for(
            '.object_version',
            object_id=object.object_id,
            version_id=object.version_id + 1,
            _external=True
        )

        return CreatedResponseModel(location=object_version_url)


class Object(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> FoundResponseModel:
        """
        Get an object.
        """
        object = get_object(object_id=path.object_id)
        object_version_url = flask.url_for(
            '.object_version',
            object_id=object.object_id,
            version_id=object.version_id,
            _external=True
        )
        return FoundResponseModel(
            location=object_version_url,
        )


def _action_exists(value: int) -> int:
    try:
        check_action_exists(value)
    except errors.ActionDoesNotExistError:
        raise PydanticCustomError("no_such_action", "Action should exist")
    return value


def _action_type_id(value: str) -> int:
    try:
        action_type_id = int(value)
    except ValueError:
        try:
            return {
                "sample": models.ActionType.SAMPLE_CREATION,
                "measurement": models.ActionType.MEASUREMENT,
                "simulation": models.ActionType.SIMULATION,
            }[value]
        except KeyError:
            raise PydanticCustomError("no_such_action_type", "Action type string should be 'sample', 'measurement' or 'simulation'")
    try:
        check_action_type_exists(action_type_id)
    except errors.ActionTypeDoesNotExistError:
        raise PydanticCustomError("no_such_action_type", "Action type should exist")
    return action_type_id


def _int_in_range(value: str, lo: int, hi: int) -> int | None:
    try:
        v = int(value)
    except ValueError:
        return None
    return v if lo <= v < hi else None


class Objects(Resource):
    class RequestBodyModel(BaseModel):
        fed_object_id: None = Field(None, description="the federated object ID of the object, must be None", examples=[None])
        fed_version_id: None = Field(None, description="the federated version ID of the object, must be None", examples=[None])
        component_id: None = Field(None, description="the federation component ID of the object, must be None", examples=[None])
        version_id: typing.Literal[0] = Field(0, description="the version ID of the object, must be 0", examples=[0])
        action_id: typing.Annotated[int, Strict()] = Field(description="the ID of an existing action to create the object with", examples=[1])
        action_schema: typing.Annotated[
            OptionalNotNone[typing.Dict[str, typing.Any]],
            Field(
                validation_alias="schema",
                description="the schema for the object, must be the same as the schema of the action used",
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
        data: typing.Dict[str, typing.Any] = Field(
            description="the data for the object",
            examples=[{
                "name": {
                    "_type": "text",
                    "text": {"en": "Example Object"}
                }
            }]
        )

        @cached_property
        def action(self) -> Action:
            try:
                return get_action(action_id=self.action_id)
            except errors.ActionDoesNotExistError:
                raise PydanticCustomError("no_such_action", "Action should exist (action_id)")

        @model_validator(mode="after")
        def check_action_and_schema(self) -> typing.Self:
            if self.action_schema not in (None, self.action.schema):
                raise PydanticCustomError(
                    "unexpected",
                    f"Schema should be {json.dumps(self.action.schema, indent=4)}",
                    {"expected": self.action.schema},
                )
            return self

    class QueryModel(BaseModel):
        action_id: typing.Annotated[int, AfterValidator(_action_exists)] | None = Field(None, description="the ID of an existing action — filter for objects created with this action", examples=[1])
        action_type_id: typing.Annotated[
            typing.Annotated[int, BeforeValidator(_action_type_id)] | None,
            Field(validation_alias=AliasChoices("action_type_id", "action_type")),
        ] = Field(None, description="the ID of an existing action type — filter for objects created with actions of this type", examples=[1])
        object_ids: typing.Annotated[
            typing.List[int],
            BeforeValidator(lambda value: [int(ss) for s in (value if isinstance(value, list) else [value]) for ss in s.split(",")]),
        ] | None = Field(None, description="a list of objects IDs  — filter for objects created with any of these IDs", examples=[[1, 2, 3]])
        related_user_id: int | None = Field(None, description="the ID of an existing user — filter for objects related to this user", examples=[1])
        limit: typing.Annotated[int | None, BeforeValidator(lambda value: _int_in_range(value, 1, 1e15))] = Field(None, description="an upper limit for the number of objects to return", examples=[1])
        offset: typing.Annotated[int | None, BeforeValidator(lambda value: _int_in_range(value, 0, 1e15))] = Field(None, description="an offset for returned objects when also using `limit`", examples=[1])
        name_only: typing.Annotated[bool, BeforeValidator(text_to_bool)] = Field(False, description="whether to reduce data and schema to the object name", examples=[False])
        query_string: typing.Annotated[str | None, Field(validation_alias="q")] = Field(None, description="a query string for the object search", examples=["name == \"Object-1\""])
        use_advanced_search: typing.Annotated[bool, BeforeValidator(text_to_bool)] = Field(True, description="whether to use the advanced search when also using `q`", examples=[True])
        get_referencing_objects: typing.Annotated[bool, BeforeValidator(text_to_bool)] = Field(False, description="whether to include referencing objects in the response", examples=[False])

    @multi_auth.login_required
    @method()
    def get(self, query: QueryModel) -> typing.List[_ObjectModel] | BadRequestErrorModel:
        """
        List all (or some) objects.

        Get a list of all objects matching the query parameters.
        """
        args = query
        if args.related_user_id is None:
            object_ids = None if args.object_ids is None else set(args.object_ids)
        else:
            object_ids = user_log.get_user_related_object_ids(args.related_user_id)
            if args.object_ids is not None:
                object_ids.intersection_update(args.object_ids)

        if args.query_string is not None:
            query_string = args.query_string
            try:
                unwrapped_filter_func, _search_tree, _use_advanced_search = generate_filter_func(query_string, args.use_advanced_search, use_permissions_filter_for_referenced_objects=not flask.g.user.has_admin_permissions)
            except Exception:
                # TODO: ensure that advanced search does not cause exceptions
                def unwrapped_filter_func(data: typing.Any, search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]) -> typing.Any:
                    """Return all objects"""
                    search_notes.append(("error", "Unable to parse search expression", 0, len(query_string)))
                    return False
            filter_func, search_notes = wrap_filter_func(unwrapped_filter_func)
        else:
            search_notes = []

            def filter_func(data: typing.Any) -> typing.Any:
                return True
        try:
            objects = get_objects_with_permissions(
                user_id=flask.g.user.id,
                permissions=Permissions.READ,
                filter_func=filter_func,
                action_ids=[args.action_id] if args.action_id is not None else None,
                action_type_ids=[args.action_type_id] if args.action_type_id is not None else None,
                project_id=None,
                limit=args.limit,
                offset=args.offset,
                name_only=args.name_only,
                object_ids=list(object_ids) if object_ids is not None else None,
            )
        except Exception as e:
            search_notes.append(('error', f"Error during search: {e}", 0, 0))
            objects = []
        if any(search_note[0] == 'error' for search_note in search_notes):
            return BadRequestErrorModel(
                error='Bad Request',
                message='\n'.join(
                    'Error: ' + search_note[1]
                    for search_note in search_notes
                    if search_note[0] == 'error'
                ),
            )
        elif args.get_referencing_objects:
            object_references = get_referencing_object_ids({object.id for object in objects})
            ret = []
            for object in objects:
                references = object_references[object.object_id]
                referenced: typing.List[ObjectReferenceModel] = []
                for ref in references:
                    if ref is not None:
                        referenced.append(ObjectReferenceModel.from_object_ref(ref))
                ret.append(
                    _ObjectModel(
                        object_id=object.object_id,
                        version_id=object.version_id,
                        action_id=object.action_id,
                        user_id=object.user_id,
                        utc_datetime=object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S") if object.utc_datetime is not None else None,
                        schema=object.schema,
                        data=object.data,
                        fed_object_id=object.fed_object_id,
                        fed_version_id=object.fed_version_id,
                        component_id=object.component_id,
                        referencing_objects=referenced
                    )
                )
            return ret
        else:
            return [
                _ObjectModel(
                    object_id=object.object_id,
                    version_id=object.version_id,
                    action_id=object.action_id,
                    user_id=object.user_id,
                    utc_datetime=object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S") if object.utc_datetime is not None else None,
                    schema=object.schema,
                    data=object.data,
                    fed_object_id=object.fed_object_id,
                    fed_version_id=object.fed_version_id,
                    component_id=object.component_id,
                    referencing_objects=None
                )
                for object in objects
            ]

    @multi_auth.login_required
    @method()
    def post(self, request_body: RequestBodyModel) -> CreatedResponseModel | BadRequestErrorModel:
        """
        Create a new object.
        """
        if flask.g.user.is_readonly:
            return BadRequestErrorModel(
                error='ReadOnlyUserError',
                message="user has been marked as read only"
            )
        action = request_body.action
        if action.type is None or action.type.disable_create_objects or action.disable_create_objects or (action.admin_only and not flask.g.user.is_admin):
            return BadRequestErrorModel(
                error="LogicError",
                message=f"creating objects with action {request_body.action_id} is disabled"
            )
        try:
            object = create_object(
                action_id=request_body.action_id,
                data=request_body.data,
                user_id=flask.g.user.id,
                schema=action.schema,
            )
        except errors.ValidationError as e:
            messages = e.message.splitlines()
            return BadRequestErrorModel(
                error="Validation Error",
                message="validation failed:\n - " + "\n - ".join(messages),
                error_details={
                    "paths": e.paths
                }
            )
        except Exception:
            return BadRequestErrorModel(
                error="LogicError",
                message="failed to create object"
            )
        object_version_url = flask.url_for(
            '.object_version',
            object_id=object.object_id,
            version_id=object.version_id,
            _external=True
        )
        return CreatedResponseModel(
            location=object_version_url
        )


class RelatedObjectsModel(BaseModel):
    referencing_objects: typing.List[ObjectReferenceModel] = Field(description="the list of referencing objects", examples=[[generate_example(ObjectReferenceModel)]])
    referenced_objects: typing.List[ObjectReferenceModel] = Field(description="the list of referenced objects", examples=[[generate_example(ObjectReferenceModel)]])


class RelatedObjects(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> RelatedObjectsModel:
        """
        List references to related objects.
        """
        referencing_object_ids, referenced_object_ids = get_related_object_ids(
            object_id=path.object_id,
            include_referencing_objects=True,
            include_referenced_objects=True,
            user_id=flask.g.user.id
        )
        return RelatedObjectsModel(
            referencing_objects=[
                ObjectReferenceModel(
                    object_id=object_id,
                    component_uuid=component_uuid,
                    eln_object_url=None,
                    eln_source_url=None
                )
                for object_id, component_uuid in referencing_object_ids
            ],
            referenced_objects=[
                ObjectReferenceModel(
                    object_id=object_id,
                    component_uuid=component_uuid,
                    eln_object_url=None,
                    eln_source_url=None
                )
                for object_id, component_uuid in referenced_object_ids
            ]
        )
