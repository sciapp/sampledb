import json
import typing
from dataclasses import dataclass
from functools import cached_property

import flask
from pydantic import (AfterValidator, AliasChoices, BaseModel, BeforeValidator,
                      Field, Strict, ValidationInfo, model_validator)
from pydantic_core import PydanticCustomError

from ... import models
from ...api.server.authentication import (multi_auth,
                                          object_permissions_required)
from ...logic import errors, user_log, users
from ...logic.action_permissions import get_user_action_permissions
from ...logic.action_types import check_action_type_exists
from ...logic.actions import Action, check_action_exists, get_action
from ...logic.object_permissions import get_objects_with_permissions
from ...logic.object_relationships import (get_referencing_object_ids,
                                           get_related_object_ids)
from ...logic.object_search import generate_filter_func, wrap_filter_func
from ...logic.objects import create_object, get_object, update_object
from ...logic.schemas.data_diffs import apply_diff, calculate_diff
from ...models import Permissions
from ...utils import text_to_bool
from ..utils import Resource, ResponseData
from .actions import action_to_json
from .users import user_to_json
from .validation_utils import (ModelWithDefaultsFromValidationInfo,
                               OptionalNotNone, ValidatingError,
                               populate_missing_or_expect_from_validation_info,
                               validate)


@dataclass(frozen=True, slots=True)
class _ValidationContext:
    object: models.Object


class _ObjectVersion(ModelWithDefaultsFromValidationInfo):
    object_id: typing.Annotated[int, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.object_id)]
    fed_object_id: typing.Annotated[typing.Optional[int], Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.fed_object_id)]
    fed_version_id: typing.Annotated[typing.Optional[int], Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.fed_version_id)]
    component_id: typing.Annotated[typing.Optional[int], Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.component_id)]
    version_id: typing.Annotated[int, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.version_id + 1)]
    action_id: typing.Annotated[int, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.object.action_id)]
    action_schema: typing.Annotated[
        OptionalNotNone[typing.Dict[str, typing.Any]],
        Field(validation_alias="schema"),
    ]
    data: OptionalNotNone[typing.Dict[str, typing.Any]]
    data_diff: OptionalNotNone[typing.Dict[str, typing.Any]]

    @cached_property
    def action(self) -> Action:
        try:
            return get_action(action_id=self.action_id)
        except errors.ActionDoesNotExistError:
            raise PydanticCustomError("no_such_action", "Action should exist (action_id)")

    @model_validator(mode="after")
    def check_action_and_schema(self, info: ValidationInfo[_ValidationContext]) -> typing.Self:
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


class _Object(BaseModel):
    fed_object_id: None = None
    fed_version_id: None = None
    component_id: None = None
    version_id: typing.Literal[0] = 0
    action_id: typing.Annotated[int, Strict()]
    action_schema: typing.Annotated[
        OptionalNotNone[typing.Dict[str, typing.Any]],
        Field(validation_alias="schema"),
    ]
    data: typing.Dict[str, typing.Any]

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


class ObjectVersion(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, version_id: int) -> ResponseData:
        try:
            object = get_object(object_id=object_id, version_id=version_id)
        except errors.ObjectVersionDoesNotExistError:
            return {
                "message": f"version {version_id} of object {object_id} does not exist"
            }, 404
        object_version_json: typing.Dict[str, typing.Any] = {
            'object_id': object.object_id,
            'version_id': object.version_id,
            'action_id': object.action_id,
            'user_id': object.user_id,
            'utc_datetime': object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S") if object.utc_datetime else None,
            'schema': object.schema,
            'data': object.data,
            'fed_object_id': object.fed_object_id,
            'fed_version_id': object.fed_version_id,
            'component_id': object.component_id
        }
        embed_action = bool(flask.request.args.get('embed_action'))
        if embed_action:
            object_version_json['action'] = None
            if object.action_id is not None:
                try:
                    if Permissions.READ in get_user_action_permissions(action_id=object.action_id, user_id=flask.g.user.id):
                        action = get_action(
                            action_id=object.action_id
                        )
                        object_version_json['action'] = action_to_json(action)
                except errors.ActionDoesNotExistError:
                    pass
        embed_user = bool(flask.request.args.get('embed_user'))
        if embed_user:
            object_version_json['user'] = None
            if object.user_id is not None:
                try:
                    user = users.get_user(object.user_id)
                    object_version_json['user'] = user_to_json(user)
                except errors.UserDoesNotExistError:
                    pass
        include_diff = text_to_bool(flask.request.args.get('include_diff', ''))
        if include_diff and object.version_id > 0:
            previous_object_version = get_object(object_id=object.object_id, version_id=object.version_id - 1)
            data_diff = calculate_diff(previous_object_version.data, object.data)
            object_version_json['data_diff'] = data_diff
        return object_version_json


