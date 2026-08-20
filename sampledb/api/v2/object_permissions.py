import typing
from contextlib import suppress

import flask
from pydantic import AfterValidator, BaseModel, BeforeValidator, Strict, Tag, Discriminator, SerializerFunctionWrapHandler, WrapSerializer, Field
from pydantic_core import PydanticCustomError

from .authentication import object_permissions_required, multi_auth
from ..utils import Resource
from ...logic import users, groups, projects, errors, object_permissions, background_tasks, objects
from ...models import Permissions
from .utils.validation import UserId, is_valid, method
from .utils.responses import NotFoundErrorModel, BadRequestErrorModel, ForbiddenErrorModel, NoContentModel, ReturnValue


def _permissions_validator(value: typing.Any) -> Permissions:
    if isinstance(value, Permissions):
        return value
    if isinstance(value, str):
        with suppress(ValueError):
            return Permissions.from_name(value)
    raise PydanticCustomError("enum", "Input should be 'none', 'read', 'write' or 'grant'")


def _permissions_serializer(permissions: Permissions, handler: SerializerFunctionWrapHandler) -> str:
    return permissions.name.lower()


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


def _is_valid_unknown_permissions(type_: typing.Literal["authenticated", "anonymous"], /) -> AfterValidator:
    return is_valid(
        lambda v, i: v in {Permissions.NONE, Permissions.READ},
        lambda i: PydanticCustomError(
            "unexpected",
            f"Permissions for {type_} users should be 'none' or 'read'",
            {"allowed": {Permissions.NONE, Permissions.READ}},
        ),
    )


type GroupId = typing.Annotated[int, AfterValidator(_group_exists)]
type ProjectId = typing.Annotated[int, AfterValidator(_project_exists)]
type PermissionsModel = typing.Annotated[Permissions, BeforeValidator(_permissions_validator), WrapSerializer(_permissions_serializer)]
type _AnonymousPermissions = typing.Annotated[PermissionsModel, _is_valid_unknown_permissions("anonymous")]
type _AuthenticatedPermissions = typing.Annotated[PermissionsModel, _is_valid_unknown_permissions("authenticated")]
type _UserPermissions = typing.Dict[UserId, PermissionsModel]
type _GroupPermissions = typing.Dict[GroupId, PermissionsModel]
type _ProjectPermissions = typing.Dict[ProjectId, PermissionsModel]


class _ObjectPermissions(BaseModel):
    users: typing.Optional[_UserPermissions] = Field(None, description="the permissions for users for this object", examples=[{"1": "grant"}])
    groups: typing.Optional[_GroupPermissions] = Field(None, description="the permissions for basic groups for this object", examples=[{"1": "read"}])
    projects: typing.Optional[_ProjectPermissions] = Field(None, description="the permissions for project groups for this object", examples=[{"1": "write"}])
    authenticated_users: typing.Optional[_AuthenticatedPermissions] = Field(None, description="the permissions for all authenticated users for this object", examples=["read"])
    anonymous_users: typing.Optional[_AnonymousPermissions] = Field(None, description="the permissions for anonymous users for this object", examples=["read"])


def _object_exists(value: int) -> int:
    try:
        objects.check_object_exists(value)
    except errors.ObjectDoesNotExistError:
        raise PydanticCustomError("no_such_object", "Object should exist")
    return value


type _ObjectId = typing.Annotated[int, AfterValidator(_object_exists)]


class _CopyObjectPermissions(BaseModel):
    source_object_id: _ObjectId = Field(description="the ID of an existing object to copy permissions from", examples=[1])
    target_object_id: _ObjectId = Field(description="the ID of an existing object to apply permissions to", examples=[2])


class AllObjectPermissionsModel(BaseModel):
    users: typing.Dict[int, str] = Field(description="the permissions for users for this object", examples=[{"1": "grant"}])
    groups: typing.Dict[int, str] = Field(description="the permissions for basic groups for this object", examples=[{"1": "read"}])
    projects: typing.Dict[int, str] = Field(description="the permissions for project groups for this object", examples=[{"1": "write"}])
    authenticated_users: str = Field(description="the permissions for all authenticated users for this object", examples=["read"])
    anonymous_users: str = Field(description="the permissions for anonymous users for this object", examples=["read"])

    @classmethod
    def from_all_object_permissions(cls, permissions: object_permissions.AllObjectPermissionsDict) -> typing.Self:
        return cls(
            users={
                user_id: permission.name.lower() for user_id, permission in permissions["users"].items()
            },
            groups={
                group_id: permission.name.lower() for group_id, permission in permissions["groups"].items()
            },
            projects={
                project_id: permission.name.lower() for project_id, permission in permissions["projects"].items()
            },
            authenticated_users=permissions["authenticated"].name.lower(),
            anonymous_users=permissions["anonymous"].name.lower(),
        )


