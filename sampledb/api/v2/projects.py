import typing

import flask
from pydantic import BaseModel, Field

from ...logic import errors, projects
from ...models import Permissions
from ..utils import Resource, ResponseData
from .authentication import multi_auth
from .utils.validation import UserId, method


def project_to_json(project: projects.Project) -> typing.Dict[str, typing.Any]:
    return {
        'project_id': project.id,
        'name': project.name,
        'description': project.description,
        'member_users': sorted(
            [
                {
                    'user_id': user_id,
                    'permissions': permissions.name.lower(),
                    'href': flask.url_for('.user', user_id=user_id, _external=True),
                } for user_id, permissions in projects.get_project_member_user_ids_and_permissions(project_id=project.id).items()
            ],
            key=lambda member_user: member_user['user_id']
        ),
        'member_groups': sorted(
            [
                {
                    'group_id': group_id,
                    'permissions': permissions.name.lower(),
                    'href': flask.url_for('.group', group_id=group_id, _external=True),
                }
                for group_id, permissions in projects.get_project_member_group_ids_and_permissions(project_id=project.id).items()
            ],
            key=lambda member_group: member_group['group_id']
        )
    }


class Projects(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> ResponseData:
        """
        List all project groups.
        """
        return [
            project_to_json(project)
            for project in sorted(projects.get_projects(), key=lambda project: project.id)
        ]


class Project(Resource):
    class PathModel(BaseModel):
        project_id: int = Field(description="the ID of an existing project group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get a project group.
        """
        try:
            project = projects.get_project(project_id=path.project_id)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {path.project_id} does not exist"
            }, 404
        return project_to_json(project)


class ProjectMemberUsers(Resource):
    class PathModel(BaseModel):
        project_id: int = Field(description="the ID of an existing project group", examples=[1])

    class RequestBodyModel(BaseModel):
        permissions: typing.Literal["read", "write", "grant"] = Field(description="the permissions to add this user with", examples=["read"])
        user_id: UserId = Field(description="the ID of an existing user to add to the project group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        List all member users of a project group.
        """
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage projects"
            }, 403
        try:
            project_permissions_by_member_id = projects.get_project_member_user_ids_and_permissions(project_id=path.project_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {path.project_id} does not exist"
            }, 404
        return [{
            'user_id': user_id,
            'permissions': project_permissions_by_member_id[user_id].name.lower(),
            'href': flask.url_for('.user', user_id=user_id, _external=True),
        } for user_id in sorted(project_permissions_by_member_id)]

    @multi_auth.login_required
    @method()
    def post(self, path: PathModel, request_body: RequestBodyModel) -> ResponseData:
        """
        Add a user to a project group.
        """
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage projects"
            }, 403
        if flask.g.user.is_readonly:
            return {
                "message": "Read-only users may not manage projects"
            }, 403
        try:
            projects.get_project(project_id=path.project_id)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {path.project_id} does not exist"
            }, 404
        user_id = request_body.user_id
        current_permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=user_id, include_groups=False)
        if current_permissions != Permissions.NONE:
            return {
                "message": "user is already a member of this project"
            }, 400
        permissions = {
            'read': Permissions.READ,
            'write': Permissions.WRITE,
            'grant': Permissions.GRANT,
        }[request_body.permissions]
        projects.add_user_to_project(path.project_id, user_id, permissions=permissions)
        return flask.redirect(flask.url_for('.project_member_user', project_id=path.project_id, user_id=user_id), code=201)


class ProjectMemberUser(Resource):
    class PathModel(BaseModel):
        project_id: int = Field(description="the ID of an existing project group", examples=[1])
        user_id: int = Field(description="the ID of an existing user", examples=[1])

    class RequestBodyModel(BaseModel):
        permissions: typing.Literal["read", "write", "grant"] = Field(description="the permissions to set this user to", examples=["read"])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get a member user of a project group.
        """
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage projects"
            }, 403
        try:
            permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=path.user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {path.project_id} does not exist"
            }, 404
        if permissions == Permissions.NONE:
            return {
                "message": "user is not a member of this project"
            }, 404
        return {
            'user_id': path.user_id,
            'permissions': permissions.name.lower(),
            'href': flask.url_for('.user', user_id=path.user_id, _external=True),
        }

    @multi_auth.login_required
    @method()
    def put(self, path: PathModel, request_body: RequestBodyModel) -> ResponseData:
        """
        Set the permissions of a member user of a project group.
        """
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage projects"
            }, 403
        if flask.g.user.is_readonly:
            return {
                "message": "Read-only users may not manage projects"
            }, 403
        try:
            current_permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=path.user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {path.project_id} does not exist"
            }, 404
        if current_permissions == Permissions.NONE:
            return {
                "message": "user is not a member of this project"
            }, 404
        permissions = {
            'read': Permissions.READ,
            'write': Permissions.WRITE,
            'grant': Permissions.GRANT,
        }[request_body.permissions]
        try:
            projects.update_user_project_permissions(project_id=path.project_id, user_id=path.user_id, permissions=permissions)
        except errors.NoMemberWithGrantPermissionsForProjectError:
            return {
                "message": "cannot change permissions for the only user with grant permissions for a project"
            }, 400
        return {
            'user_id': path.user_id,
            'permissions': permissions.name.lower(),
            'href': flask.url_for('.user', user_id=path.user_id, _external=True),
        }

    @multi_auth.login_required
    @method()
    def delete(self, path: PathModel) -> ResponseData:
        """
        Remove a user from a project group.
        """
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage projects"
            }, 403
        if flask.g.user.is_readonly:
            return {
                "message": "Read-only users may not manage projects"
            }, 403
        try:
            current_permissions = projects.get_user_project_permissions(project_id=path.project_id, user_id=path.user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {path.project_id} does not exist"
            }, 404
        if current_permissions == Permissions.NONE:
            return {
                "message": "user is not a member of this project"
            }, 404
        try:
            projects.remove_user_from_project(path.project_id, path.user_id)
        except errors.NoMemberWithGrantPermissionsForProjectError:
            return {
                "message": "cannot remove the only user with grant permissions for a project as long as there are other users"
            }, 400
        return {
            "message": f"user {path.user_id} has been removed from project {path.project_id}"
        }, 200
