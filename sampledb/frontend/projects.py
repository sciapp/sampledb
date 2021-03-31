# coding: utf-8
"""

"""

import flask
import flask_login
import json
from flask_babel import _

from . import frontend
from .. import logic
from ..logic.object_permissions import Permissions
from ..logic.security_tokens import verify_token
from ..logic.languages import get_languages, get_language, get_language_by_lang_code
from ..models.languages import Language
from .projects_forms import CreateProjectForm, EditProjectForm, LeaveProjectForm, InviteUserToProjectForm, InviteGroupToProjectForm, ProjectPermissionsForm, AddSubprojectForm, RemoveSubprojectForm, DeleteProjectForm, RemoveProjectMemberForm, RemoveProjectGroupForm, ObjectLinkForm
from .utils import check_current_user_is_not_readonly
from ..logic.utils import get_translated_text


@frontend.route('/projects/<int:project_id>', methods=['GET', 'POST'])
@flask_login.login_required
def project(project_id):
    if 'token' in flask.request.args:
        token = flask.request.args.get('token')
        expiration_time_limit = flask.current_app.config['INVITATION_TIME_LIMIT']
        token_data = verify_token(token, salt='invite_to_project', secret_key=flask.current_app.config['SECRET_KEY'], expiration=expiration_time_limit)
        if token_data is None:
            flask.flash(_('Invalid project group invitation token. Please request a new invitation.'), 'error')
            return flask.abort(403)
        if 'invitation_id' in token_data:
            if logic.projects.get_project_invitation(token_data['invitation_id']).accepted:
                flask.flash(_('This invitation token has already been used. Please request a new invitation.'), 'error')
                return flask.abort(403)
        if token_data.get('project_id', None) != project_id:
            return flask.abort(403)
        permissions = Permissions.from_value(token_data.get('permissions', Permissions.READ.value))
        if permissions == Permissions.NONE:
            flask.flash(_('Invalid permissions in project group invitation token. Please request a new invitation.'), 'error')
            return flask.abort(403)
        user_id = token_data.get('user_id', None)
        if user_id != flask_login.current_user.id:
            if user_id is not None:
                try:
                    invited_user = logic.users.get_user(user_id)
                    flask.flash(_('Please sign in as user "%(user_name)s" to accept this invitation.', user_name=invited_user.name), 'error')
                except logic.errors.UserDoesNotExistError:
                    pass
            return flask.abort(403)
        if not flask.current_app.config['DISABLE_SUBPROJECTS']:
            other_project_ids = token_data.get('other_project_ids', [])
            for notification in logic.notifications.get_notifications(user_id, unread_only=True):
                if notification.type == logic.notifications.NotificationType.INVITED_TO_PROJECT:
                    if notification.data['project_id'] == project_id:
                        logic.notifications.mark_notification_as_read(notification.id)
        else:
            other_project_ids = []
        try:
            logic.projects.add_user_to_project(project_id, user_id, permissions, other_project_ids=other_project_ids)
        except logic.errors.UserAlreadyMemberOfProjectError:
            flask.flash(_('You are already a member of this project group.'), 'error')
        except logic.errors.ProjectDoesNotExistError:
            pass
    allowed_language_ids = [
        language.id
        for language in get_languages(only_enabled_for_input=True)
    ]
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
    translations = []
    name_language_ids = []
    description_language_ids = []
    if Permissions.WRITE in user_permissions:
        edit_project_form = EditProjectForm()
        for name in project.name.items():
            lang_id = get_language_by_lang_code(name[0]).id
            name_language_ids.append(lang_id)
            item = {
                'language_id': lang_id,
                'lang_name': get_translated_text(get_language(lang_id).names),
                'name': name[1],
                'description': ''
            }
            translations.append(item)

        for description in project.description.items():
            if description[0] == '':
                continue
            lang_id = get_language_by_lang_code(description[0]).id
            description_language_ids.append(lang_id)
            for translation in translations:
                if lang_id == translation['language_id']:
                    translation['description'] = description[1]
                    break
            else:
                item = {
                    'language_id': lang_id,
                    'lang_name': get_translated_text(get_language(lang_id).names),
                    'name': '',
                    'description': description[1]
                }
                translations.append(item)
    else:
        edit_project_form = None
    show_edit_form = False
    english = get_language(Language.ENGLISH)

    project_member_user_ids_and_permissions = logic.projects.get_project_member_user_ids_and_permissions(project_id=project_id, include_groups=False)
    project_member_group_ids_and_permissions = logic.projects.get_project_member_group_ids_and_permissions(project_id=project_id)

    project_member_user_ids = list(project_member_user_ids_and_permissions.keys())
    project_member_user_ids.sort(key=lambda user_id: logic.users.get_user(user_id).name.lower())

    project_member_group_ids = list(project_member_group_ids_and_permissions.keys())
    project_member_group_ids.sort(key=lambda group_id: get_translated_text(logic.groups.get_group(group_id).name).lower())

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

    object = logic.projects.get_object_linked_to_project(project_id)
    if 'leave' in flask.request.form and Permissions.READ in user_permissions:
        if leave_project_form.validate_on_submit():
            try:
                logic.projects.remove_user_from_project(project_id=project_id, user_id=user_id)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash(_('This project group does not exist.'), 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.UserDoesNotExistError:
                return flask.abort(500)
            except logic.errors.UserNotMemberOfProjectError:
                flask.flash(_('You have already left the project group.'), 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.NoMemberWithGrantPermissionsForProjectError:
                flask.flash(_('You cannot leave this project group, because your are the only user with GRANT permissions.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            else:
                flask.flash(_('You have successfully left the project group.'), 'success')
                # create object log entry if this caused the deletion of a project linked to an object
                try:
                    logic.projects.get_project(project_id)
                except logic.errors.ProjectDoesNotExistError:
                    if object is not None:
                        logic.object_log.unlink_project(
                            flask_login.current_user.id,
                            object.id,
                            project_id,
                            project_deleted=True
                        )
                return flask.redirect(flask.url_for('.projects'))
    if 'delete' in flask.request.form and Permissions.GRANT in user_permissions:
        if delete_project_form.validate_on_submit():
            check_current_user_is_not_readonly()
            # create object log entry if deleting a project linked to an object
            if object is not None:
                logic.object_log.unlink_project(
                    flask_login.current_user.id,
                    object.id,
                    project_id,
                    project_deleted=True
                )
            try:
                logic.projects.delete_project(project_id=project_id)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash(_('This project group has already been deleted.'), 'success')
                return flask.redirect(flask.url_for('.projects'))
            else:
                flask.flash(_('You have successfully deleted the project group.'), 'success')
                return flask.redirect(flask.url_for('.projects'))
    if 'remove_member' in flask.request.form and Permissions.GRANT in user_permissions:
        if remove_project_member_form.validate_on_submit():
            check_current_user_is_not_readonly()
            member_id_str = flask.request.form['remove_member']
            try:
                member_id = int(member_id_str)
            except ValueError:
                flask.flash(_('The member ID was invalid. Please contact an administrator.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            if member_id == flask_login.current_user.id:
                flask.flash(_('You cannot remove yourself from a project group. Please press "Leave Project Group" instead.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            try:
                logic.projects.remove_user_from_project(project_id=project_id, user_id=member_id)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash(_('This project group does not exist.'), 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.UserDoesNotExistError:
                flask.flash(_('This user does not exist.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            except logic.errors.UserNotMemberOfProjectError:
                flask.flash(_('This user is not a member of this project group.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            except logic.errors.NoMemberWithGrantPermissionsForProjectError:
                flask.flash(_('You cannot remove this user from this project group, because they are the only user with GRANT permissions.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            else:
                flask.flash(_('You have successfully removed this user from the project group.'), 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    if 'remove_group' in flask.request.form and Permissions.GRANT in user_permissions:
        if remove_project_group_form.validate_on_submit():
            check_current_user_is_not_readonly()
            group_id_str = flask.request.form['remove_group']
            try:
                group_id = int(group_id_str)
            except ValueError:
                flask.flash(_('The basic group ID was invalid. Please contact an administrator.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            try:
                logic.projects.remove_group_from_project(project_id=project_id, group_id=group_id)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash(_('This project group does not exist.'), 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.GroupDoesNotExistError:
                flask.flash(_('This basic group does not exist.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            except logic.errors.GroupNotMemberOfProjectError:
                flask.flash(_('This basic group is not a member of this project group.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            except logic.errors.NoMemberWithGrantPermissionsForProjectError:
                flask.flash(_('You cannot remove this basic group from this project group, because they are the only basic group with GRANT permissions.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            else:
                flask.flash(_('You have successfully removed this basic group from the project group.'), 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    if 'edit' in flask.request.form and Permissions.WRITE in user_permissions:
        show_edit_form = True
        if edit_project_form.validate_on_submit():
            check_current_user_is_not_readonly()
            try:
                translations = json.loads(edit_project_form.translations.data)
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

                logic.projects.update_project(project_id, names, descriptions)
            except ValueError as e:
                flask.flash(str(e), 'error')
                edit_project_form.translations.errors.append(str(e))
            except logic.errors.ProjectDoesNotExistError:
                flask.flash(_('This project group does not exist.'), 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.ProjectAlreadyExistsError:
                edit_project_form.name.errors.append(_('A project group with this name already exists.'))
            except logic.errors.InvalidProjectNameError:
                edit_project_form.name.errors.append(_('This project group name is invalid.'))
            else:
                flask.flash(_('Project group information updated successfully.'), 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    if 'add_user' in flask.request.form and Permissions.GRANT in user_permissions:
        if invite_user_form.validate_on_submit():
            check_current_user_is_not_readonly()
            if not any(user.id == invite_user_form.user_id.data for user in invitable_user_list):
                flask.flash(_('You cannot add this user.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            permissions = Permissions.from_value(invite_user_form.permissions.data)
            if Permissions.READ not in permissions:
                flask.flash(_('Please select read permissions (or higher) for the invitation.'), 'error')
                return flask.redirect(flask.url_for('.projects'))
            try:
                other_project_ids = []
                for other_project_id_form in invite_user_form.other_project_ids:
                    try:
                        if other_project_id_form.add_user.data:
                            other_project_ids.append(int(other_project_id_form.project_id.data))
                    except (KeyError, ValueError):
                        pass
                logic.projects.invite_user_to_project(project_id, invite_user_form.user_id.data, flask_login.current_user.id, other_project_ids, permissions)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash(_('This project group does not exist.'), 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.UserDoesNotExistError:
                flask.flash(_('This user does not exist.'), 'error')
            except logic.errors.UserAlreadyMemberOfProjectError:
                flask.flash(_('This user is already a member of this project group.'), 'error')
            else:
                flask.flash(_('The user was successfully invited to the project group.'), 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    if 'add_group' in flask.request.form and Permissions.GRANT in user_permissions:
        if invite_group_form.validate_on_submit():
            check_current_user_is_not_readonly()
            if not any(group.id == invite_group_form.group_id.data for group in invitable_group_list):
                flask.flash(_('You cannot add this basic group.'), 'error')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
            try:
                logic.projects.add_group_to_project(project_id, invite_group_form.group_id.data, permissions=Permissions.READ)
            except logic.errors.ProjectDoesNotExistError:
                flask.flash(_('This project group does not exist.'), 'error')
                return flask.redirect(flask.url_for('.projects'))
            except logic.errors.GroupDoesNotExistError:
                flask.flash(_('This basic group does not exist.'), 'error')
            except logic.errors.GroupAlreadyMemberOfProjectError:
                flask.flash(_('This basic group is already a member of this project group.'), 'error')
            else:
                flask.flash(_('The basic group was successfully added to the project group.'), 'success')
                return flask.redirect(flask.url_for('.project', project_id=project_id))
    if not flask.current_app.config['DISABLE_SUBPROJECTS']:
        if 'remove_subproject' in flask.request.form and Permissions.GRANT in user_permissions:
            if remove_subproject_form is not None and remove_subproject_form.validate_on_submit():
                check_current_user_is_not_readonly()
                child_project_id = remove_subproject_form.child_project_id.data
                if child_project_id not in child_project_ids:
                    flask.flash(_('Project group #%(child_project_id)s is not a child of this project group.', child_project_id=int(child_project_id)), 'error')
                else:
                    logic.projects.delete_subproject_relationship(project_id, child_project_id)
                    flask.flash(_('The child project group was successfully removed from this project group.'), 'success')
                    return flask.redirect(flask.url_for('.project', project_id=project_id))
        if 'add_subproject' in flask.request.form and Permissions.GRANT in user_permissions:
            if add_subproject_form is not None and add_subproject_form.validate_on_submit():
                check_current_user_is_not_readonly()
                child_project_id = add_subproject_form.child_project_id.data
                if child_project_id not in addable_project_ids:
                    flask.flash(_('Project group #%(child_project_id)s cannot become a child of this project group.', child_project_id=int(child_project_id)), 'error')
                else:
                    logic.projects.create_subproject_relationship(project_id, child_project_id, child_can_add_users_to_parent=add_subproject_form.child_can_add_users_to_parent.data)
                    flask.flash(_('The child project group was successfully added to this project group.'), 'success')
                    return flask.redirect(flask.url_for('.project', project_id=project_id))
    object_id = object.id if object is not None else None
    object_action = None
    object_link_form = None
    linkable_objects = []
    linkable_action_ids = []
    already_linked_object_ids = []
    if Permissions.GRANT in user_permissions and not flask_login.current_user.is_readonly:
        object_link_form = ObjectLinkForm()
        if object is None:
            already_linked_object_ids = [link[1] for link in logic.projects.get_project_object_links()]
            for action_type in logic.actions.get_action_types():
                if action_type.enable_project_link:
                    linkable_action_ids.extend([
                        action.id
                        for action in logic.actions.get_actions(action_type.id)
                    ])
                    if not flask.current_app.config['LOAD_OBJECTS_IN_BACKGROUND']:
                        for object_info in logic.object_permissions.get_object_info_with_permissions(user_id, Permissions.GRANT, action_type_id=action_type.id):
                            if object_info.object_id not in already_linked_object_ids:
                                linkable_objects.append((object_info.object_id, get_translated_text(object_info.name_json)))
    if object is not None:
        object_permissions = logic.object_permissions.get_user_object_permissions(object.object_id, flask_login.current_user.id)
        if Permissions.READ in object_permissions:
            object_action = logic.actions.get_action(object.action_id)
        else:
            object = None
    return flask.render_template(
        'projects/project.html',
        ENGLISH=english,
        translations=translations,
        languages=get_languages(only_enabled_for_input=True),
        name_language_ids=name_language_ids,
        description_language_ids=description_language_ids,
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
        object=object,
        object_id=object_id,
        object_link_form=object_link_form,
        linkable_action_ids=linkable_action_ids,
        already_linked_object_ids=already_linked_object_ids,
        linkable_objects=linkable_objects,
        object_action=object_action,
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
        user_may_edit_permissions=Permissions.GRANT in user_permissions,
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
    show_create_form = False
    if 'create' in flask.request.form:
        allowed_language_ids = [
            language.id
            for language in get_languages(only_enabled_for_input=True)
        ]
        show_create_form = True
        if create_project_form.validate_on_submit():
            check_current_user_is_not_readonly()
            if flask_login.current_user.is_admin or not flask.current_app.config['ONLY_ADMINS_CAN_CREATE_PROJECTS']:
                try:
                    translations = json.loads(create_project_form.translations.data)
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

                    project_id = logic.projects.create_project(names, descriptions, flask_login.current_user.id).id
                except ValueError as e:
                    flask.flash(str(e), 'error')
                    create_project_form.translations.errors.append(str(e))
                except logic.errors.ProjectAlreadyExistsError:
                    create_project_form.translations.errors.append(_('A project group with this name already exists.'))
                except logic.errors.InvalidProjectNameError:
                    create_project_form.translations.errors.append(_('This project group name is invalid.'))
                else:
                    flask.flash(_('The project group has been created successfully.'), 'success')
                    return flask.redirect(flask.url_for('.project', project_id=project_id))
            else:
                create_project_form.translations.errors.append(_('Only administrators can create project groups.'))

    projects_by_id = {
        project.id: project
        for project in projects
    }
    project_id_hierarchy_list = logic.projects.get_project_id_hierarchy_list(list(projects_by_id))
    english = get_language(Language.ENGLISH)
    return flask.render_template(
        "projects/projects.html",
        create_project_form=create_project_form,
        show_create_form=show_create_form,
        Permissions=logic.projects.Permissions,
        projects_by_id=projects_by_id,
        project_id_hierarchy_list=project_id_hierarchy_list,
        languages=get_languages(only_enabled_for_input=True),
        ENGLISH=english
    )


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
    return flask.render_template('projects/project_permissions.html', project=project, user_permissions=user_permissions, group_permissions=group_permissions, project_permissions=project_permissions, get_user=logic.users.get_user, get_group=logic.groups.get_group, Permissions=Permissions, form=edit_user_permissions_form)


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
        flask.flash(_("Successfully updated project group permissions."), 'success')
    else:
        flask.flash(_("A problem occurred while changing the project group permissions. Please try again."), 'error')
    try:
        logic.projects.get_project(project_id)
    except logic.errors.ProjectDoesNotExistError:
        return flask.redirect(flask.url_for('.projects'))
    return flask.redirect(flask.url_for('.project_permissions', project_id=project_id))


@frontend.route('/projects/<int:project_id>/object_link', methods=['POST'])
@flask_login.login_required
def link_object(project_id):
    check_current_user_is_not_readonly()
    object_link_form = ObjectLinkForm()
    if not object_link_form.validate_on_submit():
        flask.flash(_("Missing or invalid object ID."), 'error')
        return flask.redirect(flask.url_for('.project', project_id=project_id))
    object_id = object_link_form.object_id.data
    try:
        if Permissions.GRANT not in logic.projects.get_user_project_permissions(project_id, flask_login.current_user.id, True):
            flask.flash(_("You do not have GRANT permissions for this project group."), 'error')
            return flask.redirect(flask.url_for('.project', project_id=project_id))
        if Permissions.GRANT not in logic.object_permissions.get_user_object_permissions(object_id, flask_login.current_user.id):
            flask.flash(_("You do not have GRANT permissions for this object."), 'error')
            return flask.redirect(flask.url_for('.project', project_id=project_id))
        logic.projects.link_project_and_object(project_id, object_id, flask_login.current_user.id)
    except logic.errors.ProjectObjectLinkAlreadyExistsError:
        flask.flash(_("Project group is already linked to an object or object is already linked to a project group."), 'error')
        return flask.redirect(flask.url_for('.project', project_id=project_id))
    except logic.errors.ProjectDoesNotExistError:
        flask.flash(_("Project group does not exist."), 'error')
        return flask.redirect(flask.url_for('.project', project_id=project_id))
    except logic.errors.ObjectDoesNotExistError:
        flask.flash(_("Object does not exist."), 'error')
        return flask.redirect(flask.url_for('.project', project_id=project_id))
    flask.flash(_("Successfully linked the object to a project group."), 'success')
    return flask.redirect(flask.url_for('.project', project_id=project_id))


@frontend.route('/projects/<int:project_id>/object_unlink', methods=['POST'])
@flask_login.login_required
def unlink_object(project_id):
    check_current_user_is_not_readonly()
    object_link_form = ObjectLinkForm()
    if not object_link_form.validate_on_submit():
        flask.flash(_("Missing or invalid object ID."), 'error')
        return flask.redirect(flask.url_for('.project', project_id=project_id))
    object_id = object_link_form.object_id.data
    try:
        if Permissions.GRANT not in logic.projects.get_user_project_permissions(project_id, flask_login.current_user.id, True):
            flask.flash(_("You do not have GRANT permissions for this project group."), 'error')
            return flask.redirect(flask.url_for('.project', project_id=project_id))
        logic.projects.unlink_project_and_object(project_id, object_id, flask_login.current_user.id)
    except logic.errors.ProjectObjectLinkDoesNotExistsError:
        flask.flash(_("No link exists between this object and project group."), 'error')
        return flask.redirect(flask.url_for('.project', project_id=project_id))
    except logic.errors.ProjectDoesNotExistError:
        flask.flash(_("Project group does not exist."), 'error')
        return flask.redirect(flask.url_for('.project', project_id=project_id))
    except logic.errors.ObjectDoesNotExistError:
        flask.flash(_("Object does not exist."), 'error')
        return flask.redirect(flask.url_for('.project', project_id=project_id))
    flask.flash(_("Successfully unlinked the object and project group."), 'success')
    return flask.redirect(flask.url_for('.project', project_id=project_id))
