# coding: utf-8
"""
RESTful API for SampleDB
"""

import flask
from flask_restful import Resource

from .authentication import object_permissions_required, Permissions
from ...logic import users, groups, projects, errors, object_permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class UserObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, user_id: int):
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
                users.get_user(user_id)
            except errors.UserDoesNotExistError:
                return {
                    "message": "user {} does not exist".format(user_id)
                }, 404
        return permissions.name.lower()

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int, user_id: int):
        try:
            users.get_user(user_id)
        except errors.UserDoesNotExistError:
            return {
                "message": "user {} does not exist".format(user_id)
            }, 404
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, str):
            return {
                "message": "JSON string body required"
            }, 400
        try:
            permissions = Permissions.from_name(request_json)
        except ValueError:
            return {
                "message": "Permissions name required"
            }, 400
        object_permissions.set_user_object_permissions(object_id, user_id, permissions)
        return permissions.name.lower(), 200


class UsersObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int):
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
    def get(self, object_id: int, group_id: int):
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
                    "message": "group {} does not exist".format(group_id)
                }, 404
        return permissions.name.lower()

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int, group_id: int):
        try:
            groups.get_group(group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": "group {} does not exist".format(group_id)
            }, 404
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, str):
            return {
                "message": "JSON string body required"
            }, 400
        try:
            permissions = Permissions.from_name(request_json)
        except ValueError:
            return {
                "message": "Permissions name required"
            }, 400
        object_permissions.set_group_object_permissions(object_id, group_id, permissions)
        return permissions.name.lower(), 200


class GroupsObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int):
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
    def get(self, object_id: int, project_id: int):
        permissions = object_permissions.get_object_permissions_for_projects(
            object_id=object_id
        ).get(project_id, Permissions.NONE)
        if permissions == Permissions.NONE:
            try:
                projects.get_project(project_id)
            except errors.ProjectDoesNotExistError:
                return {
                    "message": "project {} does not exist".format(project_id)
                }, 404
        return permissions.name.lower()

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int, project_id: int):
        try:
            projects.get_project(project_id)
        except errors.ProjectDoesNotExistError:
            return {
                "message": "project {} does not exist".format(project_id)
            }, 404
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, str):
            return {
                "message": "JSON string body required"
            }, 400
        try:
            permissions = Permissions.from_name(request_json)
        except ValueError:
            return {
                "message": "Permissions name required"
            }, 400
        object_permissions.set_project_object_permissions(object_id, project_id, permissions)
        return permissions.name.lower(), 200


class ProjectsObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int):
        permissions = object_permissions.get_object_permissions_for_projects(
            object_id=object_id,
        )
        return {
            project_id: permissions.name.lower()
            for project_id, permissions in permissions.items()
        }, 200


class PublicObjectPermissions(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int):
        is_public = object_permissions.object_is_public(
            object_id=object_id,
        )
        return is_public, 200

    @object_permissions_required(Permissions.GRANT)
    def put(self, object_id: int):
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, bool):
            return {
                "message": "JSON boolean body required"
            }, 400
        is_public = bool(request_json)
        object_permissions.set_object_public(object_id, is_public)
        return is_public, 200
