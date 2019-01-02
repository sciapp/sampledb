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
import datetime
import typing
import flask

from .. import db
from ..models import projects, User, Permissions, UserProjectPermissions, GroupProjectPermissions, SubprojectRelationship
from .users import get_user
from .security_tokens import generate_token, MAX_AGE
from . import groups
from . import utils
from . import errors
from . import notifications


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


def invite_user_to_project(project_id: int, user_id: int, inviter_id: int, add_to_parent_project_ids: typing.Sequence[int]=()) -> None:
    """
    Sends an invitation mail for a project to a user.

    :param project_id: the ID of an existing project
    :param user_id:  the ID of an existing users
    :param inviter_id: the ID of who invited this user to the project
    :param add_to_parent_project_ids: list of IDs of parent projects to which
        the user should also be added
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        or inviter ID exists
    :raise errors.UserAlreadyMemberOfProjectError: when the user with the given
        user ID already is a member of this project
    """
    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()
    get_user(user_id)
    if Permissions.READ in get_user_project_permissions(project_id, user_id):
        raise errors.UserAlreadyMemberOfProjectError()

    token = generate_token(
        {
            'user_id': user_id,
            'project_id': project_id,
            'other_project_ids': add_to_parent_project_ids
        },
        salt='invite_to_project',
        secret_key=flask.current_app.config['SECRET_KEY']
    )
    expiration_utc_datetime = datetime.datetime.utcnow() + datetime.timedelta(seconds=MAX_AGE)
    confirmation_url = flask.url_for("frontend.project", project_id=project_id, token=token, _external=True)
    notifications.create_notification_for_being_invited_to_a_project(user_id, project_id, inviter_id, confirmation_url, expiration_utc_datetime)


