# coding: utf-8
"""

"""
import typing
import json

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SelectMultipleField, BooleanField
from wtforms.validators import DataRequired

from . import frontend
from .permission_forms import set_up_permissions_forms, handle_permission_forms
from .. import logic
from ..logic import errors
from ..logic.components import get_component
from ..logic.locations import Location, create_location, get_location, get_locations_tree, update_location, get_object_location_assignment, confirm_object_responsibility, decline_object_responsibility, get_object_location_assignments
from ..logic.location_log import get_log_entries_for_location, LocationLogEntryType
from ..logic.languages import Language, get_language, get_languages, get_language_by_lang_code
from ..logic.security_tokens import verify_token
from ..logic.notifications import mark_notification_for_being_assigned_as_responsible_user_as_read, create_notification_for_a_declined_responsibility_assignment
from ..logic.location_permissions import get_user_location_permissions, get_location_permissions_for_all_users, get_location_permissions_for_users, get_location_permissions_for_groups, get_location_permissions_for_projects, set_location_permissions_for_all_users, set_user_location_permissions
from ..logic.users import get_user, get_users
from ..logic.groups import get_group
from ..logic.projects import get_project
from .utils import check_current_user_is_not_readonly, get_location_name, get_groups_form_data
from ..logic.utils import get_translated_text
from ..models import Permissions


class LocationForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])
    parent_location = SelectField()
    is_public = BooleanField(default=True)
    type = SelectField(validators=[DataRequired()])
    responsible_users = SelectMultipleField()
    is_hidden = BooleanField(default=False)


@frontend.route('/locations/')
@flask_login.login_required
def locations():
    locations_map, locations_tree = get_locations_tree()
    permissions_by_id = {
        location_id: get_user_location_permissions(location_id, flask_login.current_user.id)
        for location_id in locations_map
    }
    filtered_locations_tree = _filter_location_tree_for_read_permissions(locations_tree, permissions_by_id)
    has_hidden_locations = filtered_locations_tree != locations_tree
    return flask.render_template(
        'locations/locations.html',
        locations_map=locations_map,
        locations_tree=filtered_locations_tree,
        sort_location_ids_by_name=_sort_location_ids_by_name,
        has_hidden_locations=has_hidden_locations,
        permissions_by_id=permissions_by_id,
        Permissions=Permissions,
        get_component=get_component,
        get_user=get_user
    )


_LocationTree = typing.Dict[int, '_LocationTree']


def _filter_location_tree_for_read_permissions(
        location_tree: _LocationTree,
        permissions_by_id: typing.Dict[int, Permissions]
) -> _LocationTree:
    """
    Remove all location IDs from a location tree that can neither be read, nor
    have child locations that can be read.
    """
    filtered_locations_tree: _LocationTree = {}
    for location_id in location_tree:
        sub_location_tree = location_tree[location_id]
        if sub_location_tree:
            sub_location_tree = _filter_location_tree_for_read_permissions(sub_location_tree, permissions_by_id)
        if Permissions.READ in permissions_by_id[location_id] or sub_location_tree:
            filtered_locations_tree[location_id] = sub_location_tree
    return filtered_locations_tree


