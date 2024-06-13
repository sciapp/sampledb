# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic import errors, projects


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