class ObjectVersions(Resource):
    @object_permissions_required(Permissions.WRITE)
    def post(self, object_id: int) -> ResponseData:
        request_json = flask.request.get_json(force=True)
        object = get_object(object_id=object_id)
        if object.action_id is None:
            return {
                "message": "editing this object is not supported"
            }, 400
        try:
            request_data = validate(_ObjectVersion, request_json, context=_ValidationContext(object))
        except ValidatingError as e:
            return e.response
        schema = object.schema if request_data.action_schema is None else request_data.action_schema

        data = request_data.data
        data_diff = request_data.data_diff
        try:
            if data_diff is not None:
                if object.data is None or object.schema is None:
                    return {
                        "message": "previous object version must contain data and schema"
                    }, 400
                data_from_diff = apply_diff(object.data, data_diff, object.schema)
                if data is None:
                    data = data_from_diff
                elif data_from_diff != data:
                    return {
                        "message": "data and data_diff are conflicting"
                    }, 400

            update_object(
                object_id=object.id,
                data=data,
                user_id=flask.g.user.id,
                schema=schema
            )

        except errors.ValidationError as e:
            messages = e.message.splitlines()
            return {
                "message": "validation failed:\n - " + "\n - ".join(messages),
                "error_paths": e.paths
            }, 400
        except errors.DiffMismatchError:
            return {
                "message": "failed to apply diff"
            }, 400
        except Exception:
            return {
                "message": "failed to update object"
            }, 400

        object_version_url = flask.url_for(
            'api.object_version',
            object_id=object.object_id,
            version_id=object.version_id + 1,
            _external=True
        )

        return flask.redirect(object_version_url, code=201)


