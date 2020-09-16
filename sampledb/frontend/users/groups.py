# coding: utf-8
"""

"""

import flask
import flask_login

from .. import frontend
from ... import logic
from .forms import InviteUserForm, EditGroupForm, LeaveGroupForm, CreateGroupForm, DeleteGroupForm, RemoveGroupMemberForm
from ...logic.security_tokens import verify_token
from ..utils import check_current_user_is_not_readonly


@frontend.route('/groups/', methods=['GET', 'POST'])
@flask_login.login_required
def groups():
    user_id = None
    if 'user_id' in flask.request.args:
        try:
            user_id = int(flask.request.args['user_id'])
        except ValueError:
            pass
    if user_id is not None:
        if user_id != flask_login.current_user.id and not flask_login.current_user.is_admin:
            return flask.abort(403)
        groups = logic.groups.get_user_groups(user_id)
    else:
        groups = logic.groups.get_groups()
    for group in groups:
        group.is_member = (flask_login.current_user.id in logic.groups.get_group_member_ids(group.id))
    create_group_form = CreateGroupForm()
    if create_group_form.name.data is None:
        create_group_form.name.data = ''
    if create_group_form.description.data is None:
        create_group_form.description.data = ''
    show_create_form = False
    if 'create' in flask.request.form:
        check_current_user_is_not_readonly()
        show_create_form = True
        if create_group_form.validate_on_submit():
            try:
                group_id = logic.groups.create_group(create_group_form.name.data, create_group_form.description.data, flask_login.current_user.id).id
            except logic.errors.GroupAlreadyExistsError:
                create_group_form.name.errors.append('A group with this name already exists.')
            except logic.errors.InvalidGroupNameError:
                create_group_form.name.errors.append('This group name is invalid.')
            else:
                flask.flash('The group has been created successfully.', 'success')
                return flask.redirect(flask.url_for('.group', group_id=group_id))
    return flask.render_template("groups.html", groups=groups, create_group_form=create_group_form, show_create_form=show_create_form)


