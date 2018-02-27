# coding: utf-8
"""
Logic module for user managed projects

Users can create uniquely named projects and use them to more easily manage
permissions for samples or measurements. Users with GRANT permissions for a
project can add new users and manage other users' permissions.

When a project is given permissions for an object, users will get whatever
level of permissions is lower: the project's object permissions or the user's
project permissions. Same is true for a group.

This module provides a procedural interface to the underlying database model,
with the immutable Project class accessible to the developer instead of an
SQLAlchemy ORM class.

As the project models use flask-sqlalchemy however, the functions in this
module should be called from within a Flask application context.
"""

from sqlalchemy.exc import IntegrityError
import collections
import typing
from .. import db
from ..models import projects, User, Permissions, UserProjectPermissions, GroupProjectPermissions
from .users import get_user
from . import groups
from . import utils
from . import errors


# project names are limited to this (semi-arbitrary) length
MAX_PROJECT_NAME_LENGTH = 100


class Project(collections.namedtuple('Project', ['id', 'name', 'description'])):
    """
    This class provides an immutable wrapper around models.projects.Project.
    """

    def __new__(cls, id: int, name: str, description: str):
        self = super(Project, cls).__new__(cls, id, name, description)
        return self

    @classmethod
    def from_database(cls, project: projects.Project) -> 'Project':
        return Project(id=project.id, name=project.name, description=project.description)


def create_project(name: str, description: str, initial_user_id: int) -> Project:
    """
    Creates a new project with the given name and description and adds an
    initial user to it.

    :param name: the unique name of the project
    :param description: a (possibly empty) description for the project
    :param initial_user_id: the user ID of the initial project member
    :return: the newly created project
    :raise errors.InvalidProjectNameError: when the project name is empty or more
        than MAX_PROJECT_NAME_LENGTH characters long
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    :raise errors.ProjectAlreadyExistsError: when another project with the given
        name already exists
    """
    if not 1 <= len(name) <= MAX_PROJECT_NAME_LENGTH:
        raise errors.InvalidProjectNameError()
    user = get_user(initial_user_id)
    project = projects.Project(name=name, description=description)
    db.session.add(project)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing_project = projects.Project.query.filter_by(name=name).first()
        if existing_project is not None:
            raise errors.ProjectAlreadyExistsError()
        raise
    user_project_permissions = projects.UserProjectPermissions(project_id=project.id, user_id=user.id, permissions=Permissions.GRANT)
    db.session.add(user_project_permissions)
    db.session.commit()
    return Project.from_database(project)


def update_project(project_id: int, name: str, description: str='') -> None:
    """
    Updates the project's name and description.

    :param project_id: the ID of an existing project
    :param name: the new unique project name
    :param description: the new project description
    :raise errors.InvalidProjectNameError: when the project name is empty or more
        than MAX_PROJECT_NAME_LENGTH characters long
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    :raise errors.ProjectAlreadyExistsError: when another project with the given
        name already exists
    """
    if not 1 <= len(name) <= MAX_PROJECT_NAME_LENGTH:
        raise errors.InvalidProjectNameError()
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    project.name = name
    project.description = description
    db.session.add(project)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing_project = projects.Project.query.filter_by(name=name).first()
        if existing_project is not None:
            raise errors.ProjectAlreadyExistsError()
        raise


def delete_project(project_id: int) -> None:
    """
    Deletes the given project, freeing up the name and removing all permissions
    that might have been granted to the project.

    This is also implicitly done when the last member leaves a project.

    :param project_id: the ID of an existing project
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    """
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    # project object permissions and project default permissions will be
    # deleted due to ondelete = "CASCADE" in the model. No need to delete
    # them manually here.
    db.session.delete(project)
    db.session.commit()


def get_project(project_id: int) -> Project:
    """
    Returns the project with the given ID.

    :param project_id: the ID of an existing project
    :return: the project
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    """
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    return Project.from_database(project)


def get_projects() -> typing.List[Project]:
    """
    Returns a list of all existing projects.

    :return: the list of projects
    """
    return [Project.from_database(project) for project in projects.Project.query.all()]


def get_project_member_user_ids_and_permissions(project_id: int, include_groups: bool=False) -> typing.Dict[int, Permissions]:
    """
    Returns a dict of the user IDs of all members of the project with the
    given project ID, mapping them to their respective permissions.

    :param project_id: the ID of an existing project
    :param include_groups: whether or not groups membership should be
        considered as well
    :return: the member ID to member permission dict
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    """
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    user_permissions = projects.UserProjectPermissions.query.filter_by(project_id=project_id).all()
    member_user_ids_and_permissions =  {
        single_user_permissions.user_id: single_user_permissions.permissions
        for single_user_permissions in user_permissions
    }
    if include_groups:
        member_group_ids_and_permissions = get_project_member_group_ids_and_permissions(project_id)
        for member_group_id, permissions in member_group_ids_and_permissions.items():
            group_member_ids = groups.get_group_member_ids(member_group_id)
            for user_id in group_member_ids:
                if user_id not in member_user_ids_and_permissions or permissions not in member_user_ids_and_permissions[user_id]:
                    member_user_ids_and_permissions[user_id] = permissions
    return member_user_ids_and_permissions


