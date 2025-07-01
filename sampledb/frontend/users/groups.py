# coding: utf-8
"""

"""
import json
import typing

import flask
import flask_login
from flask_babel import _

from .. import frontend
from ... import logic
from .forms import InviteUserForm, EditGroupForm, LeaveGroupForm, CreateGroupForm, DeleteGroupForm, RemoveGroupMemberForm
from ..users_forms import RevokeInvitationForm
from ...logic.security_tokens import verify_token
from ...logic.languages import get_languages, Language, get_language_by_lang_code, get_language
from ..utils import check_current_user_is_not_readonly
from ...utils import FlaskResponseT
from ...logic.utils import get_translated_text
from ...models import NotificationType


@frontend.route('/groups/', methods=['GET', 'POST'])
@flask_login.login_required
def groups() -> FlaskResponseT:
    user_id = None
    allowed_language_ids = [
        language.id
        for language in get_languages(only_enabled_for_input=True)
    ]
    english = get_language(Language.ENGLISH)
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
    group_membership_by_id = {
        group.id: (flask_login.current_user.id in logic.groups.get_group_member_ids(group.id))
        for group in groups
    }
    create_group_form = CreateGroupForm()
    group_categories = list(logic.group_categories.get_group_categories())
    group_categories.sort(key=lambda category: get_translated_text(category.name).lower())
    create_group_form.categories.choices = [
        (str(category.id), category)
        for category in group_categories
    ]
    show_create_form = False
    if 'create' in flask.request.form:
        check_current_user_is_not_readonly()
        show_create_form = True
        if create_group_form.validate_on_submit():
            if flask_login.current_user.is_admin or not flask.current_app.config['ONLY_ADMINS_CAN_CREATE_GROUPS']:
                try:
                    translations = json.loads(create_group_form.translations.data)
                    if not translations:
                        raise ValueError(_('Please enter at least an english name.'))
                    names = {}
                    descriptions = {}
                    for translation in translations:
                        name = translation['name'].strip()
                        description = translation['description'].strip()
                        language_id = int(translation['language_id'])
                        if language_id not in allowed_language_ids:
                            continue

                        if language_id == Language.ENGLISH:
                            if name == '':
                                raise ValueError(_('Please enter at least an english name.'))

                        lang_code = get_language(language_id).lang_code

                        names[lang_code] = name
                        if description != '':
                            descriptions[lang_code] = description
                        else:
                            descriptions[lang_code] = ''
                    group_id = logic.groups.create_group(names, descriptions, flask_login.current_user.id).id
                    logic.group_categories.set_basic_group_categories(
                        basic_group_id=group_id,
                        category_ids=[
                            int(category_id)
                            for category_id in create_group_form.categories.data
                        ]
                    )
                except ValueError as e:
                    flask.flash(str(e), 'error')
                    create_group_form.translations.errors.append(str(e))
                except logic.errors.GroupAlreadyExistsError:
                    create_group_form.translations.errors.append(_('A basic group with this name already exists.'))
                except logic.errors.InvalidGroupNameError:
                    create_group_form.translations.errors.append(_('This basic group name is invalid.'))
                else:
                    flask.flash(_('The basic group has been created successfully.'), 'success')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
            else:
                # create_group_form.name.errors.append('Only administrators can create basic groups.')
                create_group_form.translations.errors.append(_('Only administrators can create basic groups.'))
    group_categories_by_id = {
        category.id: category
        for category in group_categories
    }
    group_category_names = logic.group_categories.get_full_group_category_names()
    group_category_tree = logic.group_categories.get_group_category_tree(
        basic_group_ids={group.id for group in groups},
        project_group_ids=set()
    )
    groups.sort(key=lambda group: get_translated_text(group.name).lower())
    return flask.render_template(
        "groups/groups.html",
        groups=groups,
        sorted_by_name=lambda groups: sorted(groups, key=lambda group: get_translated_text(group.name).lower()),
        group_membership_by_id=group_membership_by_id,
        create_group_form=create_group_form,
        show_create_form=show_create_form,
        ENGLISH=english,
        languages=get_languages(only_enabled_for_input=True),
        group_categories=group_categories,
        group_categories_by_id=group_categories_by_id,
        group_category_names=group_category_names,
        group_category_tree=group_category_tree,
    )


