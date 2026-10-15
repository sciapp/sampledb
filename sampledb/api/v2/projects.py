import typing
from http import HTTPStatus

import flask
from pydantic import BaseModel, Field

from ...logic import errors, projects
from ...models import Permissions
from ..utils import Resource
from .authentication import multi_auth
from .utils.validation import UserId, generate_example, PermissionsModel
from .utils.responses import CreatedResponseModel, NoContentModel, ErrorDetailsModel, PaginatedSequence, \
    PaginationQueryModel
from .utils.openapi import method


class ProjectMemberUserRefModel(BaseModel):
    user_id: int = Field(description="the ID of the referenced user", examples=[1])
    permissions: PermissionsModel = Field(description="the permissions for the referenced user", examples=[1])
    href: str = Field(description="the URL of the API endpoint for the referenced user", examples=["https://example.com/api/v2/users/1"])

    @classmethod
    def from_user_id_and_permissions(cls, user_id: int, permissions: Permissions) -> typing.Self:
        return cls(
            user_id=user_id,
            permissions=permissions,
            href=flask.url_for('.user', user_id=user_id, _external=True),
        )


class ProjectMemberGroupRefModel(BaseModel):
    group_id: int = Field(description="the ID of the referenced basic group", examples=[1])
    permissions: PermissionsModel = Field(description="the permissions for the referenced basic group", examples=[1])
    href: str = Field(description="the URL of the API endpoint for the referenced basic group", examples=["https://example.com/api/v2/groups/1"])

    @classmethod
    def from_group_id_and_permissions(cls, group_id: int, permissions: Permissions) -> typing.Self:
        return cls(
            group_id=group_id,
            permissions=permissions,
            href=flask.url_for('.group', group_id=group_id, _external=True),
        )


class ProjectModel(BaseModel):
    project_id: int = Field(description="the ID of the project group", examples=[1])
    name: dict[str, str] = Field(description="the name of the project group", examples=[{"en": "Example Project Group"}])
    description: dict[str, str] = Field(description="the description of the project group", examples=[{"en": "This is an example project group."}])
    member_users: list[ProjectMemberUserRefModel] = Field(description="the list of users who are members of the project group", examples=[
        [generate_example(ProjectMemberUserRefModel)]
    ])
    member_groups: list[ProjectMemberGroupRefModel] = Field(description="the list of basic groups who are members of the project group", examples=[
        [generate_example(ProjectMemberGroupRefModel)]
    ])

    @classmethod
    def from_project(cls, project: projects.Project) -> typing.Self:
        return cls(
            project_id=project.id,
            name=project.name,
            description=project.description,
            member_users=sorted(
                [
                    ProjectMemberUserRefModel.from_user_id_and_permissions(user_id, permissions)
                    for user_id, permissions in projects.get_project_member_user_ids_and_permissions(project_id=project.id).items()
                ],
                key=lambda user_ref: user_ref.user_id
            ),
            member_groups=sorted(
                [
                    ProjectMemberGroupRefModel.from_group_id_and_permissions(group_id, permissions)
                    for group_id, permissions in projects.get_project_member_group_ids_and_permissions(project_id=project.id).items()
                ],
                key=lambda group_ref: group_ref.group_id
            ),
        )


class ProjectNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The requested project group does not exist."


class OnlyAdminsMayManageProjectsModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.FORBIDDEN
    TITLE: typing.ClassVar[str] = "Only administrators may manage project groups."


class UserAlreadyIsProjectMemberModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.BAD_REQUEST
    TITLE: typing.ClassVar[str] = "The user is already a member of this project group."


class UserIsNoProjectMemberModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The user is not a member of this project group."


class CannotRemoveOnlyGrantUserFromProjectModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.BAD_REQUEST
    TITLE: typing.ClassVar[str] = "Cannot remove the only user with GRANT permissions from a project group while there are still other members in the project group."