@frontend.route('/groups/<int:group_id>', methods=['GET', 'POST'])
@flask_login.login_required
def group(group_id):
    if 'token' in flask.request.args:
        token = flask.request.args.get('token')
        expiration_time_limit = flask.current_app.config['INVITATION_TIME_LIMIT']
        token_data = verify_token(token, salt='invite_to_group', secret_key=flask.current_app.config['SECRET_KEY'], expiration=expiration_time_limit)
        if token_data is None:
            flask.flash('Invalid group invitation token. Please request a new invitation.', 'error')
            return flask.abort(403)
        if 'invitation_id' in token_data:
            if logic.groups.get_group_invitation(token_data['invitation_id']).accepted:
                flask.flash('This invitation token has already been used. Please request a new invitation.', 'error')
                return flask.abort(403)
        if token_data.get('group_id', None) != group_id:
            return flask.abort(403)
        user_id = token_data.get('user_id', None)
        if user_id != flask_login.current_user.id:
            try:
                invited_user = logic.users.get_user(user_id)
                flask.flash('Please sign in as user "{}" to accept this invitation.'.format(invited_user.name), 'error')
            except logic.errors.UserDoesNotExistError:
                pass
            return flask.abort(403)

        for notification in logic.notifications.get_notifications(user_id, unread_only=True):
            if notification.type == logic.notifications.NotificationType.INVITED_TO_GROUP:
                if notification.data['group_id'] == group_id:
                    logic.notifications.mark_notification_as_read(notification.id)

        try:
            logic.groups.add_user_to_group(group_id, user_id)
        except logic.errors.UserAlreadyMemberOfGroupError:
            flask.flash('You are already a member of this group.', 'error')
        except logic.errors.GroupDoesNotExistError:
            pass
    try:
        group_member_ids = logic.groups.get_group_member_ids(group_id)
    except logic.errors.GroupDoesNotExistError:
        flask.flash('This group does not exist.', 'error')
        return flask.abort(404)
    group_member_ids.sort(key=lambda user_id: logic.users.get_user(user_id).name.lower())
    user_is_member = flask_login.current_user.id in group_member_ids
    group = logic.groups.get_group(group_id)
    show_edit_form = False

    if user_is_member:
        leave_group_form = LeaveGroupForm()
        invite_user_form = InviteUserForm()
        edit_group_form = EditGroupForm()
        delete_group_form = DeleteGroupForm()
        remove_group_member_form = RemoveGroupMemberForm()
        if edit_group_form.name.data is None:
            edit_group_form.name.data = group.name
        if edit_group_form.description.data is None:
            edit_group_form.description.data = group.description

        if 'edit' in flask.request.form:
            check_current_user_is_not_readonly()
            show_edit_form = True
            if edit_group_form.validate_on_submit():
                try:
                    logic.groups.update_group(group_id, edit_group_form.name.data, edit_group_form.description.data)
                except logic.errors.GroupDoesNotExistError:
                    flask.flash('This group does not exist.', 'error')
                    return flask.redirect(flask.url_for('.groups'))
                except logic.errors.GroupAlreadyExistsError:
                    edit_group_form.name.errors.append('A group with this name already exists.')
                except logic.errors.InvalidGroupNameError:
                    edit_group_form.name.errors.append('This group name is invalid.')
                else:
                    flask.flash('Group information updated successfully.', 'success')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
        elif 'add_user' in flask.request.form:
            check_current_user_is_not_readonly()
            if invite_user_form.validate_on_submit():
                try:
                    logic.groups.invite_user_to_group(group_id, invite_user_form.user_id.data, flask_login.current_user.id)
                except logic.errors.GroupDoesNotExistError:
                    flask.flash('This group does not exist.', 'error')
                    return flask.redirect(flask.url_for('.groups'))
                except logic.errors.UserDoesNotExistError:
                    flask.flash('This user does not exist.', 'error')
                except logic.errors.UserAlreadyMemberOfGroupError:
                    flask.flash('This user is already a member of this group', 'error')
                else:
                    flask.flash('The user was successfully invited to the group.', 'success')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
        elif 'leave' in flask.request.form:
            if leave_group_form.validate_on_submit():
                try:
                    logic.groups.remove_user_from_group(group_id, flask_login.current_user.id)
                except logic.errors.GroupDoesNotExistError:
                    flask.flash('This group does not exist.', 'error')
                    return flask.redirect(flask.url_for('.groups'))
                except logic.errors.UserDoesNotExistError:
                    return flask.abort(500)
                except logic.errors.UserNotMemberOfGroupError:
                    flask.flash('You have already left the group.', 'error')
                    return flask.redirect(flask.url_for('.groups'))
                else:
                    flask.flash('You have successfully left the group.', 'success')
                    return flask.redirect(flask.url_for('.groups'))
        elif 'delete' in flask.request.form:
            check_current_user_is_not_readonly()
            if delete_group_form.validate_on_submit():
                try:
                    logic.groups.delete_group(group_id)
                except logic.errors.GroupDoesNotExistError:
                    flask.flash('This group has already been deleted.', 'success')
                    return flask.redirect(flask.url_for('.groups'))
                else:
                    flask.flash('You have successfully deleted the group.', 'success')
                    return flask.redirect(flask.url_for('.groups'))
        elif 'remove_member' in flask.request.form:
            check_current_user_is_not_readonly()
            if remove_group_member_form.validate_on_submit():
                member_id_str = flask.request.form['remove_member']
                try:
                    member_id = int(member_id_str)
                except ValueError:
                    flask.flash('The member ID was invalid. Please contact an administrator.', 'error')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
                try:
                    logic.groups.remove_user_from_group(group_id, member_id)
                except logic.errors.GroupDoesNotExistError:
                    flask.flash('This group does not exist.', 'error')
                    return flask.redirect(flask.url_for('.groups'))
                except logic.errors.UserDoesNotExistError:
                    flask.flash('This user does not exist.', 'error')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
                except logic.errors.UserNotMemberOfGroupError:
                    flask.flash('This user is not a member of this group.', 'success')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
                else:
                    flask.flash('This user has been removed from this group.', 'success')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
    else:
        if flask.request.method.lower() == 'post':
            return flask.abort(403)
        leave_group_form = None
        edit_group_form = None
        invite_user_form = None
        delete_group_form = None
        remove_group_member_form = None

    group_invitations = None
    show_invitation_log = flask_login.current_user.is_admin and logic.settings.get_user_settings(flask_login.current_user.id)['SHOW_INVITATION_LOG']
    if user_is_member or flask_login.current_user.is_admin:
        group_invitations = logic.groups.get_group_invitations(
            group_id=group_id,
            include_accepted_invitations=show_invitation_log,
            include_expired_invitations=show_invitation_log
        )

    return flask.render_template(
        'group.html',
        group=group,
        group_member_ids=group_member_ids,
        get_users=logic.users.get_users,
        get_user=logic.users.get_user,
        group_invitations=group_invitations,
        show_invitation_log=show_invitation_log,
        leave_group_form=leave_group_form,
        delete_group_form=delete_group_form,
        remove_group_member_form=remove_group_member_form,
        edit_group_form=edit_group_form,
        invite_user_form=invite_user_form,
        show_edit_form=show_edit_form
    )