@frontend.route('/groups/<int:group_id>', methods=['GET', 'POST'])
@flask_login.login_required
def group(group_id: int) -> FlaskResponseT:
    name_language_ids = []
    description_language_ids = []
    token = flask.request.args.get('token')
    if token:
        expiration_time_limit = flask.current_app.config['INVITATION_TIME_LIMIT']
        token_data = verify_token(token, salt='invite_to_group', secret_key=flask.current_app.config['SECRET_KEY'], expiration=expiration_time_limit)
        if token_data is None:
            flask.flash(_('Invalid basic group invitation token. Please request a new invitation.'), 'error')
            return flask.abort(403)
        if 'invitation_id' in token_data:
            try:
                group_invitation = logic.groups.get_group_invitation(token_data['invitation_id'])
            except logic.errors.GroupInvitationDoesNotExistError:
                flask.flash(_('Unknown basic group invitation. Please request a new invitation.'), 'error')
                return flask.abort(403)
            if group_invitation.accepted:
                flask.flash(_('This invitation token has already been used. Please request a new invitation.'), 'error')
                return flask.abort(403)
            if group_invitation.revoked:
                flask.flash(_('This invitation has been revoked. Please request a new invitation.'), 'error')
                return flask.abort(403)
        if token_data.get('group_id', None) != group_id:
            return flask.abort(403)
        user_id = token_data.get('user_id', None)
        if user_id != flask_login.current_user.id:
            try:
                invited_user = logic.users.get_user(user_id)
                flask.flash(_('Please sign in as user "%(user_name)s" to accept this invitation.', user_name=invited_user.name), 'error')
            except logic.errors.UserDoesNotExistError:
                pass
            return flask.abort(403)

        for notification in logic.notifications.get_notifications(user_id, unread_only=True):
            if notification.type == NotificationType.INVITED_TO_GROUP:
                if notification.data['group_id'] == group_id:
                    logic.notifications.mark_notification_as_read(notification.id)

        try:
            logic.groups.add_user_to_group(group_id, user_id)
        except logic.errors.UserAlreadyMemberOfGroupError:
            flask.flash(_('You are already a member of this basic group.'), 'error')
        except logic.errors.GroupDoesNotExistError:
            pass
    try:
        group_member_ids = logic.groups.get_group_member_ids(group_id)
    except logic.errors.GroupDoesNotExistError:
        flask.flash(_('This basic group does not exist.'), 'error')
        return flask.abort(404)
    group_member_ids.sort(key=lambda user_id: (logic.users.get_user(user_id).name or '').lower())
    user_is_member = flask_login.current_user.id in group_member_ids
    user_can_leave = user_is_member
    # admins are treated as members for the sake of permissions
    user_is_member = user_is_member or flask_login.current_user.has_admin_permissions
    group = logic.groups.get_group(group_id)
    show_edit_form = False
    revoke_invitation_form = None

    english = get_language(Language.ENGLISH)
    allowed_language_ids = [
        language.id
        for language in get_languages(only_enabled_for_input=True)
    ]

    class GroupTranslation(typing.TypedDict):
        language_id: int
        lang_name: str
        name: str
        description: str

    translations: typing.List[GroupTranslation] = []
    if user_is_member or flask_login.current_user.has_admin_permissions:
        show_objects_link = True
        if user_can_leave:
            leave_group_form = LeaveGroupForm()
        else:
            leave_group_form = None
        invite_user_form = InviteUserForm()
        revoke_invitation_form = RevokeInvitationForm()
        if 'revoke_invitation' in flask.request.form and revoke_invitation_form.validate_on_submit():
            invitation_id = revoke_invitation_form.invitation_id.data
            try:
                invitation = logic.groups.get_group_invitation(invitation_id)
            except logic.errors.GroupInvitationDoesNotExistError:
                flask.flash(_('Unknown basic group invitation.'), 'error')
                return flask.redirect(flask.url_for('.group', group_id=group_id))
            if invitation.accepted:
                flask.flash(_('This basic group invitation has already been accepted.'), 'error')
            else:
                logic.groups.revoke_group_invitation(invitation_id)
                flask.flash(_('The invitation has been revoked.'), 'success')
            return flask.redirect(flask.url_for('.group', group_id=group_id))
        edit_group_form = EditGroupForm()
        group_categories = list(logic.group_categories.get_group_categories())
        group_categories.sort(key=lambda category: get_translated_text(category.name).lower())
        edit_group_form.categories.choices = [
            (str(category.id), category)
            for category in group_categories
        ]
        if flask_login.current_user.is_admin or not flask.current_app.config['ONLY_ADMINS_CAN_DELETE_GROUPS'] or set(group_member_ids) == {flask_login.current_user.id}:
            delete_group_form = DeleteGroupForm()
        else:
            delete_group_form = None
        remove_group_member_form = RemoveGroupMemberForm()

        for lang_code, name in group.name.items():
            lang_id = get_language_by_lang_code(lang_code).id
            name_language_ids.append(lang_id)
            translation = GroupTranslation(
                language_id=lang_id,
                lang_name=get_translated_text(get_language(lang_id).names),
                name=name,
                description=''
            )
            translations.append(translation)

        for lang_code, description in group.description.items():
            if lang_code == '':
                continue
            found = False
            lang_id = get_language_by_lang_code(lang_code).id
            description_language_ids.append(lang_id)
            for translation in translations:
                if lang_id == translation['language_id']:
                    translation['description'] = description
                    found = True
                    break
            if not found:
                translation = GroupTranslation(
                    language_id=lang_id,
                    lang_name=get_translated_text(get_language(lang_id).names),
                    name='',
                    description=description[1]
                )
                translations.append(translation)

        if 'edit' in flask.request.form:
            check_current_user_is_not_readonly()
            show_edit_form = True
            if edit_group_form.validate_on_submit():
                try:
                    translations = json.loads(edit_group_form.translations.data)
                    if not translations:
                        raise ValueError(_('Please enter at least an english name.'))
                    names = {}
                    descriptions = {}
                    for translation in translations:
                        name = translation['name'].strip()
                        description = translation['description'].strip()
                        language_id = int(translation['language_id'])

                        if language_id not in allowed_language_ids:
                            continue

                        if language_id == Language.ENGLISH:
                            if name == '':
                                raise ValueError(_('Please enter at least an english name.'))
                        elif name == '' and description == '':
                            continue

                        lang_code = get_language(language_id).lang_code

                        names[lang_code] = name
                        if description != '':
                            descriptions[lang_code] = description
                        else:
                            descriptions[lang_code] = ''
                    logic.groups.update_group(group_id, names, descriptions)
                    logic.group_categories.set_basic_group_categories(
                        basic_group_id=group_id,
                        category_ids=[
                            int(category_id)
                            for category_id in edit_group_form.categories.data
                        ]
                    )
                except ValueError as e:
                    flask.flash(str(e), 'error')
                    edit_group_form.translations.errors.append(str(e))
                except logic.errors.GroupDoesNotExistError:
                    flask.flash(_('This basic group does not exist.'), 'error')
                    return flask.redirect(flask.url_for('.groups'))
                except logic.errors.GroupAlreadyExistsError:
                    edit_group_form.translations.errors.append(_('A basic group with this name already exists.'))
                except logic.errors.InvalidGroupNameError:
                    edit_group_form.translations.errors.append(_('This basic group name is invalid.'))
                else:
                    flask.flash(_('Basic group information updated successfully.'), 'success')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
        elif 'add_user' in flask.request.form:
            check_current_user_is_not_readonly()
            if invite_user_form.validate_on_submit():
                try:
                    if invite_user_form.add_directly.data and flask_login.current_user.is_admin:
                        logic.groups.add_user_to_group(
                            group_id=group_id,
                            user_id=invite_user_form.user_id.data
                        )
                        flask.flash(_('The user was successfully added to the basic group.'), 'success')
                    else:
                        logic.groups.invite_user_to_group(
                            group_id=group_id,
                            user_id=invite_user_form.user_id.data,
                            inviter_id=flask_login.current_user.id
                        )
                        flask.flash(_('The user was successfully invited to the basic group.'), 'success')
                except logic.errors.GroupDoesNotExistError:
                    flask.flash(_('This basic group does not exist.'), 'error')
                    return flask.redirect(flask.url_for('.groups'))
                except logic.errors.UserDoesNotExistError:
                    flask.flash(_('This user does not exist.'), 'error')
                except logic.errors.UserAlreadyMemberOfGroupError:
                    flask.flash(_('This user is already a member of this basic group.'), 'error')
                else:
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
        elif 'leave' in flask.request.form and leave_group_form is not None:
            if user_can_leave and leave_group_form.validate_on_submit():
                try:
                    logic.groups.remove_user_from_group(group_id, flask_login.current_user.id)
                except logic.errors.GroupDoesNotExistError:
                    flask.flash(_('This basic group does not exist.'), 'error')
                    return flask.redirect(flask.url_for('.groups'))
                except logic.errors.UserDoesNotExistError:
                    return flask.abort(500)
                except logic.errors.UserNotMemberOfGroupError:
                    flask.flash(_('You have already left the basic group.'), 'error')
                    return flask.redirect(flask.url_for('.groups'))
                else:
                    flask.flash(_('You have successfully left the basic group.'), 'success')
                    return flask.redirect(flask.url_for('.groups'))
        elif 'delete' in flask.request.form and delete_group_form:
            check_current_user_is_not_readonly()
            if delete_group_form.validate_on_submit():
                try:
                    logic.groups.delete_group(group_id)
                except logic.errors.GroupDoesNotExistError:
                    flask.flash(_('This basic group has already been deleted.'), 'success')
                    return flask.redirect(flask.url_for('.groups'))
                else:
                    flask.flash(_('You have successfully deleted the basic group.'), 'success')
                    return flask.redirect(flask.url_for('.groups'))
        elif 'remove_member' in flask.request.form:
            check_current_user_is_not_readonly()
            if remove_group_member_form.validate_on_submit():
                member_id_str = flask.request.form['remove_member']
                try:
                    member_id = int(member_id_str)
                except ValueError:
                    flask.flash(_('The member ID was invalid. Please contact an administrator.'), 'error')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
                try:
                    logic.groups.remove_user_from_group(group_id, member_id)
                except logic.errors.GroupDoesNotExistError:
                    flask.flash(_('This basic group does not exist.'), 'error')
                    return flask.redirect(flask.url_for('.groups'))
                except logic.errors.UserDoesNotExistError:
                    flask.flash(_('This user does not exist.'), 'error')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
                except logic.errors.UserNotMemberOfGroupError:
                    flask.flash(_('This user is not a member of this basic group.'), 'success')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
                else:
                    flask.flash(_('This user has been removed from this basic group.'), 'success')
                    return flask.redirect(flask.url_for('.group', group_id=group_id))
    else:
        if flask.request.method.lower() == 'post':
            return flask.abort(403)
        leave_group_form = None
        edit_group_form = None
        invite_user_form = None
        delete_group_form = None
        remove_group_member_form = None
        show_objects_link = False
        group_categories = None

    group_invitations = None
    show_invitation_log = flask_login.current_user.is_admin and logic.settings.get_user_setting(flask_login.current_user.id, 'SHOW_INVITATION_LOG')
    if user_is_member or flask_login.current_user.is_admin:
        group_invitations = logic.groups.get_group_invitations(
            group_id=group_id,
            include_accepted_invitations=show_invitation_log,
            include_expired_invitations=show_invitation_log,
            include_revoked_invitations=show_invitation_log
        )

    if english.id not in description_language_ids:
        description_language_ids.append(english.id)
    basic_group_categories = logic.group_categories.get_basic_group_categories(group.id)
    category_names = logic.group_categories.get_full_group_category_names()
    return flask.render_template(
        'groups/group.html',
        ENGLISH=english,
        translations=translations,
        languages=get_languages(only_enabled_for_input=True),
        name_language_ids=name_language_ids,
        description_language_ids=description_language_ids,
        group=group,
        group_member_ids=group_member_ids,
        group_categories=group_categories,
        group_category_names=logic.group_categories.get_full_group_category_names(),
        basic_group_categories=basic_group_categories,
        category_names=category_names,
        get_users=logic.users.get_users,
        get_user=logic.users.get_user,
        group_invitations=group_invitations,
        show_objects_link=show_objects_link,
        show_invitation_log=show_invitation_log,
        leave_group_form=leave_group_form,
        delete_group_form=delete_group_form,
        remove_group_member_form=remove_group_member_form,
        edit_group_form=edit_group_form,
        invite_user_form=invite_user_form,
        show_edit_form=show_edit_form,
        revoke_invitation_form=revoke_invitation_form
    )