@frontend.route('/locations/<int:location_id>', methods=['GET', 'POST'])
@flask_login.login_required
def location(location_id):
    try:
        location = get_location(location_id)
    except errors.LocationDoesNotExistError:
        return flask.abort(404)
    permissions = get_user_location_permissions(location_id, flask_login.current_user.id)
    mode = flask.request.args.get('mode', None)
    if mode == 'edit':
        if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask_login.current_user.is_admin:
            flask.flash(_('Only administrators can edit locations.'), 'error')
            return flask.abort(403)
        if location.fed_id is not None:
            flask.flash(_('Editing imported locations is not yet supported.'), 'error')
            return flask.abort(403)
        check_current_user_is_not_readonly()
        if Permissions.WRITE not in permissions:
            flask.flash(_('You do not have permissions to edit this location.'), 'error')
            return flask.abort(403)
        return _show_location_form(location, None, Permissions.GRANT in permissions)
    if Permissions.READ not in permissions:
        flask.flash(_('You do not have permissions to view this location.'), 'error')
        return flask.abort(403)
    locations_map, locations_tree = get_locations_tree()
    ancestors = []
    parent_location = location
    while parent_location.parent_location_id is not None:
        parent_location = get_location(parent_location.parent_location_id)
        ancestors.insert(0, parent_location)
    for ancestor in ancestors:
        locations_tree = locations_tree[ancestor.id]
    locations_tree = locations_tree[location_id]
    permissions_by_id = {
        location_id: get_user_location_permissions(location_id, flask_login.current_user.id)
        for location_id in locations_map
    }
    descendent_location_ids = logic.locations.get_descendent_location_ids(locations_tree)
    return flask.render_template(
        'locations/location.html',
        locations_map=locations_map,
        locations_tree=locations_tree,
        descendent_location_ids=descendent_location_ids,
        location=location,
        ancestors=ancestors,
        sort_location_ids_by_name=_sort_location_ids_by_name,
        permissions=permissions,
        permissions_by_id=permissions_by_id,
        Permissions=Permissions,
        location_log_entries=get_log_entries_for_location(location.id, flask_login.current_user.id) if location.type.show_location_log else None,
        LocationLogEntryType=LocationLogEntryType,
        get_component=get_component,
        get_user=get_user
    )


@frontend.route('/locations/<int:location_id>/permissions', methods=['GET', 'POST'])
@flask_login.login_required
def location_permissions(location_id):
    try:
        location = get_location(location_id)
    except errors.LocationDoesNotExistError:
        return flask.abort(404)
    permissions = get_user_location_permissions(location_id, flask_login.current_user.id)
    if Permissions.READ not in permissions:
        return flask.abort(403)
    user_may_edit = Permissions.GRANT in permissions

    all_user_permissions = get_location_permissions_for_all_users(location_id)
    user_permissions = get_location_permissions_for_users(location_id)
    group_permissions = get_location_permissions_for_groups(location_id)
    project_permissions = get_location_permissions_for_projects(location_id)
    if user_may_edit:
        (
            add_user_permissions_form,
            add_group_permissions_form,
            add_project_permissions_form,
            permissions_form
        ) = set_up_permissions_forms(
            resource_permissions=logic.location_permissions.location_permissions,
            resource_id=location_id,
            existing_all_user_permissions=all_user_permissions,
            existing_anonymous_user_permissions=None,
            existing_user_permissions=user_permissions,
            existing_group_permissions=group_permissions,
            existing_project_permissions=project_permissions
        )
        permissions_form.all_user_permissions.choices = [
            (p.name.lower(), p)
            for p in [
                Permissions.NONE, Permissions.READ, Permissions.WRITE
            ]
        ]

        users = logic.users.get_users(exclude_hidden=not flask_login.current_user.is_admin, exclude_fed=True)
        users = [user for user in users if user.id not in user_permissions]
        users.sort(key=lambda user: user.id)

        show_groups_form, groups_treepicker_info = get_groups_form_data(
            basic_group_filter=lambda group: group.id not in group_permissions
        )

        show_projects_form, projects_treepicker_info = get_groups_form_data(
            project_group_filter=lambda group: group.id not in project_permissions
        )
    else:
        permissions_form = None
        users = None
        add_user_permissions_form = None
        add_group_permissions_form = None
        add_project_permissions_form = None
        show_groups_form = False
        groups_treepicker_info = None
        show_projects_form = False
        projects_treepicker_info = None

    if flask.request.method.lower() == 'post':
        if not user_may_edit:
            flask.flash(_('You need GRANT permissions to edit the permissions for this location.'), 'error')
        else:
            if handle_permission_forms(
                logic.location_permissions.location_permissions,
                location_id,
                add_user_permissions_form,
                add_group_permissions_form,
                add_project_permissions_form,
                permissions_form,
                user_permissions,
                group_permissions,
                project_permissions
            ):
                flask.flash(_('Successfully updated location permissions.'), 'success')
            else:
                flask.flash(_('Failed to update location permissions.'), 'error')
        return flask.redirect(flask.url_for('.location_permissions', location_id=location_id))

    return flask.render_template(
        'locations/location_permissions.html',
        user_may_edit=user_may_edit,
        location=location,
        Permissions=Permissions,
        project_permissions=project_permissions,
        group_permissions=group_permissions,
        user_permissions=user_permissions,
        all_user_permissions=all_user_permissions,
        form=permissions_form,
        users=users,
        add_user_permissions_form=add_user_permissions_form,
        add_group_permissions_form=add_group_permissions_form,
        add_project_permissions_form=add_project_permissions_form,
        show_groups_form=show_groups_form,
        groups_treepicker_info=groups_treepicker_info,
        show_projects_form=show_projects_form,
        projects_treepicker_info=projects_treepicker_info,
        get_user=get_user,
        get_group=get_group,
        get_project=get_project,
    )


