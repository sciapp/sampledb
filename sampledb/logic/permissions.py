import typing

from . import settings, users, groups, projects
from ..models import Permissions
from .. import db


class ResourcePermissions(object):
    def __init__(
            self,
            resource_id_name: str,
            all_user_permissions_table: typing.Any,
            user_permissions_table: typing.Any,
            group_permissions_table: typing.Any,
            project_permissions_table: typing.Any,
            check_resource_exists: typing.Callable[[int], typing.Any]
    ) -> None:
        self._resource_id_name = resource_id_name
        self._all_user_permissions_table = all_user_permissions_table
        self._user_permissions_table = user_permissions_table
        self._group_permissions_table = group_permissions_table
        self._project_permissions_table = project_permissions_table
        self._check_resource_exists = check_resource_exists

    def get_permission_for_all_users(self, resource_id: int) -> Permissions:
        """
        Return the permissions all users have for a specific resource.

        :param resource_id: the ID of an existing resource
        :return: the permissions for all users
        """
        self._check_resource_exists(resource_id)

        all_user_permissions = self._all_user_permissions_table.query.filter_by(**{self._resource_id_name: resource_id}).first()
        if all_user_permissions is None:
            self._check_resource_exists(resource_id)
            return Permissions.NONE
        return all_user_permissions.permissions

    def set_permissions_for_all_users(self, resource_id: int, permissions: Permissions) -> None:
        """
        Set the permissions all users have for a specific resource.

        :param resource_id: the ID of an existing resource
        :param permissions: the permissions for all users
        """
        self._check_resource_exists(resource_id)

        if permissions == Permissions.NONE:
            self._all_user_permissions_table.query.filter_by(**{self._resource_id_name: resource_id}).delete()
        else:
            all_user_permissions = self._all_user_permissions_table.query.filter_by(**{self._resource_id_name: resource_id}).first()
            if all_user_permissions is None:
                all_user_permissions = self._all_user_permissions_table(permissions=permissions, **{self._resource_id_name: resource_id})
            else:
                all_user_permissions.permissions = permissions
            db.session.add(all_user_permissions)
        db.session.commit()

    def get_permissions_for_users(self, resource_id: int) -> typing.Dict[int, Permissions]:
        """
        Get explicitly granted permissions for users for a specific resource.

        This does not consider readonly users, groups, projects, admins or
        other modifications to user permissions.

        :param resource_id: the ID of an existing resource
        :return: a dict mapping users IDs to permissions
        """
        self._check_resource_exists(resource_id)

        permissions_for_users = {}
        for user_permissions in self._user_permissions_table.query.filter_by(**{self._resource_id_name: resource_id}).all():
            if user_permissions.permissions != Permissions.NONE:
                permissions_for_users[user_permissions.user_id] = user_permissions.permissions
        return permissions_for_users

    def set_permissions_for_user(self, resource_id: int, user_id: int, permissions: Permissions) -> None:
        """
        Set the permissions for a user for a specific resource.

        Clear the permissions if called with Permissions.NONE

        :param resource_id: the ID of an existing resource
        :param user_id: the ID of an existing user
        :param permissions: the new permissions
        """
        self._check_resource_exists(resource_id)
        # ensure that the user can be found
        users.get_user(user_id)

        if permissions == Permissions.NONE:
            self._user_permissions_table.query.filter_by(user_id=user_id, **{self._resource_id_name: resource_id}).delete()
        else:
            user_permissions = self._user_permissions_table.query.filter_by(user_id=user_id, **{self._resource_id_name: resource_id}).first()
            if user_permissions is None:
                user_permissions = self._user_permissions_table(user_id=user_id, permissions=permissions, **{self._resource_id_name: resource_id})
            else:
                user_permissions.permissions = permissions
            db.session.add(user_permissions)
        db.session.commit()

    def get_permissions_for_groups(self, resource_id: int) -> typing.Dict[int, Permissions]:
        """
        Get explicitly granted permissions for groups for a specific resource.

        This does not consider projects or other modifications to user
        permissions.

        :param resource_id: the ID of an existing resource
        :return: a dict mapping group IDs to permissions
        """
        self._check_resource_exists(resource_id)

        permissions_for_groups = {}
        for group_permissions in self._group_permissions_table.query.filter_by(**{self._resource_id_name: resource_id}).all():
            if group_permissions.permissions != Permissions.NONE:
                permissions_for_groups[group_permissions.group_id] = group_permissions.permissions
        return permissions_for_groups

    def set_permissions_for_group(self, resource_id: int, group_id: int, permissions: Permissions) -> None:
        """
        Set the permissions for a group for a specific resource.

        Clear the permissions if called with Permissions.NONE.

        :param resource_id: the ID of an existing resource
        :param group_id: the ID of an existing group
        :param permissions: the new permissions
        """
        self._check_resource_exists(resource_id)
        # ensure that the group can be found
        groups.get_group(group_id)

        if permissions == Permissions.NONE:
            self._group_permissions_table.query.filter_by(group_id=group_id, **{self._resource_id_name: resource_id}).delete()
        else:
            group_permissions = self._group_permissions_table.query.filter_by(group_id=group_id, **{self._resource_id_name: resource_id}).first()
            if group_permissions is None:
                group_permissions = self._group_permissions_table(group_id=group_id, permissions=permissions, **{self._resource_id_name: resource_id})
            else:
                group_permissions.permissions = permissions
            db.session.add(group_permissions)
        db.session.commit()

    def get_permissions_for_projects(self, resource_id: int) -> typing.Dict[int, Permissions]:
        """
        Get explicitly granted permissions for projects for a specific resource.

        :param resource_id: the ID of an existing resource
        :return: a dict mapping project IDs to permissions
        """
        self._check_resource_exists(resource_id)

        permissions_for_projects = {}
        for project_permissions in self._project_permissions_table.query.filter_by(**{self._resource_id_name: resource_id}).all():
            if project_permissions.permissions != Permissions.NONE:
                permissions_for_projects[project_permissions.project_id] = project_permissions.permissions
        return permissions_for_projects

    def set_permissions_for_project(self, resource_id: int, project_id: int, permissions: Permissions) -> None:
        """
        Set the permissions for a project for a specific resource.

        Clear the permissions if called with Permissions.NONE.

        :param resource_id: the ID of an existing resource
        :param project_id: the ID of an existing project
        :param permissions: the new permissions
        """
        self._check_resource_exists(resource_id)
        # ensure that the project can be found
        projects.get_project(project_id)

        if permissions == Permissions.NONE:
            self._project_permissions_table.query.filter_by(project_id=project_id, **{self._resource_id_name: resource_id}).delete()
        else:
            project_permissions = self._project_permissions_table.query.filter_by(project_id=project_id, **{self._resource_id_name: resource_id}).first()
            if project_permissions is None:
                project_permissions = self._project_permissions_table(project_id=project_id, permissions=permissions, **{self._resource_id_name: resource_id})
            else:
                project_permissions.permissions = permissions
            db.session.add(project_permissions)
        db.session.commit()

    def get_combined_permissions_for_user(
            self,
            resource_id: int,
            user_id: int,
            *,
            include_all_users: bool = True,
            include_groups: bool = True,
            include_projects: bool = True,
            include_admin_permissions: bool = True,
            limit_readonly_users: bool = True,
            additional_permissions: Permissions = Permissions.NONE
    ) -> Permissions:
        """
        Get combined permissions for a specific user for a specific resource.

        This does not consider instrument responsible users or other resource
        type dependent modifications to user permissions. Depending on the
        given arguments, it will however consider transitive permissions,
        admin permissions and readonly users.

        :param resource_id: the ID of an existing resource
        :param user_id: the ID of an existing user
        :param include_all_users: whether permissions for all users should be included
        :param include_groups: whether groups that the users are members of should be included
        :param include_projects: whether projects that the users are members of should be included
        :param include_admin_permissions: whether admin permissions should be included
        :param limit_readonly_users: whether readonly users should be limited to READ permissions
        :param additional_permissions: additional permissions to assume for this user
        :return: the combined permissions for the given user
        """
        self._check_resource_exists(resource_id)
        # ensure that the user can be found
        user = users.get_user(user_id)

        permissions = additional_permissions
        max_permissions = Permissions.GRANT

        # readonly users may never have more than READ permissions
        if user.is_readonly and limit_readonly_users:
            max_permissions = Permissions.READ

        if max_permissions not in permissions and include_admin_permissions:
            # administrators have GRANT permissions if they use admin permissions
            if user.is_admin and settings.get_user_settings(user.id)['USE_ADMIN_PERMISSIONS']:
                permissions = max(permissions, Permissions.GRANT)

        if max_permissions not in permissions and include_all_users:
            permissions = max(permissions, self.get_permission_for_all_users(resource_id))

        if max_permissions not in permissions:
            user_permissions = self._user_permissions_table.query.filter_by(user_id=user_id, **{self._resource_id_name: resource_id}).first()
            if user_permissions is not None:
                permissions = max(permissions, user_permissions.permissions)

        if max_permissions not in permissions and include_groups:
            group_permissions = self.get_permissions_for_groups(resource_id=resource_id)
            for group in groups.get_user_groups(user_id):
                permissions = max(permissions, group_permissions.get(group.id, Permissions.NONE))

        if max_permissions not in permissions and include_projects:
            project_permissions = self.get_permissions_for_projects(resource_id=resource_id)
            for project in projects.get_user_projects(user_id, include_groups=include_groups):
                max_project_permissions = projects.get_user_project_permissions(project_id=project.id, user_id=user_id, include_groups=include_groups)
                permissions = max(permissions, min(max_project_permissions, project_permissions.get(project.id, Permissions.NONE)))

        return permissions
