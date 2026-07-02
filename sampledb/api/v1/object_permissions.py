# coding: utf-8
"""
RESTful API for SampleDB
"""

import functools
import typing
import flask

from .authentication import object_permissions_required, multi_auth
from ..utils import Resource, ResponseData
from ...logic import users, groups, projects, errors, object_permissions, background_tasks, objects
from ...models import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


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
        update_functions = []
        if type(request_json) is not dict:
            return {
                "message": "JSON dict body required"
            }, 400

        # User-Permissions
        if (user_perms_json := request_json.get("users")) is not None:
            if type(user_perms_json) is not dict:
                return {
                    "message": "'users' is required to be a JSON object"
                }, 400
            for user_id, permission in user_perms_json.items():
                try:
                    users.check_user_exists(int(user_id))
                except (errors.UserDoesNotExistError, ValueError):
                    return {
                        "message": f"user {user_id} does not exist"
                    }, 404
                if type(permission) is not str:
                    return {
                        "message": "JSON string for permission required"
                    }, 400
                try:
                    user_permissions = Permissions.from_name(permission)
                except ValueError:
                    return {
                        "message": f"Permissions name for user {user_id} required"
                    }, 400

                update_functions.append(
                    functools.partial(
                        object_permissions.set_user_object_permissions,
                        object_id,
                        user_id,
                        user_permissions,
                    )
                )

        # Group-Permissions
        if (group_perms_json := request_json.get("groups")) is not None:
            if type(group_perms_json) is not dict:
                return {
                    "message": "'groups' is required to be a JSON object"
                }, 400
            for group_id, permission in group_perms_json.items():
                try:
                    groups.get_group(int(group_id))
                except (errors.GroupDoesNotExistError, ValueError):
                    return {
                        "message": f"group {group_id} does not exist"
                    }, 404
                if type(permission) is not str:
                    return {
                        "message": "JSON string for permission required"
                    }, 400
                try:
                    group_permissions = Permissions.from_name(permission)
                except ValueError:
                    return {
                        "message": f"Permissions name for group {group_id} required"
                    }, 400

                update_functions.append(
                    functools.partial(
                        object_permissions.set_group_object_permissions,
                        object_id,
                        group_id,
                        group_permissions,
                    )
                )

        # Project-Permissions
        if (project_perms_json := request_json.get("projects")) is not None:
            if type(project_perms_json) is not dict:
                return {
                    "message": "'projects' is required to be a JSON object"
                }, 400
            for project_id, permission in project_perms_json.items():
                try:
                    projects.get_project(int(project_id))
                except (errors.ProjectDoesNotExistError, ValueError):
                    return {
                        "message": f"project {project_id} does not exist"
                    }, 404
                if type(permission) is not str:
                    return {
                        "message": "JSON string for permission required"
                    }, 400
                try:
                    project_permissions = Permissions.from_name(permission)
                except ValueError:
                    return {
                        "message": f"Permissions name for project {project_id} required"
                    }, 400

                update_functions.append(
                    functools.partial(
                        object_permissions.set_project_object_permissions,
                        object_id,
                        project_id,
                        project_permissions,
                    )
                )

        # Authenticated
        if (authenticated_perms_json := request_json.get("authenticated_users")) is not None:
            if type(authenticated_perms_json) is not str:
                return {
                    "message": "JSON string for permission required"
                }, 400
            try:
                authenticated_permissions = Permissions.from_name(authenticated_perms_json)
            except ValueError:
                return {
                    "message": "Permissions name for authenticated users required"
                }, 400

            if authenticated_permissions not in {Permissions.NONE, Permissions.READ}:
                return {
                    "message": 'expected "none" or "read"'
                }, 400

            update_functions.append(
                functools.partial(
                    object_permissions.set_object_permissions_for_all_users,
                    object_id,
                    authenticated_permissions,
                )
            )

        # Anonymous
        if (public_perms_json := request_json.get("anonymous_users")) is not None:
            if public_perms_json is not None and not flask.current_app.config['ENABLE_ANONYMOUS_USERS']:
                return {
                    "message": "anonymous users are disabled"
                }, 400
            if type(public_perms_json) is not str:
                return {
                    "message": "JSON string for permission required"
                }, 400
            try:
                public_permissions = Permissions.from_name(public_perms_json)
            except ValueError:
                return {
                    "message": "Permissions name for anonymous users required"
                }, 400

            if public_permissions not in {Permissions.NONE, Permissions.READ}:
                return {
                    "message": 'expected "none" or "read"'
                }, 400

            update_functions.append(
                functools.partial(
                    object_permissions.set_object_permissions_for_anonymous_users,
                    object_id,
                    public_permissions,
                )
            )

        for item in update_functions:
            item()

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
        if type(request_json) is dict:
            request_json = [request_json]
        elif type(request_json) is not list:
            return {
                "message": "JSON list or dict body required"
            }, 400
        try:
            for item in request_json:
                if type(item) is not dict:
                    return {
                        "message": "JSON list or dict body required"
                    }, 400
                source_object_id = item.get("source_object_id", None)
                target_object_id = item.get("target_object_id", None)
                if type(source_object_id) is not int:
                    return {
                        "message": "source_object_id for JSON object required"
                    }, 400
                if type(target_object_id) is not int:
                    return {
                        "message": "target_object_id for JSON object required"
                    }, 400
                # Validating all incoming object ids before changing any permission
                for object_id in [source_object_id, target_object_id]:
                    try:
                        objects.check_object_exists(object_id)
                    except errors.ObjectDoesNotExistError:
                        return {
                            "message": f"object {object_id} does not exist"
                        }, 404

                # Assure highest permission for source object is atleast READ
                # to view object's permission
                if max(
                    object_permissions.get_object_permissions_for_all_users(source_object_id),
                    object_permissions.get_user_object_permissions(
                        object_id=source_object_id,
                        user_id=user_id,
                    )
                ) < Permissions.READ:
                    return {
                        "message": f"missing object permission for source object {source_object_id}"
                    }, 403

                # Assure highest permission for target object is atleast GRANT
                # to allow permission-manipulation
                if object_permissions.get_user_object_permissions(
                    object_id=target_object_id,
                    user_id=user_id,
                ) < Permissions.GRANT:
                    return {
                        "message": f"missing object permission for target object {target_object_id}"
                    }, 403

        except ValueError:
            return {
                "message": "body parameters 'source' and 'target' are required to be object IDs"
            }, 400
        except KeyError:
            return {
                "message": "JSON dict body required 'source' and 'target' key"
            }, 400

        for item in request_json:
            object_permissions.copy_permissions(
                source_object_id=item["source_object_id"],
                target_object_id=item["target_object_id"],
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
        try:
            users.check_user_exists(user_id)
        except errors.UserDoesNotExistError:
            return {
                "message": f"user {user_id} does not exist"
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
        try:
            groups.get_group(group_id)
        except errors.GroupDoesNotExistError:
            return {
                "message": f"group {group_id} does not exist"
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
        try:
            projects.get_project(project_id)
        except errors.ProjectDoesNotExistError:
            return {
                "message": f"project {project_id} does not exist"
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
        if not isinstance(request_json, bool):
            return {
                "message": "JSON boolean body required"
            }, 400
        is_public = bool(request_json)
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
        if not isinstance(request_json, str):
            return {
                "message": "JSON string body required"
            }, 400
        try:
            permissions = Permissions.from_name(request_json)
            if permissions not in {Permissions.NONE, Permissions.READ}:
                raise ValueError("invalid permissions level")
        except ValueError:
            return {
                "message": 'expected "none" or "read"'
            }, 400
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
        if not isinstance(request_json, str):
            return {
                "message": "JSON string body required"
            }, 400
        try:
            permissions = Permissions.from_name(request_json)
            if permissions not in {Permissions.NONE, Permissions.READ}:
                raise ValueError("invalid permissions level")
        except ValueError:
            return {
                "message": 'expected "none" or "read"'
            }, 400
        object_permissions.set_object_permissions_for_anonymous_users(
            object_id=object_id,
            permissions=permissions
        )
        background_tasks.post_trigger_object_permissions_webhooks(object_id)
        return permissions.name.lower(), 200