def add_user_to_project(project_id: int, user_id: int, permissions: Permissions, other_project_ids: typing.Sequence[int]=()) -> None:
    """
    Adds the user with the given user ID to the project with the given project ID.

    :param project_id: the ID of an existing project
    :param user_id: the ID of an existing user
    :param permissions: the permissions of the user for this project
    :param other_project_ids: IDs of (parent) projects this user should also
        be added to
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
    if other_project_ids:
        ancestor_project_ids = get_ancestor_project_ids(project_id, only_if_child_can_add_users_to_ancestor=True)
        for other_project_id in other_project_ids:
            if other_project_id in ancestor_project_ids:
                try:
                    add_user_to_project(other_project_id, user_id, permissions)
                except errors.UserAlreadyMemberOfProjectError:
                    pass


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


def filter_child_project_candidates(parent_project_id: int, child_project_ids: typing.List[int]) -> typing.List[int]:
    """
    Filters a list of project IDs to find which of them may become child
    projects of another given project.

    :param parent_project_id: the ID of an existing project
    :param child_project_ids: a list of IDs of existing projects
    :return: child_project_ids without IDs of projects which may not become
        child projects of parent_project_id
    """
    # Prevent relationship of a project with itself
    for child_project_id in child_project_ids[:]:
        if child_project_id == parent_project_id:
            child_project_ids.remove(child_project_id)
    # Prevent relationship duplication
    for child_project_id in child_project_ids[:]:
        if SubprojectRelationship.query.filter_by(parent_project_id=parent_project_id, child_project_id=child_project_id).first():
            child_project_ids.remove(child_project_id)
    # Prevent cycles
    if child_project_ids:
        ancestor_project_ids = get_ancestor_project_ids(parent_project_id)
        for child_project_id in child_project_ids[:]:
            if child_project_id in ancestor_project_ids:
                child_project_ids.remove(child_project_id)
                continue
    return child_project_ids


def create_subproject_relationship(parent_project_id: int, child_project_id: int, child_can_add_users_to_parent: bool=False) -> None:
    """
    Creates a subproject relationship between two existing projects.

    :param parent_project_id: the ID of an existing project
    :param child_project_id: the ID of an existing project
    :param child_can_add_users_to_parent: whether or not to allow users with
        GRANT permission on the child project to add users to the parent
    :raise errors.InvalidSubprojectRelationshipError: if the relationship
        would cause a cyclic relationship or exceed the maximum subproject
        depth
    """
    if not filter_child_project_candidates(parent_project_id, [child_project_id]):
            raise errors.InvalidSubprojectRelationshipError()
    subproject_relationship = SubprojectRelationship(parent_project_id=parent_project_id, child_project_id=child_project_id, child_can_add_users_to_parent=child_can_add_users_to_parent)
    db.session.add(subproject_relationship)
    db.session.commit()


def delete_subproject_relationship(parent_project_id: int, child_project_id: int) -> None:
    """
    Deletes an existing subproject relationship between two existing projects.

    :param parent_project_id: the ID of an existing project
    :param child_project_id: the ID of an existing project
    :raise errors.SubprojectRelationshipDoesNotExistError: if the relationship
        does not exist
    """
    subproject_relationship = SubprojectRelationship.query.filter_by(
        parent_project_id=parent_project_id,
        child_project_id=child_project_id
    ).first()
    if subproject_relationship is None:
        raise errors.SubprojectRelationshipDoesNotExistError()
    db.session.delete(subproject_relationship)
    db.session.commit()


def get_parent_project_ids(project_id: int, only_if_child_can_add_users_to_parent: bool=False) -> typing.List[int]:
    """
    Return the list of parent project IDs for an existing project.

    :param project_id: the ID of an existing project
    :param only_if_child_can_add_users_to_parent: whether or not to only show
        those parent projects, which someone with GRANT permissions on this
        project can add users to (transitively)
    :return: list of project IDs
    """
    subproject_relationships: typing.Iterable[SubprojectRelationship] = SubprojectRelationship.query.filter_by(
        child_project_id=project_id
    ).all()
    parent_project_ids = []
    for subproject_relationship in subproject_relationships:
        if subproject_relationship.child_can_add_users_to_parent or not only_if_child_can_add_users_to_parent:
            parent_project_ids.append(subproject_relationship.parent_project_id)
    return parent_project_ids


def get_child_project_ids(project_id: int) -> typing.List[int]:
    """
    Return the list of child project IDs for an existing project.

    :param project_id: the ID of an existing project
    :return: list of project IDs
    """
    subproject_relationships = SubprojectRelationship.query.filter_by(
        parent_project_id=project_id
    ).all()
    child_project_ids = []
    for subproject_relationship in subproject_relationships:
        child_project_ids.append(subproject_relationship.child_project_id)
    return child_project_ids


def get_ancestor_project_ids(project_id: int, only_if_child_can_add_users_to_ancestor: bool=False) -> typing.Set[int]:
    """
    Return the list of (transitive) ancestor project IDs for an existing
    project.

    :param project_id: the ID of an existing project
    :param only_if_child_can_add_users_to_ancestor: whether or not to only show
        those ancestor projects, which someone with GRANT permissions on this
        project can add users to (transitively)
    :return: set of project IDs
    """
    ancestor_project_ids = set()
    project_id_queue = [project_id]
    while project_id_queue:
        ancestor_project_id = project_id_queue.pop(0)
        if ancestor_project_id in ancestor_project_ids:
            continue
        if ancestor_project_id != project_id:
            ancestor_project_ids.add(ancestor_project_id)
        project_id_queue.extend(get_parent_project_ids(ancestor_project_id, only_if_child_can_add_users_to_parent=only_if_child_can_add_users_to_ancestor))
    return ancestor_project_ids


def get_descendent_project_ids(project_id: int) -> typing.Set[int]:
    """
    Return the list of (transitive) descendent project IDs for an existing
    project.

    :param project_id: the ID of an existing project
    :return: set of project IDs
    """
    descendent_project_ids = set()
    project_id_queue = [project_id]
    while project_id_queue:
        descendent_project_id = project_id_queue.pop(0)
        if descendent_project_id in descendent_project_ids:
            continue
        if descendent_project_id != project_id:
            descendent_project_ids.add(descendent_project_id)
        project_id_queue.extend(get_child_project_ids(descendent_project_id))
    return descendent_project_ids


def can_child_add_users_to_parent_project(child_project_id: int, parent_project_id: int) -> bool:
    """
    Return whether or not the subproject relationship allows adding users to
    the parent project.

    :param child_project_id: the ID of an existing child project
    :param parent_project_id: the ID of an existing parent project
    :return: whether or not someone with GRANT permissions on the child
        project can add users to the parent project
    """
    subproject_relationship: typing.Optional[SubprojectRelationship] = SubprojectRelationship.query.filter_by(
        child_project_id=child_project_id,
        parent_project_id=parent_project_id
    ).first()
    if subproject_relationship is None:
        return False
    return subproject_relationship.child_can_add_users_to_parent
