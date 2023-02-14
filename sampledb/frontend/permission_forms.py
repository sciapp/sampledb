import typing

import flask
from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, FieldList, FormField
from wtforms.validators import InputRequired

from ..logic import errors
from ..logic.permissions import ResourcePermissions
from ..models import Permissions


class UserPermissionsForm(FlaskForm):
    user_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class GroupPermissionsForm(FlaskForm):
    group_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ProjectPermissionsForm(FlaskForm):
    project_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class PermissionsForm(FlaskForm):
    all_user_permissions = SelectField(
        choices=[(p.name.lower(), p) for p in (Permissions.NONE, Permissions.READ)],
        validators=[InputRequired()]
    )
    anonymous_user_permissions = SelectField(
        choices=[(p.name.lower(), p) for p in (Permissions.NONE, Permissions.READ)],
        validators=[InputRequired()]
    )
    user_permissions = FieldList(FormField(UserPermissionsForm), min_entries=0)
    group_permissions = FieldList(FormField(GroupPermissionsForm), min_entries=0)
    project_permissions = FieldList(FormField(ProjectPermissionsForm), min_entries=0)


def handle_permission_forms(
        resource_permissions: ResourcePermissions,
        resource_id: int,
        add_user_permissions_form: UserPermissionsForm,
        add_group_permissions_form: GroupPermissionsForm,
        add_project_permissions_form: ProjectPermissionsForm,
        permissions_form: PermissionsForm,
        existing_user_permissions: typing.Optional[typing.Dict[int, Permissions]] = None,
        existing_group_permissions: typing.Optional[typing.Dict[int, Permissions]] = None,
        existing_project_permissions: typing.Optional[typing.Dict[int, Permissions]] = None
) -> bool:
    if 'add_user_permissions' in flask.request.form and add_user_permissions_form.validate_on_submit():
        user_id = add_user_permissions_form.user_id.data
        permissions = Permissions.from_name(add_user_permissions_form.permissions.data)
        if existing_user_permissions is None:
            existing_user_permissions = resource_permissions.get_permissions_for_users(resource_id)
        if permissions != Permissions.NONE and user_id not in existing_user_permissions:
            try:
                resource_permissions.set_permissions_for_user(
                    resource_id=resource_id,
                    user_id=user_id,
                    permissions=permissions
                )
            except errors.UserDoesNotExistError:
                return False
            else:
                return True
    elif 'add_group_permissions' in flask.request.form and add_group_permissions_form.validate_on_submit():
        group_id = add_group_permissions_form.group_id.data
        permissions = Permissions.from_name(add_group_permissions_form.permissions.data)
        if existing_group_permissions is None:
            existing_group_permissions = resource_permissions.get_permissions_for_groups(resource_id)
        if permissions != Permissions.NONE and group_id not in existing_group_permissions:
            try:
                resource_permissions.set_permissions_for_group(
                    resource_id=resource_id,
                    group_id=group_id,
                    permissions=permissions
                )
            except errors.GroupDoesNotExistError:
                return False
            else:
                return True
    elif 'add_project_permissions' in flask.request.form and add_project_permissions_form.validate_on_submit():
        project_id = add_project_permissions_form.project_id.data
        permissions = Permissions.from_name(add_project_permissions_form.permissions.data)
        if existing_project_permissions is None:
            existing_project_permissions = resource_permissions.get_permissions_for_projects(resource_id)
        if permissions != Permissions.NONE and project_id not in existing_project_permissions:
            try:
                resource_permissions.set_permissions_for_project(
                    resource_id=resource_id,
                    project_id=project_id,
                    permissions=permissions
                )
            except errors.ProjectDoesNotExistError:
                return False
            else:
                return True
    elif 'edit_permissions' in flask.request.form and permissions_form.validate_on_submit():
        permissions = Permissions.from_name(permissions_form.all_user_permissions.data)
        resource_permissions.set_permissions_for_all_users(resource_id, permissions)
        permissions = Permissions.from_name(permissions_form.anonymous_user_permissions.data)
        resource_permissions.set_permissions_for_anonymous_users(resource_id, permissions)
        for user_permissions_data in permissions_form.user_permissions.data:
            user_id = user_permissions_data['user_id']
            permissions = Permissions.from_name(user_permissions_data['permissions'])
            try:
                resource_permissions.set_permissions_for_user(
                    resource_id=resource_id,
                    user_id=user_id,
                    permissions=permissions
                )
            except errors.UserDoesNotExistError:
                continue
        for group_permissions_data in permissions_form.group_permissions.data:
            group_id = group_permissions_data['group_id']
            permissions = Permissions.from_name(group_permissions_data['permissions'])
            try:
                resource_permissions.set_permissions_for_group(
                    resource_id=resource_id,
                    group_id=group_id,
                    permissions=permissions
                )
            except errors.GroupDoesNotExistError:
                continue
        for project_permissions_data in permissions_form.project_permissions.data:
            project_id = project_permissions_data['project_id']
            permissions = Permissions.from_name(project_permissions_data['permissions'])
            try:
                resource_permissions.set_permissions_for_project(
                    resource_id=resource_id,
                    project_id=project_id,
                    permissions=permissions
                )
            except errors.ProjectDoesNotExistError:
                continue
        return True
    return False


