import json
import typing
from dataclasses import dataclass
from functools import cached_property

import flask
from pydantic import BaseModel, Field, Strict, ValidationInfo, model_validator
from pydantic_core import PydanticCustomError

from ... import models
from ...api.server.authentication import (multi_auth,
                                          object_permissions_required)
from ...logic import errors, users
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


class Objects(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        action_id: typing.Optional[int] = None
        action_id_str = flask.request.args.get('action_id', '')
        if action_id_str:
            try:
                action_id = int(action_id_str)
            except ValueError:
                return {
                    'message': 'Unable to parse action_id'
                }, 400
            try:
                check_action_exists(action_id)
            except errors.ActionDoesNotExistError:
                return {
                    'message': 'No action with the given action_id exists.'
                }, 400

        action_type_id: typing.Optional[int] = None
        action_type_id_str = flask.request.args.get('action_type_id', flask.request.args.get('action_type', None))
        if action_type_id_str is not None:
            try:
                action_type_id = int(action_type_id_str)
            except ValueError:
                # ensure old links still function
                action_type_id = {
                    'sample': models.ActionType.SAMPLE_CREATION,
                    'measurement': models.ActionType.MEASUREMENT,
                    'simulation': models.ActionType.SIMULATION
                }.get(action_type_id_str, None)
            else:
                try:
                    check_action_type_exists(action_type_id)
                except errors.ActionTypeDoesNotExistError:
                    action_type_id = None
            if action_type_id is None:
                return {
                    'message': 'No matching action type exists.'
                }, 400

        project_id = None

        limit: typing.Optional[int] = None
        limit_str = flask.request.args.get('limit')
        if limit_str is not None:
            try:
                limit = int(limit_str)
            except ValueError:
                pass
        if limit is not None and not 1 <= limit < 1e15:
            limit = None

        offset: typing.Optional[int] = None
        offset_str = flask.request.args.get('offset')
        if offset_str is not None:
            try:
                offset = int(offset_str)
            except ValueError:
                pass
        if offset is not None and not 0 <= offset < 1e15:
            offset = None

        name_only = text_to_bool(flask.request.args.get('name_only', ''))
        query_string = flask.request.args.get('q', '')
        if query_string:
            try:
                unwrapped_filter_func, _search_tree, _use_advanced_search = generate_filter_func(query_string, text_to_bool(flask.request.args.get('use_advanced_search', 'true')), use_permissions_filter_for_referenced_objects=not flask.g.user.has_admin_permissions)
            except Exception:
                # TODO: ensure that advanced search does not cause exceptions
                def unwrapped_filter_func(data: typing.Any, search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]) -> typing.Any:
                    """ Return all objects"""
                    search_notes.append(('error', "Unable to parse search expression", 0, len(query_string)))
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
                action_ids=[action_id] if action_id is not None else None,
                action_type_ids=[action_type_id] if action_type_id is not None else None,
                project_id=project_id,
                limit=limit,
                offset=offset,
                name_only=name_only
            )
        except Exception as e:
            search_notes.append(('error', f"Error during search: {e}", 0, 0))
            objects = []
        need_object_references = flask.request.args.get('get_referencing_objects', False)
        if any(search_note[0] == 'error' for search_note in search_notes):
            return {
                'message': '\n'.join(
                    'Error: ' + search_note[1]
                    for search_note in search_notes
                    if search_note[0] == 'error'
                )
            }, 400
        elif need_object_references:
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