class CannotChangePermissionsOfOnlyGrantUserInProjectModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.BAD_REQUEST
    TITLE: typing.ClassVar[str] = "Cannot change the permissions for the only user with GRANT permissions in a project group."


class Projects(Resource):
    @multi_auth.login_required
    @method()
    def get(self, query: PaginationQueryModel) -> PaginatedSequence[ProjectModel]:
        """
        List all project groups.
        """
        all_projects = projects.get_projects()
        return PaginatedSequence.apply_pagination(
            items=[
                ProjectModel.from_project(project)
                for project in all_projects
            ],
            query=query,
            id_getter=lambda project: project.project_id,
        )


class Project(Resource):
    class PathModel(BaseModel):
        project_id: int = Field(description="the ID of an existing project group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ProjectModel | ProjectNotFoundModel:
        """
        Get a project group.
        """
        try:
            project = projects.get_project(project_id=path.project_id)
        except errors.ProjectDoesNotExistError:
            return ProjectNotFoundModel(
                detail=f"Project group #{path.project_id} does not exist."
            )
        return ProjectModel.from_project(project)


class ProjectMemberUsers(Resource):
    class PathModel(BaseModel):
        project_id: int = Field(description="the ID of an existing project group", examples=[1])

    class RequestBodyModel(BaseModel):
        permissions: typing.Literal["read", "write", "grant"] = Field(description="the permissions to add this user with", examples=["read"])
        user_id: UserId = Field(description="the ID of an existing user to add to the project group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel, query: PaginationQueryModel) -> PaginatedSequence[ProjectMemberUserRefModel] | OnlyAdminsMayManageProjectsModel | ProjectNotFoundModel:
        """
        List all member users of a project group.
        """
        if not flask.g.user.is_admin:
            return OnlyAdminsMayManageProjectsModel(
                detail=f"User #{flask.g.user.id} is no administrator, but only administrators may manage project groups."
            )
        try:
            project_permissions_by_member_id = projects.get_project_member_user_ids_and_permissions(project_id=path.project_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return ProjectNotFoundModel(
                detail=f"Project group #{path.project_id} does not exist."
            )
        return PaginatedSequence.apply_pagination(
            items=[
                ProjectMemberUserRefModel.from_user_id_and_permissions(user_id, project_permissions_by_member_id[user_id])
                for user_id in project_permissions_by_member_id
            ],
            query=query,
            path=path,
            id_getter=lambda user_ref: user_ref.user_id,
        )

    @multi_auth.login_required
    @method()
    def post(self, path: PathModel, request_body: RequestBodyModel) -> CreatedResponseModel | OnlyAdminsMayManageProjectsModel | ProjectNotFoundModel | UserAlreadyIsProjectMemberModel:
        """
        Add a user to a project group.
        """
        if not flask.g.user.is_admin:
            return OnlyAdminsMayManageProjectsModel(
                detail=f"User #{flask.g.user.id} is no administrator, but only administrators may manage project groups."
            )
        try:
            projects.get_project(project_id=path.project_id)
        except errors.ProjectDoesNotExistError:
            return ProjectNotFoundModel(
                detail=f"Project group #{path.project_id} does not exist."
            )
        user_id = request_body.user_id
        current_permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=user_id, include_groups=False)
        if current_permissions != Permissions.NONE:
            return UserAlreadyIsProjectMemberModel(
                detail=f"User {user_id} is already a member of project group #{path.project_id}."
            )
        permissions = {
            'read': Permissions.READ,
            'write': Permissions.WRITE,
            'grant': Permissions.GRANT,
        }[request_body.permissions]
        projects.add_user_to_project(path.project_id, user_id, permissions=permissions)
        return CreatedResponseModel(
            location=flask.url_for(
                '.project_member_user',
                project_id=path.project_id,
                user_id=user_id
            )
        )


class ProjectMemberUser(Resource):
    class PathModel(BaseModel):
        project_id: int = Field(description="the ID of an existing project group", examples=[1])
        user_id: int = Field(description="the ID of an existing user", examples=[1])

    class RequestBodyModel(BaseModel):
        permissions: typing.Literal["read", "write", "grant"] = Field(description="the permissions to set this user to", examples=["read"])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ProjectMemberUserRefModel | OnlyAdminsMayManageProjectsModel | ProjectNotFoundModel | UserIsNoProjectMemberModel:
        """
        Get a member user of a project group.
        """
        if not flask.g.user.is_admin:
            return OnlyAdminsMayManageProjectsModel(
                detail=f"User #{flask.g.user.id} is no administrator, but only administrators may manage project groups."
            )
        try:
            permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=path.user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return ProjectNotFoundModel(
                detail=f"Project group #{path.project_id} does not exist."
            )
        if permissions == Permissions.NONE:
            return UserIsNoProjectMemberModel(
                detail=f"User #{path.user_id} is not a member of project group #{path.project_id}."
            )
        return ProjectMemberUserRefModel.from_user_id_and_permissions(path.user_id, permissions)

    @multi_auth.login_required
    @method()
    def put(self, path: PathModel, request_body: RequestBodyModel) -> ProjectMemberUserRefModel | OnlyAdminsMayManageProjectsModel | ProjectNotFoundModel | UserIsNoProjectMemberModel | CannotChangePermissionsOfOnlyGrantUserInProjectModel:
        """
        Set the permissions of a member user of a project group.
        """
        if not flask.g.user.is_admin:
            return OnlyAdminsMayManageProjectsModel(
                detail=f"User #{flask.g.user.id} is no administrator, but only administrators may manage project groups."
            )
        try:
            current_permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=path.user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return ProjectNotFoundModel(
                detail=f"Project group #{path.project_id} does not exist."
            )
        if current_permissions == Permissions.NONE:
            return UserIsNoProjectMemberModel(
                detail=f"User #{path.user_id} is not a member of project group #{path.project_id}."
            )
        permissions = {
            'read': Permissions.READ,
            'write': Permissions.WRITE,
            'grant': Permissions.GRANT,
        }[request_body.permissions]
        try:
            projects.update_user_project_permissions(project_id=path.project_id, user_id=path.user_id, permissions=permissions)
        except errors.NoMemberWithGrantPermissionsForProjectError:
            return CannotChangePermissionsOfOnlyGrantUserInProjectModel(
                detail=f"User #{path.user_id} is the only user with GRANT permissions for project group #{path.project_id}."
            )
        return ProjectMemberUserRefModel.from_user_id_and_permissions(path.user_id, permissions)

    @multi_auth.login_required
    @method()
    def delete(self, path: PathModel) -> NoContentModel | OnlyAdminsMayManageProjectsModel | ProjectNotFoundModel | UserIsNoProjectMemberModel | CannotRemoveOnlyGrantUserFromProjectModel:
        """
        Remove a user from a project group.
        """
        if not flask.g.user.is_admin:
            return OnlyAdminsMayManageProjectsModel(
                detail=f"User #{flask.g.user.id} is no administrator, but only administrators may manage project groups."
            )
        try:
            current_permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=path.user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return ProjectNotFoundModel(
                detail=f"Project group #{path.project_id} does not exist."
            )
        if current_permissions == Permissions.NONE:
            return UserIsNoProjectMemberModel(
                detail=f"User #{path.user_id} is not a member of project group #{path.project_id}."
            )
        try:
            projects.remove_user_from_project(path.project_id, path.user_id)
        except errors.NoMemberWithGrantPermissionsForProjectError:
            return CannotRemoveOnlyGrantUserFromProjectModel(
                detail=f"User #{path.user_id} is the only user with GRANT permissions for project group #{path.project_id} and there are still other members in the project group."
            )
        return NoContentModel()