class ObjectPermissions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> AllObjectPermissionsModel | NotFoundErrorModel:
        """
        Get all permissions for an object.
        """
        try:
            permissions = object_permissions.get_all_object_permissions(object_id=path.object_id)
        except errors.ObjectDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"object {path.object_id} does not exist"
            )
        return AllObjectPermissionsModel.from_all_object_permissions(
            permissions
        )

    @object_permissions_required(Permissions.GRANT)
    @method()
    def put(self, path: PathModel, request_body: _ObjectPermissions) -> AllObjectPermissionsModel | BadRequestErrorModel:
        """
        Set new permissions for an object.
        """
        if request_body.anonymous_users is not None and not flask.current_app.config["ENABLE_ANONYMOUS_USERS"]:
            return BadRequestErrorModel(
                error="Bad Request",
                message="anonymous users are disabled"
            )
        for user_id, permissions in (request_body.users or {}).items():
            object_permissions.set_user_object_permissions(
                path.object_id,
                user_id,
                permissions,
            )
        for group_id, permissions in (request_body.groups or {}).items():
            object_permissions.set_group_object_permissions(
                path.object_id,
                group_id,
                permissions,
            )
        for project_id, permissions in (request_body.projects or {}).items():
            object_permissions.set_project_object_permissions(
                path.object_id,
                project_id,
                permissions,
            )
        if request_body.authenticated_users is not None:
            object_permissions.set_object_permissions_for_all_users(
                path.object_id,
                request_body.authenticated_users,
            )
        if request_body.anonymous_users is not None:
            object_permissions.set_object_permissions_for_anonymous_users(
                path.object_id,
                request_body.anonymous_users,
            )
        return AllObjectPermissionsModel.from_all_object_permissions(
            object_permissions.get_all_object_permissions(object_id=path.object_id)
        )


class CopyObjectsPermissions(Resource):
    type RequestBodyModel = typing.Annotated[
        typing.Union[
            typing.Annotated[_CopyObjectPermissions, Tag('instance')],
            typing.Annotated[typing.List[_CopyObjectPermissions], Tag('list')],
        ],
        Discriminator(lambda v: 'list' if isinstance(v, list) else 'instance'),
    ]

    @multi_auth.login_required
    @method()
    def post(self, request_body: RequestBodyModel) -> NoContentModel | ForbiddenErrorModel:
        """
        Copy permissions from one object to another..
        """
        user_id = flask.g.user.id
        user = users.get_user(user_id=user_id)
        if user.is_readonly:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="No permission to copy object's permissions"
            )
        if not isinstance(request_body, list):
            request_body = [request_body]
        for item in request_body:
            # Assure highest permission for source object is atleast READ
            # to view object's permission
            if max(
                object_permissions.get_object_permissions_for_all_users(item.source_object_id),
                object_permissions.get_user_object_permissions(
                    object_id=item.source_object_id,
                    user_id=user_id,
                )
            ) < Permissions.READ:
                return ForbiddenErrorModel(
                    error="Forbidden",
                    message=f"missing object permission for source object {item.source_object_id}"
                )
            # Assure highest permission for target object is atleast GRANT
            # to allow permission-manipulation
            if object_permissions.get_user_object_permissions(
                object_id=item.target_object_id,
                user_id=user_id,
            ) < Permissions.GRANT:
                return ForbiddenErrorModel(
                    error="Forbidden",
                    message=f"missing object permission for target object {item.target_object_id}"
                )
        for item in request_body:
            object_permissions.copy_permissions(
                source_object_id=item.source_object_id,
                target_object_id=item.target_object_id,
            )
        return NoContentModel()


