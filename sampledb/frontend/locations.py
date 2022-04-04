# coding: utf-8
"""

"""

import typing
import json

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField
from wtforms.validators import DataRequired

from . import frontend
from .permission_forms import set_up_permissions_forms, handle_permission_forms
from .. import logic
from ..logic import errors
from ..logic.components import get_component
from ..logic.locations import Location, create_location, get_location, get_locations_tree, update_location, get_object_location_assignment, confirm_object_responsibility
from ..logic.languages import Language, get_language, get_languages, get_language_by_lang_code
from ..logic.security_tokens import verify_token
from ..logic.notifications import mark_notification_for_being_assigned_as_responsible_user_as_read
from ..logic.location_permissions import get_user_location_permissions, get_location_permissions_for_all_users, get_location_permissions_for_users, get_location_permissions_for_groups, get_location_permissions_for_projects, set_location_permissions_for_all_users, set_user_location_permissions
from ..logic.users import get_user
from ..logic.groups import get_group
from ..logic.projects import get_project
from .utils import check_current_user_is_not_readonly, get_location_name
from ..logic.utils import get_translated_text
from ..models import Permissions


class LocationForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])
    parent_location = SelectField()
    is_public = BooleanField(default=True)


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
        get_component=get_component
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
        return _show_location_form(location, None)
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
    return flask.render_template(
        'locations/location.html',
        locations_map=locations_map,
        locations_tree=locations_tree,
        location=location,
        ancestors=ancestors,
        sort_location_ids_by_name=_sort_location_ids_by_name,
        permissions=permissions,
        permissions_by_id=permissions_by_id,
        Permissions=Permissions,
        get_component=get_component
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
            logic.location_permissions.location_permissions,
            location_id,
            all_user_permissions,
            user_permissions,
            group_permissions,
            project_permissions
        )
        permissions_form.all_user_permissions.choices = [
            (p.name.lower(), p)
            for p in [
                Permissions.NONE, Permissions.READ, Permissions.WRITE
            ]
        ]

        users = logic.users.get_users(exclude_hidden=True, exclude_fed=True)
        users = [user for user in users if user.id not in user_permissions]
        users.sort(key=lambda user: user.id)
        groups = logic.groups.get_groups()
        groups = [group for group in groups if group.id not in group_permissions]
        groups.sort(key=lambda group: group.id)
        projects = logic.projects.get_projects()
        projects = [project for project in projects if project.id not in project_permissions]
        projects.sort(key=lambda project: project.id)

        projects_by_id = {
            project.id: project
            for project in projects
        }
        if not flask.current_app.config['DISABLE_SUBPROJECTS']:
            project_id_hierarchy_list = logic.projects.get_project_id_hierarchy_list(list(projects_by_id))
            project_id_hierarchy_list = [
                (level, project_id, project_id not in project_permissions)
                for level, project_id in project_id_hierarchy_list
            ]
        else:
            project_id_hierarchy_list = [
                (0, project.id, project.id not in project_permissions)
                for project in sorted(projects, key=lambda project: project.id)
            ]
        show_projects_form = any(
            enabled
            for level, project_id, enabled in project_id_hierarchy_list
        )
    else:
        permissions_form = None
        users = None
        add_user_permissions_form = None
        groups = None
        add_group_permissions_form = None
        projects = None
        add_project_permissions_form = None
        projects_by_id = None
        project_id_hierarchy_list = None
        show_projects_form = False

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
        groups=groups,
        add_group_permissions_form=add_group_permissions_form,
        projects=projects,
        add_project_permissions_form=add_project_permissions_form,
        projects_by_id=projects_by_id,
        project_id_hierarchy_list=project_id_hierarchy_list,
        show_projects_form=show_projects_form,
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
    return _show_location_form(None, parent_location)


@frontend.route('/locations/confirm_responsibility')
@flask_login.login_required
def accept_responsibility_for_object():
    token = flask.request.args.get('t', None)
    if token is None:
        flask.flash(_('The confirmation token is missing.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    object_location_assignment_id = verify_token(token, salt='confirm_responsibility', secret_key=flask.current_app.config['SECRET_KEY'], expiration=None)
    if object_location_assignment_id is None:
        flask.flash(_('The confirmation token is invalid.'), 'error')
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
    else:
        confirm_object_responsibility(object_location_assignment_id)
        flask.flash(_('You have successfully confirmed this responsibility assignment.'), 'success')
        mark_notification_for_being_assigned_as_responsible_user_as_read(
            user_id=flask_login.current_user.id,
            object_location_assignment_id=object_location_assignment_id
        )
    return flask.redirect(flask.url_for('.object', object_id=object_location_assignment.object_id))


def _sort_location_ids_by_name(location_ids: typing.Iterable[int], location_map: typing.Dict[int, Location]) -> typing.List[int]:
    location_ids = list(location_ids)
    location_ids.sort(key=lambda location_id: get_location_name(location_map[location_id]))
    return location_ids


def _show_location_form(location: typing.Optional[Location], parent_location: typing.Optional[Location]):
    english = get_language(Language.ENGLISH)
    name_language_ids = []
    description_language_ids = []
    location_translations = []
    if location is not None:
        submit_text = "Save"
    elif parent_location is not None:
        submit_text = "Create"
    else:
        submit_text = "Create"

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
        if location_id not in invalid_location_ids
    ]
    location_is_fed = {str(loc.id): loc.fed_id is not None for loc in locations_map.values() if loc.id not in invalid_location_ids}
    if not location_form.is_submitted():
        if location is not None and location.parent_location_id:
            location_form.parent_location.data = str(location.parent_location_id)
        elif parent_location is not None:
            location_form.parent_location.data = str(parent_location.id)
        else:
            location_form.parent_location.data = str(-1)

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
            if not translations:
                raise ValueError(_('Please enter at least an english name.'))
            names = {}
            descriptions = {}
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
        parent_location_id = location_form.parent_location.data

        if len(location_form.translations.errors) == 0:
            try:
                parent_location_id = int(parent_location_id)
            except ValueError:
                parent_location_id = None
            if parent_location_id < 0:
                parent_location_id = None
            if location is None:
                location = create_location(names, descriptions, parent_location_id, flask_login.current_user.id)
                if location_form.is_public.data:
                    set_location_permissions_for_all_users(location.id, Permissions.WRITE)
                else:
                    set_user_location_permissions(location.id, flask_login.current_user.id, Permissions.GRANT)
                flask.flash(_('The location was created successfully.'), 'success')
            else:
                update_location(location.id, names, descriptions, parent_location_id, flask_login.current_user.id)
                flask.flash(_('The location was updated successfully.'), 'success')
            return flask.redirect(flask.url_for('.location', location_id=location.id))
    if english.id not in description_language_ids:
        description_language_ids.append(english.id)
    return flask.render_template(
        'locations/location_form.html',
        location=location,
        location_form=location_form,
        submit_text=submit_text,
        ENGLISH=english,
        languages=get_languages(only_enabled_for_input=True),
        translations=location_translations,
        name_language_ids=name_language_ids,
        description_language_ids=description_language_ids,
        location_is_fed=location_is_fed
    )
