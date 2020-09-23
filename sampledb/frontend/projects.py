# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from .. import logic
from ..logic.object_permissions import Permissions
from ..logic.security_tokens import verify_token
from .projects_forms import CreateProjectForm, EditProjectForm, LeaveProjectForm, InviteUserToProjectForm, InviteGroupToProjectForm, ProjectPermissionsForm, AddSubprojectForm, RemoveSubprojectForm, DeleteProjectForm, RemoveProjectMemberForm, RemoveProjectGroupForm
from .utils import check_current_user_is_not_readonly


@frontend.route('/projects/<int:project_id>', methods=['GET', 'POST'])
@flask_login.login_required
def project(project_id):
    if 'token' in flask.request.args:
        token = flask.request.args.get('token')
        expiration_time_limit = flask.current_app.config['INVITATION_TIME_LIMIT']
        token_data = verify_token(token, salt='invite_to_project', secret_key=flask.current_app.config['SECRET_KEY'], expiration=expiration_time_limit)
        if token_data is None:
            flask.flash('Invalid project invitation token. Please request a new invitation.', 'error')
            return flask.abort(403)
        if 'invitation_id' in token_data:
            if logic.projects.get_project_invitation(token_data['invitation_id']).accepted:
                flask.flash('This invitation token has already been used. Please request a new invitation.', 'error')
                return flask.abort(403)
        if token_data.get('project_id', None) != project_id:
            return flask.abort(403)
        user_id = token_data.get('user_id', None)
        if user_id != flask_login.current_user.id:
            if user_id is not None:
                try:
                    invited_user = logic.users.get_user(user_id)
                    flask.flash('Please sign in as user "{}" to accept this invitation.'.format(invited_user.name), 'error')
                except logic.errors.UserDoesNotExistError:
                    pass
            return flask.abort(403)
        other_project_ids = token_data.get('other_project_ids', [])
        for notification in logic.notifications.get_notifications(user_id, unread_only=True):
            if notification.type == logic.notifications.NotificationType.INVITED_TO_PROJECT:
                if notification.data['project_id'] == project_id:
                    logic.notifications.mark_notification_as_read(notification.id)
        try:
            logic.projects.add_user_to_project(project_id, user_id, logic.object_permissions.Permissions.READ, other_project_ids=other_project_ids)
        except logic.errors.UserAlreadyMemberOfProjectError:
            flask.flash('You are already a member of this project', 'error')
        except logic.errors.ProjectDoesNotExistError:
            pass
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

    project_member_user_ids = list(project_member_user_ids_and_permissions.keys())
    project_member_user_ids.sort(key=lambda user_id: logic.users.get_user(user_id).name.lower())

    project_member_group_ids = list(project_member_group_ids_and_permissions.keys())
    project_member_group_ids.sort(key=lambda group_id: logic.groups.get_group(group_id).name.lower())

    if Permissions.GRANT in user_permissions:
        invitable_user_list = []
        for user in logic.users.get_users(exclude_hidden=True):
            if user.id not in project_member_user_ids_and_permissions:
                invitable_user_list.append(user)
        parent_projects_with_add_permissions = logic.projects.get_ancestor_project_ids(project_id, only_if_child_can_add_users_to_ancestor=True)
    else:
        invitable_user_list = []
        parent_projects_with_add_permissions = []
    if invitable_user_list:
        other_project_ids_data = []
        for parent_project_id in parent_projects_with_add_permissions:
            other_project_ids_data.append({'project_id': parent_project_id})
        invite_user_form = InviteUserToProjectForm(other_project_ids=other_project_ids_data)
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
        other_project_ids_data = []
        for parent_project_id in parent_projects_with_add_permissions:
            other_project_ids_data.append({'project_id': parent_project_id})
        invite_group_form = InviteGroupToProjectForm(other_project_ids=other_project_ids_data)
    else:
        invite_group_form = None
    child_project_ids = logic.projects.get_child_project_ids(project_id)
    child_project_ids_can_add_to_parent = {child_project_id: logic.projects.can_child_add_users_to_parent_project(parent_project_id=project_id, child_project_id=child_project_id) for child_project_id in child_project_ids}
    parent_project_ids = logic.projects.get_parent_project_ids(project_id)
    add_subproject_form = None
    remove_subproject_form = None
    delete_project_form = None
    remove_project_member_form = None
    remove_project_group_form = None
    addable_projects = []
    addable_project_ids = []
    if Permissions.GRANT in user_permissions:
        for other_project in logic.projects.get_user_projects(flask_login.current_user.id, include_groups=True):
            if other_project.id == project.id:
                continue
            if Permissions.GRANT in logic.projects.get_user_project_permissions(other_project.id, flask_login.current_user.id, include_groups=True):
                addable_projects.append(other_project)
        addable_project_ids = logic.projects.filter_child_project_candidates(project_id, [child_project.id for child_project in addable_projects])
        addable_projects = [logic.projects.get_project(child_project_id) for child_project_id in addable_project_ids]
        if addable_projects:
            add_subproject_form = AddSubprojectForm()
        if child_project_ids:
            remove_subproject_form = RemoveSubprojectForm()
        delete_project_form = DeleteProjectForm()
        remove_project_member_form = RemoveProjectMemberForm()
        remove_project_group_form = RemoveProjectGroupForm()

    project_invitations = None
    show_invitation_log = flask_login.current_user.is_admin and logic.settings.get_user_settings(flask_login.current_user.id)['SHOW_INVITATION_LOG']
    if Permissions.GRANT in user_permissions or flask_login.current_user.is_admin:
        project_invitations = logic.projects.get_project_invitations(
            project_id=project_id,
            include_accepted_invitations=show_invitation_log,
            include_expired_invitations=show_invitation_log
        )

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
    if 'delete' in flask.request.form and Permissions.GRANT in user_permissions:
        if delete_project_form.validate_on_submit():
            check_current_user_is_not_readonly()
            try:
                logic.projects.delete_project(project_id=project_id)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash('This project has already been deleted.', 'success')
                return flask.redirect(flask.url_for('.projects'))
            else:
                flask.flash('You have successfully deleted the project.', 'success')
                return flask.redirect(flask.url_for('.projects'))
    if 'remove_member' in flask.request.form and Permissions.GRANT in user_permissions:
        if remove_project_member_form.validate_on_submit():
            check_current_user_is_not_readonly()
            member_id_str = flask.request.form['remove_member']
            try:
                member_id = int(member_id_str)
            except ValueError:
                flask.flash('The member ID was invalid. Please contact an administrator.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            if member_id == flask_login.current_user.id:
                flask.flash('You cannot remove yourself from a project. Please press "Leave Project" instead.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            try:
                logic.projects.remove_user_from_project(project_id=project_id, user_id=member_id)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash('This project does not exist.', 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.UserDoesNotExistError:
                flask.flash('This user does not exist.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            except logic.errors.UserNotMemberOfProjectError:
                flask.flash('This user is not a member of this project.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            except logic.errors.NoMemberWithGrantPermissionsForProjectError:
                flask.flash('You cannot remove this users from this project, because they are the only user with GRANT permissions.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            else:
                flask.flash('You have successfully removed this user from the project.', 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    if 'remove_group' in flask.request.form and Permissions.GRANT in user_permissions:
        if remove_project_group_form.validate_on_submit():
            check_current_user_is_not_readonly()
            group_id_str = flask.request.form['remove_group']
            try:
                group_id = int(group_id_str)
            except ValueError:
                flask.flash('The group ID was invalid. Please contact an administrator.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            try:
                logic.projects.remove_group_from_project(project_id=project_id, group_id=group_id)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash('This project does not exist.', 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.GroupDoesNotExistError:
                flask.flash('This group does not exist.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            except logic.errors.GroupNotMemberOfProjectError:
                flask.flash('This group is not a member of this project.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            except logic.errors.NoMemberWithGrantPermissionsForProjectError:
                flask.flash('You cannot remove this group from this project, because they are the only group with GRANT permissions.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            else:
                flask.flash('You have successfully removed this group from the project.', 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    if 'edit' in flask.request.form and Permissions.WRITE in user_permissions:
        show_edit_form = True
        if edit_project_form.validate_on_submit():
            check_current_user_is_not_readonly()
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
            check_current_user_is_not_readonly()
            if not any(user.id == invite_user_form.user_id.data for user in invitable_user_list):
                flask.flash('You cannot add this user.', 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            try:
                other_project_ids = []
                for other_project_id_form in invite_user_form.other_project_ids:
                    try:
                        if other_project_id_form.add_user.data:
                            other_project_ids.append(int(other_project_id_form.project_id.data))
                    except (KeyError, ValueError):
                        pass
                logic.projects.invite_user_to_project(project_id, invite_user_form.user_id.data, flask_login.current_user.id, other_project_ids)
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
            check_current_user_is_not_readonly()
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
    if 'remove_subproject' in flask.request.form and Permissions.GRANT in user_permissions:
        if remove_subproject_form is not None and remove_subproject_form.validate_on_submit():
            check_current_user_is_not_readonly()
            child_project_id = remove_subproject_form.child_project_id.data
            if child_project_id not in child_project_ids:
                flask.flash('Project #{} is not a subproject of this project.'.format(int(child_project_id)), 'error')
            else:
                logic.projects.delete_subproject_relationship(project_id, child_project_id)
                flask.flash('The subproject was successfully removed from this project.', 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    if 'add_subproject' in flask.request.form and Permissions.GRANT in user_permissions:
        if add_subproject_form is not None and add_subproject_form.validate_on_submit():
            check_current_user_is_not_readonly()
            child_project_id = add_subproject_form.child_project_id.data
            if child_project_id not in addable_project_ids:
                flask.flash('Project #{} cannot become a subproject of this project.'.format(int(child_project_id)), 'error')
            else:
                logic.projects.create_subproject_relationship(project_id, child_project_id, child_can_add_users_to_parent=add_subproject_form.child_can_add_users_to_parent.data)
                flask.flash('The subproject was successfully added to this project.', 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    return flask.render_template(
        'project.html',
        get_user=logic.users.get_user,
        get_group=logic.groups.get_group,
        get_project=logic.projects.get_project,
        project=project,
        project_member_user_ids=project_member_user_ids,
        project_member_group_ids=project_member_group_ids,
        project_member_user_ids_and_permissions=project_member_user_ids_and_permissions,
        project_member_group_ids_and_permissions=project_member_group_ids_and_permissions,
        project_invitations=project_invitations,
        show_invitation_log=show_invitation_log,
        leave_project_form=leave_project_form,
        delete_project_form=delete_project_form,
        remove_project_member_form=remove_project_member_form,
        remove_project_group_form=remove_project_group_form,
        edit_project_form=edit_project_form,
        show_edit_form=show_edit_form,
        invite_user_form=invite_user_form,
        invitable_user_list=invitable_user_list,
        invite_group_form=invite_group_form,
        invitable_group_list=invitable_group_list,
        show_objects_link=show_objects_link,
        child_project_ids=child_project_ids,
        child_project_ids_can_add_to_parent=child_project_ids_can_add_to_parent,
        parent_project_ids=parent_project_ids,
        add_subproject_form=add_subproject_form,
        addable_projects=addable_projects,
        remove_subproject_form=remove_subproject_form,
        user_may_edit_permissions=Permissions.GRANT in user_permissions
    )


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
            check_current_user_is_not_readonly()
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
    check_current_user_is_not_readonly()
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