def get_user_project_permissions(project_id: int, user_id: int, include_groups: bool=False) -> Permissions:
    """
    Returns a the permissions of a single user for a project, optionally
    including the users group memberships.

    :param project_id: the ID of an existing project
    :param user_id: the ID of an existing user
    :param include_groups: whether or not groups membership should be
        considered as well
    :return: permissions of this user
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    user_permissions = projects.UserProjectPermissions.query.filter_by(project_id=project_id, user_id=user_id).first()
    if user_permissions:
        permissions = user_permissions.permissions
    else:
        # verify that project exists or raise error
        get_project(project_id)
        permissions = Permissions.NONE
    if include_groups:
        group_permissions = projects.GroupProjectPermissions.query.filter_by(project_id=project_id).all()
        for group_permission in group_permissions:
            if user_id in groups.get_group_member_ids(group_permission.group_id) and permissions in group_permission.permissions:
                permissions = group_permission.permissions
    return permissions


def get_project_member_group_ids_and_permissions(project_id: int) -> typing.Dict[int, Permissions]:
    """
    Returns a dict of the group IDs of all members of the project with the
    given project ID, mapping them to their respective permissions.

    :param project_id: the ID of an existing project
    :return: the member ID to member permission dict
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    """
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    group_permissions = projects.GroupProjectPermissions.query.filter_by(project_id=project_id).all()
    return {
        single_group_permissions.group_id: single_group_permissions.permissions
        for single_group_permissions in group_permissions
    }


def get_user_projects(user_id: int, include_groups: bool=False) -> typing.List[Project]:
    """
    Returns a list of the project IDs of all projects the user with the given
    user ID is a member of.

    :param project_id: the ID of an existing project
    :param include_groups: whether or not groups membership should be
        considered as well
    :return: the member ID list
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    user = get_user(user_id)
    user_permissions = projects.UserProjectPermissions.query.filter_by(user_id=user.id).all()
    project_ids = {
        user_permission.project_id for user_permission in user_permissions
    }
    if include_groups:
        user_groups = groups.get_user_groups(user_id)
        for group in user_groups:
            group_permissions = projects.GroupProjectPermissions.query.filter_by(group_id=group.id).all()
            for group_permission in group_permissions:
                project_ids.add(group_permission.project_id)
    return [get_project(project_id) for project_id in project_ids]


def invite_user_to_project(project_id: int, user_id: int) -> None:
    """
    Sends an invitation mail for a project to a user.

    :param project_id: the ID of an existing project
    :param user_id:  the ID of an existing users
    """
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    get_user(user_id)
    if Permissions.READ in get_user_project_permissions(project_id, user_id):
        raise errors.UserAlreadyMemberOfProjectError()
    utils.send_confirm_email_to_invite_user_to_project(project_id, user_id)


def add_user_to_project(project_id: int, user_id: int, permissions: Permissions) -> None:
    """
    Adds the user with the given user ID to the project with the given project ID.

    :param project_id: the ID of an existing project
    :param user_id: the ID of an existing user
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    :raise errors.UserAlreadyMemberOfProjectError: when the user is already
        a member of the project
    """
    if permissions == permissions.NONE:
        # project members with no permissions are not stored
        return
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    user = get_user(user_id)
    existing_permissions = projects.UserProjectPermissions.query.filter_by(
        project_id=project_id,
        user_id=user.id
    ).first()
    if existing_permissions is not None:
        raise errors.UserAlreadyMemberOfProjectError()
    user_permissions = UserProjectPermissions(project_id=project_id, user_id=user_id, permissions=permissions)
    db.session.add(user_permissions)
    db.session.commit()


def add_group_to_project(project_id: int, group_id: int, permissions: Permissions) -> None:
    """
    Adds the group with the given group ID to the project with the given project ID.

    :param project_id: the ID of an existing project
    :param group_id: the ID of an existing group
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    :raise errors.GroupAlreadyMemberOfProjectError: when the group is already
        a member of the project
    """
    if permissions == permissions.NONE:
        # project members with no permissions are not stored
        return
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    group = groups.get_group(group_id)
    existing_permissions = projects.GroupProjectPermissions.query.filter_by(
        project_id=project_id,
        group_id=group.id
    ).first()
    if existing_permissions is not None:
        raise errors.GroupAlreadyMemberOfProjectError()
    group_permissions = GroupProjectPermissions(project_id=project_id, group_id=group_id, permissions=permissions)
    db.session.add(group_permissions)
    db.session.commit()