class UserObjectPermissions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])
        user_id: UserId = Field(description="the ID of an existing user", examples=[1])

    class QueryModel(BaseModel):
        include_instrument_responsible_users: bool = Field(False, description="whether to include permissions gained as an instrument responsible user", examples=[False])
        include_groups: bool = Field(False, description="whether to include permissions gained as an a member of a basic group", examples=[False])
        include_projects: bool = Field(False, description="whether to include permissions gained as an a member of a project group", examples=[False])
        include_admins: bool = Field(False, description="whether to include permissions gained as an administrator", examples=[False])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel, query: QueryModel) -> ReturnValue[PermissionsModel] | NotFoundErrorModel:
        """
        Get the object permissions for a user.
        """
        permissions = object_permissions.get_object_permissions_for_users(
            object_id=path.object_id,
            include_instrument_responsible_users=query.include_instrument_responsible_users,
            include_groups=query.include_groups,
            include_projects=query.include_projects,
            include_admin_permissions=query.include_admins
        ).get(path.user_id, Permissions.NONE)
        if permissions == Permissions.NONE:
            try:
                users.check_user_exists(path.user_id)
            except errors.UserDoesNotExistError:
                return NotFoundErrorModel(
                    error="Not Found",
                    message=f"user {path.user_id} does not exist"
                )
        return ReturnValue(permissions)

    @object_permissions_required(Permissions.GRANT)
    @method()
    def put(self, path: PathModel, request_body: PermissionsModel) -> ReturnValue[PermissionsModel]:
        """
        Set the object permissions for a user.
        """
        permissions = request_body
        object_permissions.set_user_object_permissions(path.object_id, path.user_id, permissions)
        background_tasks.post_trigger_object_permissions_webhooks(path.object_id)
        return ReturnValue(permissions)


class UsersObjectPermissions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    class QueryModel(BaseModel):
        include_instrument_responsible_users: bool = Field(False, description="whether to include permissions gained as an instrument responsible user", examples=[False])
        include_groups: bool = Field(False, description="whether to include permissions gained as an a member of a basic group", examples=[False])
        include_projects: bool = Field(False, description="whether to include permissions gained as an a member of a project group", examples=[False])
        include_admins: bool = Field(False, description="whether to include permissions gained as an administrator", examples=[False])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel, query: QueryModel) -> ReturnValue[typing.Dict[int, PermissionsModel]]:
        """
        Get the object permissions granted to users.
        """
        permissions = object_permissions.get_object_permissions_for_users(
            object_id=path.object_id,
            include_instrument_responsible_users=query.include_instrument_responsible_users,
            include_groups=query.include_groups,
            include_projects=query.include_projects,
            include_admin_permissions=query.include_admins
        )
        return ReturnValue({
            user_id: permissions
            for user_id, permissions in permissions.items()
        })


class GroupObjectPermissions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])
        group_id: GroupId = Field(description="the ID of an existing basic group", examples=[1])

    class QueryModel(BaseModel):
        include_projects: bool = Field(False, description="whether to include permissions gained as an a member of a project group", examples=[False])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel, query: QueryModel) -> ReturnValue[PermissionsModel] | NotFoundErrorModel:
        """
        Get the object permissions for a basic group.
        """
        permissions = object_permissions.get_object_permissions_for_groups(
            object_id=path.object_id,
            include_projects=query.include_projects
        ).get(path.group_id, Permissions.NONE)
        if permissions == Permissions.NONE:
            try:
                groups.get_group(path.group_id)
            except errors.GroupDoesNotExistError:
                return NotFoundErrorModel(
                    error="Not Found",
                    message=f"group {path.group_id} does not exist"
                )
        return ReturnValue(permissions)

    @object_permissions_required(Permissions.GRANT)
    @method()
    def put(self, path: PathModel, request_body: PermissionsModel) -> ReturnValue[PermissionsModel]:
        """
        Set the object permissions for a basic group.
        """
        permissions = request_body
        object_permissions.set_group_object_permissions(path.object_id, path.group_id, permissions)
        background_tasks.post_trigger_object_permissions_webhooks(path.object_id)
        return ReturnValue(permissions)


class GroupsObjectPermissions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    class QueryModel(BaseModel):
        include_projects: bool = Field(False, description="whether to include permissions gained as an a member of a project group", examples=[False])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel, query: QueryModel) -> ReturnValue[typing.Dict[int, PermissionsModel]]:
        """
        Get the object permissions granted to basic groups.
        """
        permissions = object_permissions.get_object_permissions_for_groups(
            object_id=path.object_id,
            include_projects=query.include_projects
        )
        return ReturnValue({
            group_id: permissions
            for group_id, permissions in permissions.items()
        })


