import typing

import flask
from pydantic import BaseModel, Field

from ...logic import errors, projects
from ...models import Permissions
from ..utils import Resource
from .authentication import multi_auth
from .utils.validation import UserId, generate_example
from .utils.responses import NotFoundErrorModel, ForbiddenErrorModel, CreatedResponseModel, BadRequestErrorModel, NoContentModel
from .utils.openapi import method
from .object_permissions import PermissionsModel


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


class Projects(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> list[ProjectModel]:
        """
        List all project groups.
        """
        return [
            ProjectModel.from_project(project)
            for project in sorted(projects.get_projects(), key=lambda project: project.id)
        ]


class Project(Resource):
    class PathModel(BaseModel):
        project_id: int = Field(description="the ID of an existing project group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ProjectModel | NotFoundErrorModel:
        """
        Get a project group.
        """
        try:
            project = projects.get_project(project_id=path.project_id)
        except errors.ProjectDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"project {path.project_id} does not exist"
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
    def get(self, path: PathModel) -> list[ProjectMemberUserRefModel] | ForbiddenErrorModel | NotFoundErrorModel:
        """
        List all member users of a project group.
        """
        if not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Only admins may manage projects"
            )
        try:
            project_permissions_by_member_id = projects.get_project_member_user_ids_and_permissions(project_id=path.project_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"project {path.project_id} does not exist"
            )
        return [
            ProjectMemberUserRefModel.from_user_id_and_permissions(user_id, project_permissions_by_member_id[user_id])
            for user_id in sorted(project_permissions_by_member_id)
        ]

    @multi_auth.login_required
    @method()
    def post(self, path: PathModel, request_body: RequestBodyModel) -> CreatedResponseModel | BadRequestErrorModel | ForbiddenErrorModel | NotFoundErrorModel:
        """
        Add a user to a project group.
        """
        if not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Only admins may manage projects"
            )
        if flask.g.user.is_readonly:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Read-only users may not manage projects"
            )
        try:
            projects.get_project(project_id=path.project_id)
        except errors.ProjectDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"project {path.project_id} does not exist"
            )
        user_id = request_body.user_id
        current_permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=user_id, include_groups=False)
        if current_permissions != Permissions.NONE:
            return BadRequestErrorModel(
                error="Bad Request",
                message="user is already a member of this project"
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
    def get(self, path: PathModel) -> ProjectMemberUserRefModel | ForbiddenErrorModel | NotFoundErrorModel:
        """
        Get a member user of a project group.
        """
        if not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Only admins may manage projects"
            )
        try:
            permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=path.user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"project {path.project_id} does not exist"
            )
        if permissions == Permissions.NONE:
            return NotFoundErrorModel(
                error="Not Found",
                message="user is not a member of this project"
            )
        return ProjectMemberUserRefModel.from_user_id_and_permissions(path.user_id, permissions)

    @multi_auth.login_required
    @method()
    def put(self, path: PathModel, request_body: RequestBodyModel) -> ProjectMemberUserRefModel | BadRequestErrorModel | ForbiddenErrorModel | NotFoundErrorModel:
        """
        Set the permissions of a member user of a project group.
        """
        if not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Only admins may manage projects"
            )
        if flask.g.user.is_readonly:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Read-only users may not manage projects"
            )
        try:
            current_permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=path.user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"project {path.project_id} does not exist"
            )
        if current_permissions == Permissions.NONE:
            return NotFoundErrorModel(
                error="Not Found",
                message="user is not a member of this project"
            )
        permissions = {
            'read': Permissions.READ,
            'write': Permissions.WRITE,
            'grant': Permissions.GRANT,
        }[request_body.permissions]
        try:
            projects.update_user_project_permissions(project_id=path.project_id, user_id=path.user_id, permissions=permissions)
        except errors.NoMemberWithGrantPermissionsForProjectError:
            return BadRequestErrorModel(
                error="Bad Request",
                message="cannot change permissions for the only user with grant permissions for a project"
            )
        return ProjectMemberUserRefModel.from_user_id_and_permissions(path.user_id, permissions)

    @multi_auth.login_required
    @method()
    def delete(self, path: PathModel) -> NoContentModel | BadRequestErrorModel | ForbiddenErrorModel | NotFoundErrorModel:
        """
        Remove a user from a project group.
        """
        if not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Only admins may manage projects"
            )
        if flask.g.user.is_readonly:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Read-only users may not manage projects"
            )
        try:
            current_permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=path.user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"project {path.project_id} does not exist"
            )
        if current_permissions == Permissions.NONE:
            return NotFoundErrorModel(
                error="Not Found",
                message="user is not a member of this project"
            )
        try:
            projects.remove_user_from_project(path.project_id, path.user_id)
        except errors.NoMemberWithGrantPermissionsForProjectError:
            return BadRequestErrorModel(
                error="Bad Request",
                message="cannot remove the only user with grant permissions for a project as long as there are other users"
            )
        return NoContentModel()
