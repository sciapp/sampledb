import typing
from contextlib import suppress

import flask
from pydantic import AfterValidator, BaseModel, BeforeValidator, Strict
from pydantic_core import PydanticCustomError

from .authentication import object_permissions_required, multi_auth
from ..utils import Resource, ResponseData
from ...logic import users, groups, projects, errors, object_permissions, background_tasks, objects
from ...models import Permissions
from .validation_utils import UserId, ValidatingError, is_valid, validate


def _permissions(value: typing.Any) -> Permissions:
    if isinstance(value, str):
        with suppress(ValueError):
            return Permissions.from_name(value)
    raise PydanticCustomError("enum", "Input should be 'none', 'read', 'write' or 'grant'")


def _group_exists(value: int) -> int:
    try:
        groups.get_group(value)
    except errors.GroupDoesNotExistError:
        raise PydanticCustomError("no_such_group", "Group should exist")
    return value


def _project_exists(value: int) -> int:
    try:
        projects.get_project(value)
    except errors.ProjectDoesNotExistError:
        raise PydanticCustomError("no_such_project", "Project should exist")
    return value


type _GroupId = typing.Annotated[int, AfterValidator(_group_exists)]
type _ProjectId = typing.Annotated[int, AfterValidator(_project_exists)]
type _Permissions = typing.Annotated[Permissions, BeforeValidator(_permissions)]
type _UnknownPermissions = typing.Annotated[_Permissions, _is_valid_unknown_permissions]
type _UserPermissions = typing.Dict[UserId, _Permissions]
type _GroupPermissions = typing.Dict[_GroupId, _Permissions]
type _ProjectPermissions = typing.Dict[_ProjectId, _Permissions]


def _is_valid_unknown_permissions(permissions: Permissions, /, type_: typing.Literal["authenticated", "anonymous"]) -> AfterValidator:
    return is_valid(
        lambda v, i: v in {Permissions.NONE, Permissions.READ},
        lambda i: PydanticCustomError(
            "unexpected",
            f"Permissions for {type_} users should be 'none' or 'read'",
            {"allowed": {Permissions.NONE, Permissions.READ}},
        ),
    )


class _ObjectPermissions(BaseModel):
    users: typing.Optional[_UserPermissions] = None
    groups: typing.Optional[_GroupPermissions] = None
    projects: typing.Optional[_ProjectPermissions] = None
    authenticated_users: typing.Optional[_UnknownPermissions] = None
    anonymous_users: typing.Optional[_UnknownPermissions] = None


def _check_object_exists(value: int) -> int:
    try:
        objects.check_object_exists(value)
    except errors.ObjectDoesNotExistError:
        raise PydanticCustomError("no_such_object", "Object should exist")
    return value


type ObjectId = typing.Annotated[int, AfterValidator(_check_object_exists)]


class _CopyObjectPermissions(BaseModel):
    source_object_id: ObjectId
    target_object_id: ObjectId


def all_object_permissions_dict_to_json(permissions: object_permissions.AllObjectPermissionsDict) -> typing.Dict[str, typing.Any]:
    return {
        "users": {
            user_id: permission.name.lower() for user_id, permission in permissions["users"].items()
        },
        "groups": {
            group_id: permission.name.lower() for group_id, permission in permissions["groups"].items()
        },
        "projects": {
            project_id: permission.name.lower() for project_id, permission in permissions["projects"].items()
        },
        "authenticated_users": permissions["authenticated"].name.lower(),
        "anonymous_users": permissions["anonymous"].name.lower(),
    }


class ObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        try:
            permissions = object_permissions.get_all_object_permissions(object_id=object_id)
        except errors.ObjectDoesNotExistError:
            return {
                "message": f"object {object_id} does not exist"
            }, 404
        return all_object_permissions_dict_to_json(
            permissions
        ), 200

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int) -> ResponseData:
        request_json = flask.request.get_json(force=True)
        try:
            request_data = validate(_ObjectPermissions, request_json)
        except ValidatingError as e:
            return e.response
        if request_data.anonymous_users is not None and not flask.current_app.config["ENABLE_ANONYMOUS_USERS"]:
            return {
                "message": "anonymous users are disabled"
            }, 400
        for user_id, permissions in (request_data.users or {}).items():
            object_permissions.set_user_object_permissions(
                object_id,
                user_id,
                permissions,
            )
        for group_id, permissions in (request_data.groups or {}).items():
            object_permissions.set_group_object_permissions(
                object_id,
                group_id,
                permissions,
            )
        for project_id, permissions in (request_data.projects or {}).items():
            object_permissions.set_project_object_permissions(
                object_id,
                project_id,
                permissions,
            )
        if request_data.authenticated_users is not None:
            object_permissions.set_object_permissions_for_all_users(
                object_id,
                request_data.authenticated_users,
            )
        if request_data.anonymous_users is not None:
            object_permissions.set_object_permissions_for_anonymous_users(
                object_id,
                request_data.anonymous_users,
            )
        return all_object_permissions_dict_to_json(
            object_permissions.get_all_object_permissions(object_id=object_id)
        ), 200