@frontend.route('/locations/new/', methods=['GET', 'POST'])
@flask_login.login_required
def new_location():
    if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask_login.current_user.is_admin:
        flask.flash(_('Only administrators can create locations.'), 'error')
        return flask.abort(403)
    check_current_user_is_not_readonly()
    parent_location = None
    parent_location_id = flask.request.args.get('parent_location_id', None)
    if parent_location_id is not None:
        try:
            parent_location_id = int(parent_location_id)
        except ValueError:
            parent_location_id = None
    if parent_location_id:
        try:
            parent_location = get_location(parent_location_id)
        except errors.LocationDoesNotExistError:
            flask.flash(_('The requested parent location does not exist.'), 'error')
        if parent_location is not None:
            parent_location_permissions = get_user_location_permissions(parent_location_id, flask_login.current_user.id)
            if Permissions.WRITE not in parent_location_permissions:
                flask.flash(_('You do not have the required permissions for the requested parent location.'), 'error')
                parent_location = None
    return _show_location_form(None, parent_location, True)


def _handle_object_location_assignment(
        token_salt: str,
        missing_token_text: str,
        invalid_token_text: str,
        success_text: str,
        callback: typing.Callable[[int], None]
) -> typing.Any:
    token = flask.request.args.get('t', None)
    if token is None:
        flask.flash(missing_token_text, 'error')
        return flask.redirect(flask.url_for('.index'))
    object_location_assignment_id = verify_token(
        token=token,
        salt=token_salt,
        secret_key=flask.current_app.config['SECRET_KEY'],
        expiration=None
    )
    if object_location_assignment_id is None:
        flask.flash(invalid_token_text, 'error')
        return flask.redirect(flask.url_for('.index'))
    try:
        object_location_assignment = get_object_location_assignment(object_location_assignment_id)
    except errors.ObjectLocationAssignmentDoesNotExistError:
        flask.flash(_('This responsibility assignment does not exist.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    if object_location_assignment.responsible_user_id != flask_login.current_user.id:
        flask.flash(_('This responsibility assignment belongs to another user.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    if object_location_assignment.confirmed:
        flask.flash(_('This responsibility assignment has already been confirmed.'), 'success')
    elif object_location_assignment.declined:
        flask.flash(_('This responsibility assignment has already been declined.'), 'success')
    else:
        callback(object_location_assignment_id)
        flask.flash(success_text, 'success')
        mark_notification_for_being_assigned_as_responsible_user_as_read(
            user_id=flask_login.current_user.id,
            object_location_assignment_id=object_location_assignment_id
        )
    return flask.redirect(flask.url_for('.object', object_id=object_location_assignment.object_id))


@frontend.route('/locations/confirm_responsibility')
@flask_login.login_required
def accept_responsibility_for_object():
    return _handle_object_location_assignment(
        token_salt='confirm_responsibility',
        missing_token_text=_('The confirmation token is missing.'),
        invalid_token_text=_('The confirmation token is invalid.'),
        success_text=_('You have successfully confirmed this responsibility assignment.'),
        callback=confirm_object_responsibility
    )


@frontend.route('/locations/decline_responsibility')
@flask_login.login_required
def decline_responsibility_for_object():
    def _callback(object_location_assignment_id: int) -> None:
        decline_object_responsibility(object_location_assignment_id)
        object_location_assignment = get_object_location_assignment(object_location_assignment_id)
        if object_location_assignment.user_id != object_location_assignment.responsible_user_id:
            # notify the assigning user that the assignment was declined
            create_notification_for_a_declined_responsibility_assignment(object_location_assignment.user_id, object_location_assignment_id)
        all_object_location_assignments = get_object_location_assignments(object_id=object_location_assignment.object_id)
        all_object_location_assignments.sort(key=lambda assignment: (assignment.utc_datetime, assignment.id), reverse=True)
        for assignment in all_object_location_assignments:
            if assignment.confirmed and assignment.responsible_user_id is not None:
                current_responsible_user_id = assignment.responsible_user_id
                break
        else:
            current_responsible_user_id = None
        if current_responsible_user_id not in (None, object_location_assignment.responsible_user_id, object_location_assignment.user_id):
            # notify the currently responsible user that the assignment was declined
            create_notification_for_a_declined_responsibility_assignment(current_responsible_user_id, object_location_assignment_id)
    return _handle_object_location_assignment(
        token_salt='decline_responsibility',
        missing_token_text=_('The declination token is missing.'),
        invalid_token_text=_('The declination token is invalid.'),
        success_text=_('You have successfully declined this responsibility assignment.'),
        callback=_callback
    )


def _sort_location_ids_by_name(location_ids: typing.Iterable[int], location_map: typing.Dict[int, Location]) -> typing.List[int]:
    location_ids = list(location_ids)
    location_ids.sort(key=lambda location_id: get_location_name(location_map[location_id]))
    return location_ids


def _show_location_form(location: typing.Optional[Location], parent_location: typing.Optional[Location], has_grant_permissions):
    english = get_language(Language.ENGLISH)
    name_language_ids = []
    description_language_ids = []
    location_translations = []
    if location is not None:
        submit_text = "Save"
        may_change_hidden = flask_login.current_user.is_admin
    else:
        submit_text = "Create"
        may_change_hidden = False

    location_types = logic.locations.get_location_types()

    locations_map, locations_tree = get_locations_tree()
    invalid_location_ids = []
    if location is not None:
        invalid_location_ids.append(location.id)
        ancestor_ids = []
        _parent_location = location
        while _parent_location.parent_location_id is not None:
            _parent_location = get_location(_parent_location.parent_location_id)
            ancestor_ids.insert(0, _parent_location.id)
        locations_subtree = locations_tree
        for ancestor_id in ancestor_ids:
            locations_subtree = locations_subtree[ancestor_id]
        locations_subtree = locations_subtree[location.id]
        unhandled_descendent_ids_and_subtrees = [(descendent_id, locations_subtree) for descendent_id in locations_subtree]
        while unhandled_descendent_ids_and_subtrees:
            descendent_id, locations_subtree = unhandled_descendent_ids_and_subtrees.pop(0)
            invalid_location_ids.append(descendent_id)
            locations_subtree = locations_subtree[descendent_id]
            for descendent_id in locations_subtree:
                unhandled_descendent_ids_and_subtrees.append((descendent_id, locations_subtree))

    for location_id in locations_map:
        if location_id not in invalid_location_ids:
            if Permissions.WRITE not in get_user_location_permissions(location_id, flask_login.current_user.id):
                invalid_location_ids.append(location_id)

    location_form = LocationForm()
    location_form.parent_location.choices = [('-1', '-')] + [
        (str(location_id), locations_map[location_id].name)
        for location_id in locations_map
        if location_id not in invalid_location_ids and locations_map[location_id].type.enable_sub_locations
    ]
    if has_grant_permissions:
        users = [
            user
            for user in get_users()
            if (user.fed_id is None and not user.is_hidden) or (location is not None and user in location.responsible_users)
        ]
        location_form.responsible_users.choices = [
            (str(user.id), user.get_name())
            for user in users
        ]
    else:
        location_form.responsible_users.choices = []
    # filter permitted location types
    location_types = [
        location_type
        for location_type in location_types
        if not location_type.admin_only or flask_login.current_user.is_admin or (location is not None and location.type_id == location_type.id)
    ]
    location_form.type.choices = [
        (str(location_type.id), location_type.name)
        for location_type in location_types
    ]
    location_type_is_fed = {
        str(location_type.id): location_type.fed_id is not None
        for location_type in location_types
    }
    location_type_enable_parent_location = {
        str(location_type.id): location_type.enable_parent_location
        for location_type in location_types
    }
    location_type_enable_responsible_users = {
        str(location_type.id): location_type.enable_responsible_users
        for location_type in location_types
    }
    location_is_fed = {
        str(loc.id): loc.fed_id is not None
        for loc in locations_map.values()
        if loc.id not in invalid_location_ids
    }
    previous_parent_location_is_invalid = False
    if not location_form.is_submitted():
        if location is not None and location.parent_location_id:
            location_form.parent_location.data = str(location.parent_location_id)
        elif parent_location is not None:
            location_form.parent_location.data = str(parent_location.id)
        else:
            location_form.parent_location.data = str(-1)
        if location_form.parent_location.data not in [
            value
            for value, label in location_form.parent_location.choices
        ]:
            previous_parent_location_is_invalid = True
            location_form.parent_location.data = str(-1)
        if location is not None:
            location_form.type.data = str(location.type_id)
        else:
            # default to the generic location type
            location_form.type.data = str(logic.locations.LocationType.LOCATION)
        if location is not None and has_grant_permissions:
            location_form.responsible_users.data = [str(user.id) for user in location.responsible_users]
        else:
            location_form.responsible_users.data = []
        if location is not None:
            location_form.is_hidden.data = location.is_hidden
        else:
            location_form.is_hidden.data = False

    form_is_valid = False
    if location_form.validate_on_submit():
        form_is_valid = True

    if location is not None:
        name_language_ids = []
        description_language_ids = []
        for language_code, name in location.name.items():
            language = get_language_by_lang_code(language_code)
            if not language.enabled_for_input:
                continue
            name_language_ids.append(language.id)
            location_translations.append({
                'language_id': language.id,
                'lang_name': get_translated_text(language.names),
                'name': name,
                'description': ''
            })

        for language_code, description in location.description.items():
            language = get_language_by_lang_code(language_code)
            if not language.enabled_for_input:
                continue
            description_language_ids.append(language.id)
            for translation in location_translations:
                if language.id == translation['language_id']:
                    translation['description'] = description
                    break
            else:
                location_translations.append({
                    'language_id': language.id,
                    'lang_name': get_translated_text(language.names),
                    'name': '',
                    'description': description
                })

    if form_is_valid:
        try:
            translations = json.loads(location_form.translations.data)
            names = {}
            descriptions = {}
            if not translations:
                raise ValueError(_('Please enter at least an english name.'))
            for translation in translations:
                name = translation['name'].strip()
                description = translation['description'].strip()
                language_id = int(translation['language_id'])
                if language_id == Language.ENGLISH:
                    if name == '':
                        raise ValueError(_('Please enter at least an english name.'))
                elif name == '' and description == '':
                    continue
                language = get_language(language_id)
                if language.enabled_for_input:
                    names[language.lang_code] = name
                    descriptions[language.lang_code] = description
                else:
                    location_form.translations.errors.append(_('One of these languages is not supported.'))
        except errors.LanguageDoesNotExistError:
            location_form.translations.errors.append(_('One of these languages is not supported.'))
        except Exception as e:
            location_form.translations.errors.append(str(e))
        form_is_valid = not location_form.translations.errors
    if form_is_valid:
        try:
            parent_location_id = int(location_form.parent_location.data)
        except ValueError:
            parent_location_id = None
        if parent_location_id == -1:
            parent_location_id = None
        if parent_location_id is not None:
            try:
                parent_location = logic.locations.get_location(parent_location_id)
            except errors.LocationDoesNotExistError:
                parent_location_id = None
                parent_location = None
                form_is_valid = False
        else:
            parent_location = None
    if form_is_valid:
        try:
            location_type_id = int(location_form.type.data)
        except ValueError:
            location_type_id = None
        if location_type_id is not None:
            try:
                location_type = logic.locations.get_location_type(location_type_id)
            except errors.LocationTypeDoesNotExistError:
                location_type_id = None
                location_type = None
                form_is_valid = False
        else:
            location_type = None
            form_is_valid = False
            location_form.type.errors.append(_('Please select a valid location type.'))
    responsible_user_ids = []
    if form_is_valid and has_grant_permissions:
        valid_user_ids = [
            user.id
            for user in users
        ]
        for user_id in location_form.responsible_users.data:
            try:
                user_id = int(user_id)
            except ValueError:
                continue
            if user_id not in responsible_user_ids and user_id in valid_user_ids:
                responsible_user_ids.append(user_id)
    if form_is_valid:
        if location_type.admin_only and not flask_login.current_user.is_admin and location is None:
            location_form.type.errors.append(_('Only administrators may create locations of this type.'))
            form_is_valid = False
        if parent_location is not None:
            if not location_type.enable_parent_location:
                location_form.parent_location.errors.append(_('Locations of this type may not have a parent location.'))
                form_is_valid = False
            if not parent_location.type.enable_sub_locations:
                location_form.parent_location.errors.append(_('This location may not have sub locations.'))
                form_is_valid = False
        if not location_type.enable_responsible_users and responsible_user_ids:
            location_form.responsible_users.errors.append(_('This location may not have responsible users.'))
            form_is_valid = False
    if form_is_valid:
        if location is None:
            location = create_location(
                name=names,
                description=descriptions,
                parent_location_id=parent_location_id,
                user_id=flask_login.current_user.id,
                type_id=location_type_id
            )
            if location_form.is_public.data:
                set_location_permissions_for_all_users(location.id, Permissions.WRITE)
            else:
                set_user_location_permissions(location.id, flask_login.current_user.id, Permissions.GRANT)
            flask.flash(_('The location was created successfully.'), 'success')
        else:
            update_location(
                location_id=location.id,
                name=names,
                description=descriptions,
                parent_location_id=parent_location_id,
                user_id=flask_login.current_user.id,
                type_id=location_type_id,
                is_hidden=location_form.is_hidden.data if may_change_hidden else location.is_hidden,
            )
            flask.flash(_('The location was updated successfully.'), 'success')
        if has_grant_permissions:
            logic.locations.set_location_responsible_users(location.id, responsible_user_ids)
        return flask.redirect(flask.url_for('.location', location_id=location.id))
    if english.id not in description_language_ids:
        description_language_ids.append(english.id)
    return flask.render_template(
        'locations/location_form.html',
        location=location,
        location_types=location_types,
        location_form=location_form,
        submit_text=submit_text,
        ENGLISH=english,
        languages=get_languages(only_enabled_for_input=True),
        translations=location_translations,
        name_language_ids=name_language_ids,
        description_language_ids=description_language_ids,
        location_is_fed=location_is_fed,
        location_type_is_fed=location_type_is_fed,
        location_type_enable_parent_location=location_type_enable_parent_location,
        location_type_enable_responsible_users=location_type_enable_responsible_users,
        previous_parent_location_is_invalid=previous_parent_location_is_invalid,
        has_grant_permissions=has_grant_permissions,
        may_change_hidden=may_change_hidden,
    )