class Object(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        object = get_object(object_id=object_id)
        object_version_url = flask.url_for(
            'api.object_version',
            object_id=object.object_id,
            version_id=object.version_id,
            _external=True
        )
        return flask.redirect(object_version_url, code=302)


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


class _ObjectsQuery(BaseModel):
    action_id: typing.Annotated[int, AfterValidator(_action_exists)] | None = None
    action_type_id: typing.Annotated[
        typing.Annotated[int, BeforeValidator(_action_type_id)] | None,
        Field(validation_alias=AliasChoices("action_type_id", "action_type")),
    ] = None
    object_ids: typing.Annotated[
        typing.List[int],
        BeforeValidator(lambda value: [int(ss) for s in value for ss in s.split(",")]),
    ] | None = None
    related_user_id: int | None = None
    limit: typing.Annotated[int | None, BeforeValidator(lambda value: _int_in_range(value, 1, 1e15))] = None
    offset: typing.Annotated[int | None, BeforeValidator(lambda value: _int_in_range(value, 0, 1e15))] = None
    name_only: typing.Annotated[bool, BeforeValidator(text_to_bool)] = False
    query_string: typing.Annotated[str | None, Field(validation_alias="q")] = None
    use_advanced_search: typing.Annotated[bool, BeforeValidator(text_to_bool)] = True
    get_referencing_objects: typing.Annotated[bool, BeforeValidator(text_to_bool)] = False


class Objects(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        args_dict = {k: vs if k == "object_ids" else vs[0] for k, vs in flask.request.args.lists()}
        try:
            args = validate(_ObjectsQuery, args_dict)
        except ValidatingError as e:
            return e.response
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
            return {
                'message': '\n'.join(
                    'Error: ' + search_note[1]
                    for search_note in search_notes
                    if search_note[0] == 'error'
                )
            }, 400
        elif args.get_referencing_objects:
            object_references = get_referencing_object_ids({object.id for object in objects})
            ret = []
            for object in objects:
                references = object_references[object.object_id]
                referenced: typing.List[typing.Dict[str, typing.Any]] = []
                for ref in references:
                    if ref is not None:
                        reference_dict: typing.Dict[str, typing.Any] = {'object_id': ref.object_id}
                        if ref.component_uuid is not None:
                            reference_dict['component_uuid'] = ref.component_uuid
                        if ref.eln_source_url is not None:
                            reference_dict['eln_source_url'] = ref.eln_source_url
                        if ref.eln_object_url is not None:
                            reference_dict['eln_object_id'] = ref.eln_object_url
                        referenced.append(reference_dict)
                ret.append(
                    {
                        'object_id': object.object_id,
                        'version_id': object.version_id,
                        'action_id': object.action_id,
                        'user_id': object.user_id,
                        'utc_datetime': object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S") if object.utc_datetime is not None else None,
                        'schema': object.schema,
                        'data': object.data,
                        'fed_object_id': object.fed_object_id,
                        'fed_version_id': object.fed_version_id,
                        'component_id': object.component_id,
                        'referencing_objects': referenced
                    }
                )
            return ret, 200
        else:
            return [
                {
                    'object_id': object.object_id,
                    'version_id': object.version_id,
                    'action_id': object.action_id,
                    'user_id': object.user_id,
                    'utc_datetime': object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S") if object.utc_datetime is not None else None,
                    'schema': object.schema,
                    'data': object.data,
                    'fed_object_id': object.fed_object_id,
                    'fed_version_id': object.fed_version_id,
                    'component_id': object.component_id
                }
                for object in objects
            ], 200

    @multi_auth.login_required
    def post(self) -> ResponseData:
        if flask.g.user.is_readonly:
            return {
                'message': 'user has been marked as read only'
            }, 400
        request_json = flask.request.get_json(force=True)
        try:
            request_data = validate(_Object, request_json)
        except ValidatingError as e:
            return e.response
        action = request_data.action
        if action.type is None or action.type.disable_create_objects or action.disable_create_objects or (action.admin_only and not flask.g.user.is_admin):
            return {
                "message": f"creating objects with action {request_data.action_id} is disabled"
            }, 400
        try:
            object = create_object(
                action_id=request_data.action_id,
                data=request_data.data,
                user_id=flask.g.user.id,
                schema=action.schema,
            )
        except errors.ValidationError as e:
            messages = e.message.splitlines()
            return {
                "message": "validation failed:\n - " + "\n - ".join(messages),
                "error_paths": e.paths
            }, 400
        except Exception:
            return {
                "message": "failed to create object"
            }, 400
        object_version_url = flask.url_for(
            'api.object_version',
            object_id=object.object_id,
            version_id=object.version_id,
            _external=True
        )
        return flask.redirect(object_version_url, code=201)


class RelatedObjects(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        referencing_object_ids, referenced_object_ids = get_related_object_ids(
            object_id=object_id,
            include_referencing_objects=True,
            include_referenced_objects=True,
            user_id=flask.g.user.id
        )
        return {
            "referencing_objects": [
                {
                    "object_id": object_id,
                    "component_uuid": component_uuid
                }
                for object_id, component_uuid in referencing_object_ids
            ],
            "referenced_objects": [
                {
                    "object_id": object_id,
                    "component_uuid": component_uuid
                }
                for object_id, component_uuid in referenced_object_ids
            ]
        }