class ProjectObjectPermissions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])
        project_id: ProjectId = Field(description="the ID of an existing project group", examples=[1])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ReturnValue[PermissionsModel] | NotFoundErrorModel:
        """
        Get the object permissions for a project group.
        """
        permissions = object_permissions.get_object_permissions_for_projects(
            object_id=path.object_id
        ).get(path.project_id, Permissions.NONE)
        if permissions == Permissions.NONE:
            try:
                projects.get_project(path.project_id)
            except errors.ProjectDoesNotExistError:
                return NotFoundErrorModel(
                    error="Not Found",
                    message=f"project {path.project_id} does not exist"
                )
        return ReturnValue(permissions)

    @object_permissions_required(Permissions.GRANT)
    @method()
    def put(self, path: PathModel, request_body: PermissionsModel) -> ReturnValue[PermissionsModel]:
        """
        Set the object permissions for a project group.
        """
        permissions = request_body
        object_permissions.set_project_object_permissions(path.object_id, path.project_id, permissions)
        background_tasks.post_trigger_object_permissions_webhooks(path.object_id)
        return ReturnValue(permissions)


class ProjectsObjectPermissions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ReturnValue[typing.Dict[int, PermissionsModel]]:
        """
        Get the object permissions granted to project groups.
        """
        permissions = object_permissions.get_object_permissions_for_projects(
            object_id=path.object_id,
        )
        return ReturnValue({
            project_id: permissions
            for project_id, permissions in permissions.items()
        })


class PublicObjectPermissions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    type RequestBodyModel = typing.Annotated[bool, Strict()]

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ReturnValue[bool]:
        """
        Get whether authenticated users have READ permissions.
        """
        is_public = Permissions.READ in object_permissions.get_object_permissions_for_all_users(
            object_id=path.object_id
        )
        return ReturnValue(is_public)

    @object_permissions_required(Permissions.GRANT)
    @method()
    def put(self, path: PathModel, request_body: RequestBodyModel) -> ReturnValue[bool]:
        """
        Set whether authenticated users have READ permissions.
        """
        is_public = request_body
        object_permissions.set_object_permissions_for_all_users(
            object_id=path.object_id,
            permissions=Permissions.READ if is_public else Permissions.NONE
        )
        background_tasks.post_trigger_object_permissions_webhooks(path.object_id)
        return ReturnValue(is_public)


class AuthenticatedUserObjectPermissions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ReturnValue[PermissionsModel]:
        """
        Get the object permissions for authenticated users.
        """
        permissions = object_permissions.get_object_permissions_for_all_users(
            object_id=path.object_id
        )
        return ReturnValue(permissions)

    @object_permissions_required(Permissions.GRANT)
    @method()
    def put(self, path: PathModel, request_body: _AuthenticatedPermissions) -> ReturnValue[PermissionsModel]:
        """
        Set the object permissions for authenticated users.
        """
        permissions = request_body
        object_permissions.set_object_permissions_for_all_users(
            object_id=path.object_id,
            permissions=permissions
        )
        background_tasks.post_trigger_object_permissions_webhooks(path.object_id)
        return ReturnValue(permissions)


class AnonymousUserObjectPermissions(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ReturnValue[PermissionsModel] | BadRequestErrorModel:
        """
        Get the object permissions for anonymous users.
        """
        if not flask.current_app.config['ENABLE_ANONYMOUS_USERS']:
            return BadRequestErrorModel(
                error="Bad Request",
                message="anonymous users are disabled"
            )
        permissions = object_permissions.get_object_permissions_for_anonymous_users(
            object_id=path.object_id
        )
        return ReturnValue(permissions)

    @object_permissions_required(Permissions.GRANT)
    @method()
    def put(self, path: PathModel, request_body: _AnonymousPermissions) -> ReturnValue[PermissionsModel] | BadRequestErrorModel:
        """
        Set the object permissions for anonymous users.
        """
        if not flask.current_app.config['ENABLE_ANONYMOUS_USERS']:
            return BadRequestErrorModel(
                error="Bad Request",
                message="anonymous users are disabled"
            )
        permissions = request_body
        object_permissions.set_object_permissions_for_anonymous_users(
            object_id=path.object_id,
            permissions=permissions
        )
        background_tasks.post_trigger_object_permissions_webhooks(path.object_id)
        return ReturnValue(permissions)
