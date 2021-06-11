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

import collections
import datetime
import typing
import flask
from .. import db
from ..models import projects, Permissions, UserProjectPermissions, GroupProjectPermissions, SubprojectRelationship
from .users import get_user
from .security_tokens import generate_token
from . import groups
from . import errors
from . import objects
from . import object_log
from .notifications import create_notification_for_being_invited_to_a_project
from .languages import get_language_by_lang_code, Language


# project names are limited to this (semi-arbitrary) length
MAX_PROJECT_NAME_LENGTH = 100


class Project(collections.namedtuple('Project', ['id', 'name', 'description'])):
    """
    This class provides an immutable wrapper around models.projects.Project.
    """

    def __new__(cls, id: int, name: dict, description: dict):
        self = super(Project, cls).__new__(cls, id, name, description)
        return self

    @classmethod
    def from_database(cls, project: projects.Project) -> 'Project':
        return Project(id=project.id, name=project.name, description=project.description)


class ProjectInvitation(collections.namedtuple('ProjectInvitation', ['id', 'project_id', 'user_id', 'inviter_id', 'utc_datetime', 'accepted'])):
    """
    This class provides an immutable wrapper around models.projects.ProjectInvitation.
    """

    def __new__(cls, id: int, project_id: int, user_id: int, inviter_id: int, utc_datetime: datetime.datetime, accepted: bool):
        self = super(ProjectInvitation, cls).__new__(cls, id, project_id, user_id, inviter_id, utc_datetime, accepted)
        return self

    @classmethod
    def from_database(cls, project_invitation: projects.ProjectInvitation) -> 'ProjectInvitation':
        return ProjectInvitation(
            id=project_invitation.id,
            project_id=project_invitation.project_id,
            user_id=project_invitation.user_id,
            inviter_id=project_invitation.inviter_id,
            utc_datetime=project_invitation.utc_datetime,
            accepted=project_invitation.accepted
        )

    @property
    def expired(self):
        expiration_datetime = self.utc_datetime + datetime.timedelta(seconds=flask.current_app.config['INVITATION_TIME_LIMIT'])
        return datetime.datetime.utcnow() >= expiration_datetime


def create_project(name: typing.Union[str, dict], description: typing.Union[str, dict], initial_user_id: int) -> Project:
    """
    Creates a new project with the given name and description and adds an
    initial user to it.

    :param name: the unique names of the project in a dict. Keys are lang codes and values names.
    :param description: (possibly empty) descriptions for the project in a dict.
        Keys are lang codes and values are descriptions
    :param initial_user_id: the user ID of the initial project member
    :return: the newly created project
    :raise errors.InvalidProjectNameError: when the project name is empty or more
        than MAX_PROJECT_NAME_LENGTH characters long
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    :raise errors.ProjectAlreadyExistsError: when another project with the given
        name already exists
    :raise errors.LanguageDoesNotExistError: when there is no language for the given lang codes
    """
    if isinstance(name, str):
        name = {
            'en': name
        }
    if isinstance(description, str):
        description = {
            'en': description
        }
    try:
        for language_code, name_text in list(name.items()):
            language = get_language_by_lang_code(language_code)
            if not 1 <= len(name_text) <= MAX_PROJECT_NAME_LENGTH:
                if language.id == Language.ENGLISH:
                    raise errors.InvalidProjectNameError()
                else:
                    del name[language_code]
            existing_project = projects.Project.query.filter(
                projects.Project.name[language_code].astext.cast(db.Unicode) == name_text
            ).first()
            if existing_project is not None:
                raise errors.ProjectAlreadyExistsError()
    except errors.LanguageDoesNotExistError:
        raise errors.LanguageDoesNotExistError("There is no language for the given lang code")
    except errors.InvalidProjectNameError:
        raise errors.InvalidProjectNameError()
    except errors.ProjectAlreadyExistsError:
        raise errors.ProjectAlreadyExistsError()
    if 'en' not in name:
        raise errors.MissingEnglishTranslationError()
    if not name['en']:
        raise errors.InvalidProjectNameError()

    for item in list(description.items()):
        if item[1] == '':
            del description[item[0]]

    user = get_user(initial_user_id)
    project = projects.Project(name=name, description=description)
    db.session.add(project)

    db.session.commit()
    user_project_permissions = projects.UserProjectPermissions(project_id=project.id, user_id=user.id, permissions=Permissions.GRANT)
    db.session.add(user_project_permissions)
    db.session.commit()
    return Project.from_database(project)