def remove_user_from_project(project_id: int, user_id: int) -> None:
    """
    Removes the user with the given user ID from the project with the given
    project ID.

    If there are no member users or groups left in the project, it is deleted
    and its name is freed up to be used again for a new project.

    :param project_id: the ID of an existing project
    :param user_id: the ID of an existing user
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    :raise errors.UserNotMemberOfProjectError: when the user is not a member of
        the project
    :raise errors.NoMemberWithGrantPermissionsForProjectError: when there would
        be no user or group with grant permissions left
    """
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    user = get_user(user_id)
    existing_permissions = projects.UserProjectPermissions.query.filter_by(
        project_id=project_id,
        user_id=user.id
    ).first()
    if existing_permissions is None:
        raise errors.UserNotMemberOfProjectError()
    other_group_permissions = projects.GroupProjectPermissions.query.filter_by(project_id=project_id).all()
    other_user_permissions = projects.UserProjectPermissions.query.filter_by(project_id=project_id).filter(UserProjectPermissions.user_id != user_id).all()
    if existing_permissions.permissions == Permissions.GRANT and (other_user_permissions or other_group_permissions):
        any_other_user_with_grant = any(user_permissions.permissions == Permissions.GRANT for user_permissions in other_user_permissions)
        if not any_other_user_with_grant:
            raise errors.NoMemberWithGrantPermissionsForProjectError()
    if not other_user_permissions and not other_group_permissions:
        db.session.delete(project)
    else:
        db.session.delete(existing_permissions)
    db.session.commit()


def remove_group_from_project(project_id: int, group_id: int) -> None:
    """
    Removes the group with the given group ID from the project with the given
    project ID.

    :param project_id: the ID of an existing project
    :param group_id: the ID of an existing group
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    :raise errors.GroupNotMemberOfProjectError: when the group is not a member of
        the project
    """
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    group = groups.get_group(group_id)
    existing_permissions = projects.GroupProjectPermissions.query.filter_by(
        project_id=project_id,
        group_id=group.id
    ).first()
    if existing_permissions is None:
        raise errors.GroupNotMemberOfProjectError()
    db.session.delete(existing_permissions)
    db.session.commit()


def update_user_project_permissions(project_id: int, user_id: int, permissions: Permissions) -> None:
    """
    Updates the permissions of the user with the given user ID for the project
    with the given project ID.

    Removes the user from the project if permissions is NONE.

    :param project_id: the ID of an existing project
    :param user_id: the ID of an existing user
    :param permissions: the new permissions
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    :raise errors.UserNotMemberOfProjectError: when the user is not a member of
        the project
    :raise errors.NoMemberWithGrantPermissionsForProjectError: when there would
        be no user or group with grant permissions left
    """

    if permissions == Permissions.NONE:
        remove_user_from_project(project_id=project_id, user_id=user_id)
        return
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    user = get_user(user_id)
    existing_permissions = projects.UserProjectPermissions.query.filter_by(
        project_id=project_id,
        user_id=user_id
    ).first()
    if existing_permissions is None:
        raise errors.UserNotMemberOfProjectError()
    if existing_permissions.permissions == permissions:
        return

    if existing_permissions.permissions == Permissions.GRANT:
        other_user_permissions = projects.UserProjectPermissions.query.filter_by(project_id=project_id).filter(UserProjectPermissions.user_id != user_id).all()
        any_other_user_with_grant = any(user_permissions.permissions == Permissions.GRANT for user_permissions in other_user_permissions)
        if not any_other_user_with_grant:
            raise errors.NoMemberWithGrantPermissionsForProjectError()

    existing_permissions.permissions = permissions
    db.session.add(existing_permissions)
    db.session.commit()


def update_group_project_permissions(project_id: int, group_id: int, permissions: Permissions) -> None:
    """
    Updates the permissions of the group with the given group ID for the project
    with the given project ID.

    Removes the group from the project if permissions is NONE.

    :param project_id: the ID of an existing project
    :param group_id: the ID of an existing group
    :param permissions: the new permissions
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    :raise errors.GroupNotMemberOfProjectError: when the group is not a member of
        the project
    """

    if permissions == Permissions.NONE:
        remove_group_from_project(project_id=project_id, group_id=group_id)
        return
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    group = groups.get_group(group_id)
    existing_permissions = projects.GroupProjectPermissions.query.filter_by(
        project_id=project_id,
        group_id=group_id
    ).first()
    if existing_permissions is None:
        raise errors.GroupNotMemberOfProjectError()

    existing_permissions.permissions = permissions
    db.session.add(existing_permissions)
    db.session.commit()


def get_group_projects(group_id: int) -> typing.List[Project]:
    """
    Returns a list of the project IDs of all projects the group with the given
    group ID is a member of.

    :param project_id: the ID of an existing project
    :return: the member ID list
    :raise errors.GroupDoesNotExistError: when no group with the given
        group ID exists
    """
    group = groups.get_group(group_id)
    group_permissions = projects.GroupProjectPermissions.query.filter_by(group_id=group.id).all()
    project_ids = {
        group_permission.project_id for group_permission in group_permissions
    }
    return [get_project(project_id) for project_id in project_ids]