def set_up_permissions_forms(
        *,
        resource_permissions: ResourcePermissions,
        resource_id: int,
        existing_all_user_permissions: typing.Optional[Permissions] = None,
        existing_anonymous_user_permissions: typing.Optional[Permissions] = None,
        existing_user_permissions: typing.Optional[typing.Dict[int, Permissions]] = None,
        existing_group_permissions: typing.Optional[typing.Dict[int, Permissions]] = None,
        existing_project_permissions: typing.Optional[typing.Dict[int, Permissions]] = None
) -> typing.Tuple[UserPermissionsForm, GroupPermissionsForm, ProjectPermissionsForm, PermissionsForm]:
    if existing_all_user_permissions is None:
        existing_all_user_permissions = resource_permissions.get_permissions_for_all_users(resource_id)
    if existing_anonymous_user_permissions is None:
        existing_anonymous_user_permissions = resource_permissions.get_permissions_for_anonymous_users(resource_id)
    if existing_user_permissions is None:
        existing_user_permissions = resource_permissions.get_permissions_for_users(resource_id)
    if existing_group_permissions is None:
        existing_group_permissions = resource_permissions.get_permissions_for_groups(resource_id)
    if existing_project_permissions is None:
        existing_project_permissions = resource_permissions.get_permissions_for_projects(resource_id)

    all_user_permissions_form_data = existing_all_user_permissions.name.lower()

    anonymous_user_permissions_form_data = existing_anonymous_user_permissions.name.lower()

    user_permission_form_data = []
    for user_id, permissions in sorted(existing_user_permissions.items()):
        if user_id is None:
            continue
        user_permission_form_data.append({'user_id': user_id, 'permissions': permissions.name.lower()})

    group_permission_form_data = []
    for group_id, permissions in sorted(existing_group_permissions.items()):
        if group_id is None:
            continue
        group_permission_form_data.append({'group_id': group_id, 'permissions': permissions.name.lower()})

    project_permission_form_data = []
    for project_id, permissions in sorted(existing_project_permissions.items()):
        if project_id is None:
            continue
        project_permission_form_data.append({'project_id': project_id, 'permissions': permissions.name.lower()})

    permissions_form = PermissionsForm(
        all_user_permissions=all_user_permissions_form_data,
        anonymous_user_permissions=anonymous_user_permissions_form_data,
        user_permissions=user_permission_form_data,
        group_permissions=group_permission_form_data,
        project_permissions=project_permission_form_data
    )
    add_user_permissions_form = UserPermissionsForm()
    add_group_permissions_form = GroupPermissionsForm()
    add_project_permissions_form = ProjectPermissionsForm()
    return (
        add_user_permissions_form,
        add_group_permissions_form,
        add_project_permissions_form,
        permissions_form
    )