def update_project(project_id: int, name: dict, description: dict) -> None:
    """
    Updates the project's name and description.

    :param project_id: the ID of an existing project
    :param name: the new unique project names in a dict. Keys are lang codes and values are names.
    :param description: the new project descriptions in a dict. Keys are lang codes and values are descriptions.
    :raise errors.InvalidProjectNameError: when the project name is empty or more
        than MAX_PROJECT_NAME_LENGTH characters long
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    :raise errors.ProjectAlreadyExistsError: when another project with the given
        name already exists
    :raise errors.LanguageDoesNotExistError: when there is no language for the given lang codes.
    """
    try:
        for language_code, name_text in list(name.items()):
            language = get_language_by_lang_code(language_code)
            if not 1 <= len(name_text) <= MAX_PROJECT_NAME_LENGTH:
                if language.id != Language.ENGLISH and not name_text:
                    del name[language_code]
                else:
                    raise errors.InvalidProjectNameError()
            existing_project = projects.Project.query.filter(
                projects.Project.name[language_code].astext.cast(db.Unicode) == name_text
            ).first()
            if existing_project is not None and existing_project.id != project_id:
                raise errors.ProjectAlreadyExistsError()

    except errors.LanguageDoesNotExistError:
        raise errors.LanguageDoesNotExistError("There is no language for the given lang code")
    except errors.InvalidProjectNameError:
        raise errors.InvalidProjectNameError()
    except errors.ProjectAlreadyExistsError:
        raise errors.ProjectAlreadyExistsError()
    except Exception as e:
        raise e
    if 'en' not in name:
        raise errors.MissingEnglishTranslationError()

    project = projects.Project.query.get(project_id)
    if project is None:
        raise errors.ProjectDoesNotExistError()

    for item in list(description.items()):
        if item[1] == '':
            del description[item[0]]

    project.name = name
    project.description = description
    db.session.add(project)
    db.session.commit()


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