class CopyObjectsPermissions(Resource):
    @multi_auth.login_required
    def post(self) -> ResponseData:
        user_id = flask.g.user.id
        user = users.get_user(user_id=user_id)
        if user.is_readonly:
            return {
                "message": "No permission to copy object's permissions"
            }, 403
        request_json = flask.request.get_json(force=True)
        try:
            if not isinstance(request_json, list):
                request_data = [validate(_CopyObjectPermissions, request_json)]
            else:
                request_data = validate(typing.List[_CopyObjectPermissions], request_json)
        except ValidatingError as e:
            return e.response
        for item in request_data:
            # Assure highest permission for source object is atleast READ
            # to view object's permission
            if max(
                object_permissions.get_object_permissions_for_all_users(item.source_object_id),
                object_permissions.get_user_object_permissions(
                    object_id=item.source_object_id,
                    user_id=user_id,
                )
            ) < Permissions.READ:
                return {
                    "message": f"missing object permission for source object {item.source_object_id}"
                }, 403
            # Assure highest permission for target object is atleast GRANT
            # to allow permission-manipulation
            if object_permissions.get_user_object_permissions(
                object_id=item.target_object_id,
                user_id=user_id,
            ) < Permissions.GRANT:
                return {
                    "message": f"missing object permission for target object {item.target_object_id}"
                }, 403
        for item in request_data:
            object_permissions.copy_permissions(
                source_object_id=item.source_object_id,
                target_object_id=item.target_object_id,
            )
        return "", 200


class UserObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, user_id: int) -> ResponseData:
        include_instrument_responsible_users = 'include_instrument_responsible_users' in flask.request.args
        include_groups = 'include_groups' in flask.request.args
        include_projects = 'include_projects' in flask.request.args
        include_admins = 'include_admins' in flask.request.args
        permissions = object_permissions.get_object_permissions_for_users(
            object_id=object_id,
            include_instrument_responsible_users=include_instrument_responsible_users,
            include_groups=include_groups,
            include_projects=include_projects,
            include_admin_permissions=include_admins
        ).get(user_id, Permissions.NONE)
        if permissions == Permissions.NONE:
            try:
                users.check_user_exists(user_id)
            except errors.UserDoesNotExistError:
                return {
                    "message": f"user {user_id} does not exist"
                }, 404
        return permissions.name.lower()

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int, user_id: int) -> ResponseData:
        request_json = flask.request.get_json(force=True)
        try:
            validate(UserId, user_id)
        except ValidatingError as e:
            return e.response[0], 404
        try:
            permissions: Permissions = validate(_Permissions, request_json)
        except ValidatingError as e:
            return e.response
        object_permissions.set_user_object_permissions(object_id, user_id, permissions)
        background_tasks.post_trigger_object_permissions_webhooks(object_id)
        return permissions.name.lower(), 200


class UsersObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        include_instrument_responsible_users = 'include_instrument_responsible_users' in flask.request.args
        include_groups = 'include_groups' in flask.request.args
        include_projects = 'include_projects' in flask.request.args
        include_admins = 'include_admins' in flask.request.args
        permissions = object_permissions.get_object_permissions_for_users(
            object_id=object_id,
            include_instrument_responsible_users=include_instrument_responsible_users,
            include_groups=include_groups,
            include_projects=include_projects,
            include_admin_permissions=include_admins
        )
        return {
            user_id: permissions.name.lower()
            for user_id, permissions in permissions.items()
        }, 200


class GroupObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, group_id: int) -> ResponseData:
        include_projects = 'include_projects' in flask.request.args
        permissions = object_permissions.get_object_permissions_for_groups(
            object_id=object_id,
            include_projects=include_projects
        ).get(group_id, Permissions.NONE)
        if permissions == Permissions.NONE:
            try:
                groups.get_group(group_id)
            except errors.GroupDoesNotExistError:
                return {
                    "message": f"group {group_id} does not exist"
                }, 404
        return permissions.name.lower()

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int, group_id: int) -> ResponseData:
        request_json = flask.request.get_json(force=True)
        try:
            validate(_GroupId, group_id)
        except ValidatingError as e:
            return e.response[0], 404
        try:
            permissions: Permissions = validate(_Permissions, request_json)
        except ValidatingError as e:
            return e.response
        object_permissions.set_group_object_permissions(object_id, group_id, permissions)
        background_tasks.post_trigger_object_permissions_webhooks(object_id)
        return permissions.name.lower(), 200


class GroupsObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        include_projects = 'include_projects' in flask.request.args
        permissions = object_permissions.get_object_permissions_for_groups(
            object_id=object_id,
            include_projects=include_projects
        )
        return {
            group_id: permissions.name.lower()
            for group_id, permissions in permissions.items()
        }, 200


class ProjectObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, project_id: int) -> ResponseData:
        permissions = object_permissions.get_object_permissions_for_projects(
            object_id=object_id
        ).get(project_id, Permissions.NONE)
        if permissions == Permissions.NONE:
            try:
                projects.get_project(project_id)
            except errors.ProjectDoesNotExistError:
                return {
                    "message": f"project {project_id} does not exist"
                }, 404
        return permissions.name.lower()

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int, project_id: int) -> ResponseData:
        request_json = flask.request.get_json(force=True)
        try:
            validate(_ProjectId, project_id)
        except ValidatingError as e:
            return e.response[0], 404
        try:
            permissions: Permissions = validate(_Permissions, request_json)
        except ValidatingError as e:
            return e.response
        object_permissions.set_project_object_permissions(object_id, project_id, permissions)
        background_tasks.post_trigger_object_permissions_webhooks(object_id)
        return permissions.name.lower(), 200


class ProjectsObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        permissions = object_permissions.get_object_permissions_for_projects(
            object_id=object_id,
        )
        return {
            project_id: permissions.name.lower()
            for project_id, permissions in permissions.items()
        }, 200


class PublicObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        is_public = Permissions.READ in object_permissions.get_object_permissions_for_all_users(
            object_id=object_id
        )
        return is_public, 200

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int) -> ResponseData:
        request_json = flask.request.get_json(force=True)
        try:
            is_public: bool = validate(typing.Annotated[bool, Strict()], request_json)
        except ValidatingError as e:
            return e.response
        object_permissions.set_object_permissions_for_all_users(
            object_id=object_id,
            permissions=Permissions.READ if is_public else Permissions.NONE
        )
        background_tasks.post_trigger_object_permissions_webhooks(object_id)
        return is_public, 200


class AuthenticatedUserObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        permissions = object_permissions.get_object_permissions_for_all_users(
            object_id=object_id
        )
        return permissions.name.lower(), 200

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int) -> ResponseData:
        request_json = flask.request.get_json(force=True)
        try:
            permissions: Permissions = validate(_UnknownPermissions, request_json)
        except ValidatingError as e:
            return e.response
        object_permissions.set_object_permissions_for_all_users(
            object_id=object_id,
            permissions=permissions
        )
        background_tasks.post_trigger_object_permissions_webhooks(object_id)
        return permissions.name.lower(), 200


class AnonymousUserObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        if not flask.current_app.config['ENABLE_ANONYMOUS_USERS']:
            return {
                "message": "anonymous users are disabled"
            }, 400
        permissions = object_permissions.get_object_permissions_for_anonymous_users(
            object_id=object_id
        )
        return permissions.name.lower(), 200

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int) -> ResponseData:
        if not flask.current_app.config['ENABLE_ANONYMOUS_USERS']:
            return {
                "message": "anonymous users are disabled"
            }, 400
        request_json = flask.request.get_json(force=True)
        try:
            permissions: Permissions = validate(_UnknownPermissions, request_json)
        except ValidatingError as e:
            return e.response
        object_permissions.set_object_permissions_for_anonymous_users(
            object_id=object_id,
            permissions=permissions
        )
        background_tasks.post_trigger_object_permissions_webhooks(object_id)
        return permissions.name.lower(), 200
