# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from .. import logic
from ..logic.permissions import Permissions
from ..logic.security_tokens import verify_token
from .projects_forms import CreateProjectForm, EditProjectForm, LeaveProjectForm, InviteUserToProjectForm, InviteGroupToProjectForm, ProjectPermissionsForm


@frontend.route('/projects/<int:project_id>', methods=['GET', 'POST'])
@flask_login.login_required
def project(project_id):
    if 'token' in flask.request.args:
        token = flask.request.args.get('token')
        user_id = verify_token(token, salt='invite_to_project', secret_key=flask.current_app.config['SECRET_KEY'])
        if user_id != flask_login.current_user.id:
            if user_id is not None:
                try:
                    invited_user = logic.users.get_user(user_id)
                    flask.flash('Please sign in as user "{}" to accept this invitation.'.format(invited_user.name), 'error')
                except logic.errors.UserDoesNotExistError:
                    pass
            return flask.abort(403)
        logic.projects.add_user_to_project(project_id, user_id, logic.permissions.Permissions.READ)
    user_id = flask_login.current_user.id
    try:
        project = logic.projects.get_project(project_id)
    except logic.errors.ProjectDoesNotExistError:
        return flask.abort(404)
    user_permissions = logic.projects.get_user_project_permissions(project_id=project_id, user_id=user_id, include_groups=True)
    if Permissions.READ in user_permissions:
        show_objects_link = True
    else:
        show_objects_link = False
    if Permissions.READ in user_permissions:
        leave_project_form = LeaveProjectForm()
    else:
        leave_project_form = None
    if Permissions.WRITE in user_permissions:
        edit_project_form = EditProjectForm()
        if edit_project_form.name.data is None:
            edit_project_form.name.data = project.name
        if edit_project_form.description.data is None:
            edit_project_form.description.data = project.description
    else:
        edit_project_form = None
    show_edit_form = False
    project_member_user_ids_and_permissions = logic.projects.get_project_member_user_ids_and_permissions(project_id=project_id, include_groups=False)
    project_member_group_ids_and_permissions = logic.projects.get_project_member_group_ids_and_permissions(project_id=project_id)
    if Permissions.GRANT in user_permissions:
        invitable_user_list = []
        for user in logic.users.get_users():
            if user.id not in project_member_user_ids_and_permissions:
                invitable_user_list.append(user)
    else:
        invitable_user_list = []
    if invitable_user_list:
        invite_user_form = InviteUserToProjectForm()
    else:
        invite_user_form = None
    if Permissions.GRANT in user_permissions:
        invitable_group_list = []
        for group in logic.groups.get_user_groups(user_id):
            if group.id not in project_member_group_ids_and_permissions:
                invitable_group_list.append(group)
    else:
        invitable_group_list = []
    if invitable_group_list:
        invite_group_form = InviteGroupToProjectForm()
    else:
        invite_group_form = None
    if 'leave' in flask.request.form and Permissions.READ in user_permissions:
        if leave_project_form.validate_on_submit():
            try:
                logic.projects.remove_user_from_project(project_id=project_id, user_id=user_id)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash('This project does not exist.', 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.UserDoesNotExistError:
                return flask.abort(500)
            except logic.errors.UserNotMemberOfProjectError:
                flask.flash('You have already left the project.', 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.NoMemberWithGrantPermissionsForProjectError:
                flask.flash('You cannot leave this project, because your are the only user with GRANT permissions.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            else:
                flask.flash('You have successfully left the project.', 'success')
                return flask.redirect(flask.url_for('.projects'))
    if 'edit' in flask.request.form and Permissions.WRITE in user_permissions:
        show_edit_form = True
        if edit_project_form.validate_on_submit():
            try:
                logic.projects.update_project(project_id, edit_project_form.name.data, edit_project_form.description.data)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash('This project does not exist.', 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.ProjectAlreadyExistsError:
                edit_project_form.name.errors.append('A project with this name already exists.')
            except logic.errors.InvalidProjectNameError:
                edit_project_form.name.errors.append('This project name is invalid.')
            else:
                flask.flash('Project information updated successfully.', 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    if 'add_user' in flask.request.form and Permissions.GRANT in user_permissions:
        if invite_user_form.validate_on_submit():
            if not any(user.id == invite_user_form.user_id.data for user in invitable_user_list):
                flask.flash('You cannot add this user.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            try:
                logic.projects.invite_user_to_project(project_id, invite_user_form.user_id.data)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash('This project does not exist.', 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.UserDoesNotExistError:
                flask.flash('This user does not exist.', 'error')
            except logic.errors.UserAlreadyMemberOfProjectError:
                flask.flash('This user is already a member of this project.', 'error')
            else:
                flask.flash('The user was successfully invited to the project.', 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    if 'add_group' in flask.request.form and Permissions.GRANT in user_permissions:
        if invite_group_form.validate_on_submit():
            if not any(group.id == invite_group_form.group_id.data for group in invitable_group_list):
                flask.flash('You cannot add this group.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            try:
                logic.projects.add_group_to_project(project_id, invite_group_form.group_id.data, permissions=Permissions.READ)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash('This project does not exist.', 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.GroupDoesNotExistError:
                flask.flash('This group does not exist.', 'error')
            except logic.errors.GroupAlreadyMemberOfProjectError:
                flask.flash('This group is already a member of this project.', 'error')
            else:
                flask.flash('The group was successfully added to the project.', 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    return flask.render_template('project.html', get_user=logic.users.get_user, get_group=logic.groups.get_group, project=project, project_member_user_ids_and_permissions=project_member_user_ids_and_permissions, project_member_group_ids_and_permissions=project_member_group_ids_and_permissions, leave_project_form=leave_project_form, edit_project_form=edit_project_form, show_edit_form=show_edit_form, invite_user_form=invite_user_form, invitable_user_list=invitable_user_list, invite_group_form=invite_group_form, invitable_group_list=invitable_group_list, show_objects_link=show_objects_link)


@frontend.route('/projects/', methods=['GET', 'POST'])
@flask_login.login_required
def projects():
    user_id = None
    if 'user_id' in flask.request.args:
        try:
            user_id = int(flask.request.args['user_id'])
        except ValueError:
            pass
    if user_id is not None:
        if user_id != flask_login.current_user.id and not flask_login.current_user.is_admin:
            return flask.abort(403)
        projects = logic.projects.get_user_projects(user_id)
    else:
        projects = logic.projects.get_projects()
    for project in projects:
        project.permissions = logic.projects.get_user_project_permissions(project_id=project.id, user_id=flask_login.current_user.id, include_groups=True)
    create_project_form = CreateProjectForm()
    if create_project_form.name.data is None:
        create_project_form.name.data = ''
    if create_project_form.description.data is None:
        create_project_form.description.data = ''
    show_create_form = False
    if 'create' in flask.request.form:
        show_create_form = True
        if create_project_form.validate_on_submit():
            try:
                project_id = logic.projects.create_project(create_project_form.name.data, create_project_form.description.data, flask_login.current_user.id).id
            except logic.errors.ProjectAlreadyExistsError:
                create_project_form.name.errors.append('A project with this name already exists.')
            except logic.errors.InvalidProjectNameError:
                create_project_form.name.errors.append('This project name is invalid.')
            else:
                flask.flash('The project has been created successfully.', 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    return flask.render_template("projects.html", projects=projects, create_project_form=create_project_form, show_create_form=show_create_form, Permissions=logic.projects.Permissions)


@frontend.route('/projects/<int:project_id>/permissions')
@flask_login.login_required
def project_permissions(project_id):
    try:
        project = logic.projects.get_project(project_id)
    except logic.errors.ProjectDoesNotExistError:
        return flask.abort(404)

    user_permissions = logic.projects.get_project_member_user_ids_and_permissions(project_id, include_groups=False)
    group_permissions = logic.projects.get_project_member_group_ids_and_permissions(project_id)
    if Permissions.GRANT in logic.projects.get_user_project_permissions(project_id=project_id, user_id=flask_login.current_user.id, include_groups=True):
        user_permission_form_data = []
        for user_id, permissions in user_permissions.items():
            if user_id is None:
                continue
            user_permission_form_data.append({'user_id': user_id, 'permissions': permissions.name.lower()})
        group_permission_form_data = []
        for group_id, permissions in group_permissions.items():
            if group_id is None:
                continue
            group_permission_form_data.append({'group_id': group_id, 'permissions': permissions.name.lower()})
        edit_user_permissions_form = ProjectPermissionsForm(user_permissions=user_permission_form_data, group_permissions=group_permission_form_data)
    else:
        edit_user_permissions_form = None
    return flask.render_template('project_permissions.html', project=project, user_permissions=user_permissions, group_permissions=group_permissions, project_permissions=project_permissions, get_user=logic.users.get_user, get_group=logic.groups.get_group, Permissions=Permissions, form=edit_user_permissions_form)


@frontend.route('/projects/<int:project_id>/permissions', methods=['POST'])
@flask_login.login_required
def update_project_permissions(project_id):
    try:
        if Permissions.GRANT not in logic.projects.get_user_project_permissions(project_id, flask_login.current_user.id, include_groups=True):
            return flask.abort(403)
    except logic.errors.ProjectDoesNotExistError:
        return flask.abort(404)

    edit_user_permissions_form = ProjectPermissionsForm()
    if 'edit_user_permissions' in flask.request.form and edit_user_permissions_form.validate_on_submit():
        # First handle GRANT updates, then others (to prevent temporarily not having a GRANT user)
        for user_permissions_data in sorted(edit_user_permissions_form.user_permissions.data, key=lambda upd: upd['permissions'] != 'grant'):
            user_id = user_permissions_data['user_id']
            try:
                logic.users.get_user(user_id)
            except logic.errors.UserDoesNotExistError:
                continue
            permissions = Permissions.from_name(user_permissions_data['permissions'])
            try:
                logic.projects.update_user_project_permissions(project_id=project_id, user_id=user_id, permissions=permissions)
            except logic.errors.NoMemberWithGrantPermissionsForProjectError:
                continue
        for group_permissions_data in edit_user_permissions_form.group_permissions.data:
            group_id = group_permissions_data['group_id']
            try:
                logic.groups.get_group(group_id)
            except logic.errors.GroupDoesNotExistError:
                continue
            permissions = Permissions.from_name(group_permissions_data['permissions'])
            logic.projects.update_group_project_permissions(project_id=project_id, group_id=group_id, permissions=permissions)
        flask.flash("Successfully updated project permissions.", 'success')
    else:
        flask.flash("A problem occurred while changing the project permissions. Please try again.", 'error')
    try:
        logic.projects.get_project(project_id)
    except logic.errors.ProjectDoesNotExistError:
        return flask.redirect(flask.url_for('.projects'))
    return flask.redirect(flask.url_for('.project_permissions', project_id=project_id))