def get_project_member_user_ids_and_permissions(project_id: int, include_groups: bool = False) -> typing.Dict[int, Permissions]:
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
    member_user_ids_and_permissions = {
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


def get_user_project_permissions(project_id: int, user_id: int, include_groups: bool = False) -> Permissions:
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


def get_user_projects(
        user_id: int,
        include_groups: bool = False,
        min_permissions: Permissions = Permissions.NONE
) -> typing.List[Project]:
    """
    Returns a list of the project IDs of all projects the user with the given
    user ID is a member of.

    :param project_id: the ID of an existing project
    :param include_groups: whether or not groups membership should be
        considered as well
    :param min_permissions: only return projects for which the user has at
        least this permission level
    :return: the member ID list
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    user = get_user(user_id)
    user_permissions = projects.UserProjectPermissions.query.filter_by(user_id=user.id).all()
    project_ids = {
        user_permission.project_id for user_permission in user_permissions
        if min_permissions in user_permission.permissions
    }
    if include_groups:
        user_groups = groups.get_user_groups(user_id)
        for group in user_groups:
            group_permissions = projects.GroupProjectPermissions.query.filter_by(group_id=group.id).all()
            for group_permission in group_permissions:
                if min_permissions in group_permission.permissions:
                    project_ids.add(group_permission.project_id)
    return [get_project(project_id) for project_id in project_ids]


def invite_user_to_project(
        project_id: int,
        user_id: int,
        inviter_id: int,
        add_to_parent_project_ids: typing.Sequence[int] = (),
        permissions: Permissions = Permissions.READ
) -> None:
    """
    Sends an invitation mail for a project to a user.

    :param project_id: the ID of an existing project
    :param user_id:  the ID of an existing users
    :param inviter_id: the ID of who invited this user to the project
    :param add_to_parent_project_ids: list of IDs of parent projects to which
        the user should also be added
    :param permissions: the permissions that the user should get
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
    invitation = projects.ProjectInvitation(
        project_id=project_id,
        user_id=user_id,
        inviter_id=inviter_id,
        utc_datetime=datetime.datetime.utcnow()
    )
    db.session.add(invitation)
    db.session.commit()
    token = generate_token(
        {
            'invitation_id': invitation.id,
            'user_id': user_id,
            'project_id': project_id,
            'permissions': permissions.value,
            'other_project_ids': add_to_parent_project_ids
        },
        salt='invite_to_project',
        secret_key=flask.current_app.config['SECRET_KEY']
    )
    expiration_time_limit = flask.current_app.config['INVITATION_TIME_LIMIT']
    expiration_utc_datetime = datetime.datetime.utcnow() + datetime.timedelta(seconds=expiration_time_limit)
    confirmation_url = flask.url_for("frontend.project", project_id=project_id, token=token, _external=True)
    create_notification_for_being_invited_to_a_project(user_id, project_id, inviter_id, confirmation_url, expiration_utc_datetime)


def add_user_to_project(project_id: int, user_id: int, permissions: Permissions, other_project_ids: typing.Sequence[int] = ()) -> None:
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
    invitations = get_project_invitations(
        project_id=project_id,
        user_id=user_id,
        include_expired_invitations=False,
        include_accepted_invitations=False
    )
    for invitation in invitations:
        invitation = projects.ProjectInvitation.query.filter_by(id=invitation.id).first()
        invitation.accepted = True
        db.session.add(invitation)
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
    :param permissions: the permissions for the group
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
    get_user(user_id)
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
    groups.get_group(group_id)
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


def create_subproject_relationship(parent_project_id: int, child_project_id: int, child_can_add_users_to_parent: bool = False) -> None:
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


def get_parent_project_ids(project_id: int, only_if_child_can_add_users_to_parent: bool = False) -> typing.List[int]:
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


def get_ancestor_project_ids(project_id: int, only_if_child_can_add_users_to_ancestor: bool = False) -> typing.Set[int]:
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


def get_project_invitations(
        project_id: int,
        user_id: typing.Optional[int] = None,
        include_accepted_invitations: bool = True,
        include_expired_invitations: bool = True
) -> typing.List[ProjectInvitation]:
    """
    Get all (current) invitations for a user to join a project.

    :param project_id: the ID of an existing project
    :param user_id: the ID of an existing user or None
    :param include_accepted_invitations: whether or not to include invitations
        that have already been accepted by the user
    :param include_expired_invitations: whether or not to include invitations
        that have already expired
    :return: the list of project invitations
    :raise errors.ProjectDoesNotExistError: when no project with the given
        project ID exists
    """
    project_invitations_query = projects.ProjectInvitation.query.filter_by(project_id=project_id)
    if user_id is not None:
        project_invitations_query = project_invitations_query.filter_by(user_id=user_id)
    if not include_accepted_invitations:
        project_invitations_query = project_invitations_query.filter_by(accepted=False)
    if not include_expired_invitations:
        expiration_time_limit = flask.current_app.config['INVITATION_TIME_LIMIT']
        expired_invitation_datetime = datetime.datetime.utcnow() - datetime.timedelta(seconds=expiration_time_limit)
        project_invitations_query.filter(projects.ProjectInvitation.utc_datetime > expired_invitation_datetime)
    project_invitations = project_invitations_query.order_by(projects.ProjectInvitation.utc_datetime).all()
    if not project_invitations:
        # ensure that a project with this ID exists
        get_project(project_id)
    return [
        ProjectInvitation.from_database(project_invitation)
        for project_invitation in project_invitations
    ]


def get_project_invitation(invitation_id: int) -> ProjectInvitation:
    """
    Get an existing invitation.

    :param invitation_id: the ID of an existing invitation
    :return: the invitation
    :raise errors.ProjectInvitationDoesNotExistError: when no invitation with
        the given ID exists
    """
    invitation = projects.ProjectInvitation.query.filter_by(id=invitation_id).first()
    if invitation is None:
        raise errors.ProjectInvitationDoesNotExistError()
    return ProjectInvitation.from_database(invitation)


def get_project_id_hierarchy_list(project_ids: typing.List[int]) -> typing.List[typing.Tuple[int, int]]:
    """
    Return a list of project IDs and the degree that they are related to a root project.

    This list is sorted so that child projects follow their parents. If a
    project is the child of multiple parent projects, it and its descendents
    will be included repeatedly.

    :param project_ids: the project IDs to include
    :return: a list of tuples containing the project level and ID
    """
    child_project_ids = {
        project_id: [
            child_project_id
            for child_project_id in get_child_project_ids(project_id)
            if child_project_id in project_ids
        ]
        for project_id in project_ids
    }

    root_project_ids = [
        project_id
        for project_id in project_ids
        if not any(
            project_id in ids
            for ids in child_project_ids.values()
        )
    ]

    project_id_hierarchy_list = []
    parent_project_queue = [
        (0, project_id)
        for project_id in sorted(root_project_ids, reverse=True)
    ]
    while parent_project_queue:
        level, parent_project_id = parent_project_queue.pop()
        project_id_hierarchy_list.append((level, parent_project_id))
        parent_project_queue.extend([
            (level + 1, project_id)
            for project_id in reversed(child_project_ids[parent_project_id])
        ])
        if not parent_project_queue:
            # In case of cyclical relationships, which should be
            # impossible, projects may not be included yet, so
            # if there are any left, this picks the one with the lowest ID.
            remaining_project_ids = set(project_ids) - {
                project_id
                for level, project_id in project_id_hierarchy_list
            }
            if remaining_project_ids:
                parent_project_queue.append((0, sorted(remaining_project_ids)[0]))

    return project_id_hierarchy_list


def link_project_and_object(
        project_id: int,
        object_id: int,
        user_id: int
) -> None:
    """
    Link a project and an object.

    This link is exclusive, as any project can be linked to at most one object
    and vice versa.

    If the project is deleted, this link will be removed automatically.

    :param project_id: the ID of an existing project
    :param object_id: the ID of an existing object
    :param user_id: the ID of the user creating this link
    :raise errors.ProjectDoesNotExistError: if no project with the given ID
        exists
    :raise errors.ObjectDoesNotExistError: if no object with the given ID
        exists
    :raise errors.UserDoesNotExistError: if no user with the given ID exists
    :raise errors.ProjectObjectLinkAlreadyExistsError: if another link exists
        for either the project or the object
    """
    # make sure the object exists
    objects.get_object(object_id)
    # make sure the project exists
    get_project(project_id)
    # make sure the user exists
    get_user(user_id)
    if projects.ProjectObjectAssociation.query.filter(
            db.or_(
                projects.ProjectObjectAssociation.project_id == project_id,
                projects.ProjectObjectAssociation.object_id == object_id
            )
    ).first() is not None:
        raise errors.ProjectObjectLinkAlreadyExistsError()

    db.session.add(projects.ProjectObjectAssociation(project_id=project_id, object_id=object_id))
    db.session.commit()

    object_log.link_project(user_id=user_id, object_id=object_id, project_id=project_id)


def unlink_project_and_object(
        project_id: int,
        object_id: int,
        user_id: int
) -> None:
    """
    Remove a link between a project and an object.

    :param project_id: the ID of an existing project
    :param object_id: the ID of an existing object
    :param user_id: the ID of the user removing this link
    :raise errors.ProjectDoesNotExistError: if no project with the given ID
        exists
    :raise errors.ObjectDoesNotExistError: if no object with the given ID
        exists
    :raise errors.UserDoesNotExistError: if no user with the given ID exists
    :raise errors.ProjectObjectLinkDoesNotExistsError: if no link exists
        between the project and the object
    """
    # make sure the user exists
    get_user(user_id)
    association = projects.ProjectObjectAssociation.query.filter_by(
        project_id=project_id,
        object_id=object_id
    ).first()
    if association is None:
        # make sure the object exists
        objects.get_object(object_id)
        # make sure the project exists
        get_project(project_id)
        raise errors.ProjectObjectLinkDoesNotExistsError()
    db.session.delete(association)
    db.session.commit()

    object_log.unlink_project(user_id=user_id, object_id=object_id, project_id=project_id)


def get_project_linked_to_object(object_id: int) -> typing.Optional[Project]:
    """
    Return the project linked to a given object, or None.

    :param object_id: the ID of an existing object
    :return: the linked project or None
    :raise errors.ObjectDoesNotExistError: if no object with the given ID
        exists
    """
    association = projects.ProjectObjectAssociation.query.filter_by(
        object_id=object_id
    ).first()
    if association is None:
        # make sure the object exists
        objects.get_object(object_id)
        return None

    return get_project(association.project_id)


def get_object_linked_to_project(project_id: int) -> typing.Optional[objects.Object]:
    """
    Return the object linked to a given project, or None.

    :param project_id: the ID of an existing project
    :return: the linked object or None
    :raise errors.ProjectDoesNotExistError: if no project with the given ID
        exists
    """
    association = projects.ProjectObjectAssociation.query.filter_by(
        project_id=project_id
    ).first()
    if association is None:
        # make sure the project exists
        get_project(project_id)
        return None

    return objects.get_object(association.object_id)


def get_project_object_links() -> typing.List[typing.Tuple[int, int]]:
    """
    Return a list of all links between a project and an object.

    :return: the list of project and object ID tuples
    """
    return [
        (link.project_id, link.object_id)
        for link in projects.ProjectObjectAssociation.query.all()
    ]
