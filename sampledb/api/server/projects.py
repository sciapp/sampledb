import typing

import flask
from pydantic import BaseModel

from ...logic import errors, projects
from ...models import Permissions
from ..utils import Resource, ResponseData
from .authentication import multi_auth
from .validation_utils import UserId, ValidatingError, validate


class _ProjectMemberUser(BaseModel):
    permissions: typing.Literal["read", "write", "grant"]


class _ProjectMemberUsers(_ProjectMemberUser):
    user_id: UserId


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
                    'href': flask.url_for('api.user', user_id=user_id, _external=True),
                } for user_id, permissions in projects.get_project_member_user_ids_and_permissions(project_id=project.id).items()
            ],
            key=lambda member_user: member_user['user_id']
        ),
        'member_groups': sorted(
            [
                {
                    'group_id': group_id,
                    'permissions': permissions.name.lower(),
                    'href': flask.url_for('api.group', group_id=group_id, _external=True),
                }
                for group_id, permissions in projects.get_project_member_group_ids_and_permissions(project_id=project.id).items()
            ],
            key=lambda member_group: member_group['group_id']
        )
    }


class Projects(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        return [
            project_to_json(project)
            for project in sorted(projects.get_projects(), key=lambda project: project.id)
        ]


class Project(Resource):
    @multi_auth.login_required
    def get(self, project_id: int) -> ResponseData:
        try:
            project = projects.get_project(project_id=project_id)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {project_id} does not exist"
            }, 404
        return project_to_json(project)


class ProjectMemberUsers(Resource):
    @multi_auth.login_required
    def get(self, project_id: int) -> ResponseData:
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage projects"
            }, 403
        try:
            project_permissions_by_member_id = projects.get_project_member_user_ids_and_permissions(project_id=project_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {project_id} does not exist"
            }, 404
        return [{
            'user_id': user_id,
            'permissions': project_permissions_by_member_id[user_id].name.lower(),
            'href': flask.url_for('api.user', user_id=user_id, _external=True),
        } for user_id in sorted(project_permissions_by_member_id)]

    @multi_auth.login_required
    def post(self, project_id: int) -> ResponseData:
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage projects"
            }, 403
        if flask.g.user.is_readonly:
            return {
                "message": "Read-only users may not manage projects"
            }, 403
        try:
            projects.get_project(project_id=project_id)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {project_id} does not exist"
            }, 404
        request_json = flask.request.get_json(force=True)
        try:
            request_data = validate(_ProjectMemberUsers, request_json)
        except ValidatingError as err:
            return err.response
        user_id = request_data.user_id
        current_permissions = projects.get_user_project_permissions(project_id=project_id, user_id=user_id, include_groups=False)
        if current_permissions != Permissions.NONE:
            return {
                "message": "user is already a member of this project"
            }, 400
        permissions = {
            'read': Permissions.READ,
            'write': Permissions.WRITE,
            'grant': Permissions.GRANT,
        }[request_data.permissions]
        projects.add_user_to_project(project_id, user_id, permissions=permissions)
        return flask.redirect(flask.url_for('.project_member_user', project_id=project_id, user_id=user_id), code=201)


class ProjectMemberUser(Resource):
    @multi_auth.login_required
    def get(self, project_id: int, user_id: int) -> ResponseData:
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage projects"
            }, 403
        try:
            permissions = projects.get_user_project_permissions(project_id=project_id, user_id=user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {project_id} does not exist"
            }, 404
        if permissions == Permissions.NONE:
            return {
                "message": "user is not a member of this project"
            }, 404
        return {
            'user_id': user_id,
            'permissions': permissions.name.lower(),
            'href': flask.url_for('api.user', user_id=user_id, _external=True),
        }

    @multi_auth.login_required
    def put(self, project_id: int, user_id: int) -> ResponseData:
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage projects"
            }, 403
        if flask.g.user.is_readonly:
            return {
                "message": "Read-only users may not manage projects"
            }, 403
        try:
            current_permissions = projects.get_user_project_permissions(project_id=project_id, user_id=user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {project_id} does not exist"
            }, 404
        if current_permissions == Permissions.NONE:
            return {
                "message": "user is not a member of this project"
            }, 404
        request_json = flask.request.get_json(force=True)
        try:
            request_data = validate(_ProjectMemberUser, request_json)
        except ValidatingError as err:
            return err.response
        permissions = {
            'read': Permissions.READ,
            'write': Permissions.WRITE,
            'grant': Permissions.GRANT,
        }[request_data.permissions]
        try:
            projects.update_user_project_permissions(project_id=project_id, user_id=user_id, permissions=permissions)
        except errors.NoMemberWithGrantPermissionsForProjectError:
            return {
                "message": "cannot change permissions for the only user with grant permissions for a project"
            }, 400
        return {
            'user_id': user_id,
            'permissions': permissions.name.lower(),
            'href': flask.url_for('api.user', user_id=user_id, _external=True),
        }

    @multi_auth.login_required
    def delete(self, project_id: int, user_id: int) -> ResponseData:
        if not flask.g.user.is_admin:
            return {
                "message": "Only admins may manage projects"
            }, 403
        if flask.g.user.is_readonly:
            return {
                "message": "Read-only users may not manage projects"
            }, 403
        try:
            current_permissions = projects.get_user_project_permissions(project_id=project_id, user_id=user_id, include_groups=False)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {project_id} does not exist"
            }, 404
        if current_permissions == Permissions.NONE:
            return {
                "message": "user is not a member of this project"
            }, 404
        try:
            projects.remove_user_from_project(project_id, user_id)
        except errors.NoMemberWithGrantPermissionsForProjectError:
            return {
                "message": "cannot remove the only user with grant permissions for a project as long as there are other users"
            }, 400
        return {
            "message": f"user {user_id} has been removed from project {project_id}"
        }, 200
