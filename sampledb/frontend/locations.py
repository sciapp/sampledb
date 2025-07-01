# coding: utf-8
"""

"""
import typing
import json

import flask
import flask_login
import werkzeug.datastructures
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SelectMultipleField, BooleanField, IntegerField, FormField, FieldList
from wtforms.validators import DataRequired

from . import frontend
from .permission_forms import set_up_permissions_forms, handle_permission_forms
from .. import logic
from ..logic import errors
from ..logic.components import get_component
from ..logic.locations import Location, create_location, get_location, get_locations_tree, update_location, get_object_location_assignment, confirm_object_responsibility, decline_object_responsibility, get_object_location_assignments, get_location_capacities, get_assigned_object_count_by_action_types
from ..logic.location_log import get_log_entries_for_location
from ..logic.languages import Language, get_language, get_languages, get_language_by_lang_code
from ..logic.security_tokens import verify_token
from ..logic.notifications import mark_notification_for_being_assigned_as_responsible_user_as_read, create_notification_for_a_declined_responsibility_assignment
from ..logic.location_permissions import get_user_location_permissions, get_location_permissions_for_all_users, get_location_permissions_for_users, get_location_permissions_for_groups, get_location_permissions_for_projects, set_location_permissions_for_all_users, set_user_location_permissions
from ..logic.users import get_user, get_users
from ..logic.groups import get_group
from ..logic.projects import get_project
from ..logic.settings import get_user_settings, set_user_settings
from ..logic.topics import get_topics, set_location_topics
from .utils import check_current_user_is_not_readonly, get_location_name, get_groups_form_data, parse_filter_id_params, build_modified_url
from ..utils import FlaskResponseT
from ..logic.utils import get_translated_text
from ..models import Permissions, LocationLogEntryType


LOCATION_LIST_FILTER_PARAMETERS = (
    'location_list_filters',
    'topic_ids'
)


class LocationCapacityForm(FlaskForm):
    action_type_id = SelectField(validators=[DataRequired()], coerce=int, choices=[], validate_choice=False)
    capacity = IntegerField()


class LocationForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])
    parent_location = SelectField()
    is_public = BooleanField(default=True)
    type = SelectField(validators=[DataRequired()])
    responsible_users = SelectMultipleField()
    is_hidden = BooleanField(default=False)
    enable_object_assignments = BooleanField(default=True)
    capacities = FieldList(FormField(LocationCapacityForm))
    topics = SelectMultipleField()


@frontend.route('/locations/')
@flask_login.login_required
def locations() -> FlaskResponseT:
    locations_map, locations_tree = get_locations_tree()
    permissions_by_id = {
        location_id: get_user_location_permissions(location_id, flask_login.current_user.id)
        for location_id in locations_map
    }

    topics = get_topics()
    topics_by_id = {
        topic.id: topic
        for topic in topics
    }
    valid_topic_ids = [topic.id for topic in topics]

    if 'location_list_filters' in flask.request.args or any(any(flask.request.args.getlist(param)) for param in LOCATION_LIST_FILTER_PARAMETERS):
        (
            success,
            filter_topic_ids,
        ) = _parse_location_list_filters(
            params=flask.request.args,
            valid_topic_ids=valid_topic_ids
        )
        if not success:
            return flask.abort(400)
    else:
        filter_topic_ids = get_user_settings(user_id=flask_login.current_user.id)['DEFAULT_LOCATION_LIST_FILTERS'].get('filter_topic_ids', [])

    if filter_topic_ids is None or flask.current_app.config['DISABLE_TOPICS']:
        filter_topic_ids = []

    if filter_topic_ids:
        def locations_filter(location: Location) -> bool:
            return location_has_topic_ids(location, frozenset(filter_topic_ids))
        locations_tree = filter_location_tree_by_predicate(locations_tree, locations_map, locations_filter)
    else:
        def locations_filter(location: Location) -> bool:
            return True

    filter_topic_infos = []
    if filter_topic_ids:
        for topic_id in filter_topic_ids:
            topic = topics_by_id[topic_id]
            filter_topic_infos.append({
                'name': get_translated_text(topic.name, default=_('Unnamed Topic')),
                'url': flask.url_for('.topic', topic_id=topic_id)
            })

    filtered_locations_tree = filter_location_tree_by_predicate(locations_tree, locations_map, lambda location: user_has_read_permissions_for_location(location, permissions_by_id))
    has_hidden_locations = filtered_locations_tree != locations_tree
    return flask.render_template(
        'locations/locations.html',
        locations_map=locations_map,
        locations_tree=filtered_locations_tree,
        sort_location_ids_by_name=sort_location_ids_by_name,
        has_hidden_locations=has_hidden_locations,
        permissions_by_id=permissions_by_id,
        Permissions=Permissions,
        get_component=get_component,
        get_user=get_user,
        topics=topics,
        filter_topic_infos=filter_topic_infos,
        filter_topic_ids=filter_topic_ids,
        locations_filter=locations_filter
    )


_LocationTree = typing.Dict[int, '_LocationTree']


def location_has_topic_ids(location: Location, topic_ids: typing.FrozenSet[int]) -> bool:
    location_topic_ids = {
        topic.id
        for topic in location.topics
    }
    return len(location_topic_ids.intersection(topic_ids)) > 0


def user_has_read_permissions_for_location(location: Location, permissions_by_id: typing.Dict[int, Permissions]) -> bool:
    return Permissions.READ in permissions_by_id[location.id]


def filter_location_tree_by_predicate(
        location_tree: _LocationTree,
        locations_map: typing.Dict[int, Location],
        predicate: typing.Callable[[Location], bool]
) -> _LocationTree:
    filtered_locations_tree: _LocationTree = {}
    for location_id in location_tree:
        sub_location_tree = location_tree[location_id]
        if sub_location_tree:
            sub_location_tree = filter_location_tree_by_predicate(sub_location_tree, locations_map, predicate)
        if predicate(locations_map[location_id]) or sub_location_tree:
            filtered_locations_tree[location_id] = sub_location_tree
    return filtered_locations_tree


def _parse_location_list_filters(
        params: werkzeug.datastructures.MultiDict[str, str],
        valid_topic_ids: typing.List[int]
) -> typing.Tuple[
    bool,
    typing.Optional[typing.List[int]],
]:
    FALLBACK_RESULT = False, None
    success, filter_topic_ids = parse_filter_id_params(
        params=params,
        param_aliases=['topic_ids'],
        valid_ids=valid_topic_ids,
        id_map={},
        multi_params_error='',
        parse_error=_('Unable to parse topic IDs.'),
        invalid_id_error=_('Invalid topic ID.')
    )
    if not success:
        return FALLBACK_RESULT

    return (
        True,
        filter_topic_ids,
    )


@frontend.route('/locations/', methods=['POST'])
@flask_login.login_required
def save_location_list_defaults() -> FlaskResponseT:
    if 'save_default_location_filters' in flask.request.form:
        topics = get_topics()
        valid_topic_ids = [topic.id for topic in topics]
        success, filter_topic_ids = _parse_location_list_filters(
            params=flask.request.form,
            valid_topic_ids=valid_topic_ids
        )
        if not success:
            return flask.abort(400)
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_LOCATION_LIST_FILTERS': {
                    'filter_topic_ids': filter_topic_ids,
                }
            }
        )
        return flask.redirect(build_modified_url('.locations', blocked_parameters=LOCATION_LIST_FILTER_PARAMETERS))
    if 'clear_default_location_filters' in flask.request.form:
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_LOCATION_LIST_FILTERS': {}
            }
        )
        return flask.redirect(build_modified_url('.locations', blocked_parameters=LOCATION_LIST_FILTER_PARAMETERS))
    return flask.abort(400)


@frontend.route('/locations/<int:location_id>', methods=['GET', 'POST'])
@flask_login.login_required
def location(location_id: int) -> FlaskResponseT:
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
    ancestors: typing.List[Location] = []
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
    if location.type.enable_capacities:
        capacities = get_location_capacities(location.id)
        stored_objects = get_assigned_object_count_by_action_types(location.id)
        action_types = logic.action_types.get_action_types(filter_fed_defaults=True)
    else:
        capacities = None
        stored_objects = None
        action_types = None
    return flask.render_template(
        'locations/location.html',
        locations_map=locations_map,
        locations_tree=locations_tree,
        descendent_location_ids=descendent_location_ids,
        location=location,
        ancestors=ancestors,
        sort_location_ids_by_name=sort_location_ids_by_name,
        permissions=permissions,
        permissions_by_id=permissions_by_id,
        Permissions=Permissions,
        location_log_entries=get_log_entries_for_location(location.id, flask_login.current_user.id) if location.type.show_location_log else None,
        LocationLogEntryType=LocationLogEntryType,
        capacities=capacities,
        stored_objects=stored_objects,
        action_types=action_types,
        get_component=get_component,
        get_user=get_user
    )


@frontend.route('/locations/<int:location_id>/permissions', methods=['GET', 'POST'])
@flask_login.login_required
def location_permissions(location_id: int) -> FlaskResponseT:
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

        users = logic.users.get_users(exclude_hidden=not flask_login.current_user.is_admin or not flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN'], exclude_fed=True, exclude_eln_import=True)
        users = [user for user in users if user.id not in user_permissions]
        users.sort(key=lambda user: user.id)

        show_groups_form, groups_treepicker_info = get_groups_form_data(
            basic_group_filter=lambda group: group.id not in group_permissions
        )

        show_projects_form, projects_treepicker_info = get_groups_form_data(
            project_group_filter=lambda group: group.id not in project_permissions
        )

        if flask.request.method.lower() == 'post':
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
            flask.flash(_('You need GRANT permissions to edit the permissions for this location.'), 'error')
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
def new_location() -> FlaskResponseT:
    if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask_login.current_user.is_admin:
        flask.flash(_('Only administrators can create locations.'), 'error')
        return flask.abort(403)
    check_current_user_is_not_readonly()
    parent_location = None
    parent_location_id_str = flask.request.args.get('parent_location_id', None)
    if parent_location_id_str is not None:
        try:
            parent_location_id = int(parent_location_id_str)
        except ValueError:
            parent_location_id = None
    else:
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
) -> FlaskResponseT:
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
def accept_responsibility_for_object() -> FlaskResponseT:
    return _handle_object_location_assignment(
        token_salt='confirm_responsibility',
        missing_token_text=_('The confirmation token is missing.'),
        invalid_token_text=_('The confirmation token is invalid.'),
        success_text=_('You have successfully confirmed this responsibility assignment.'),
        callback=confirm_object_responsibility
    )


@frontend.route('/locations/decline_responsibility')
@flask_login.login_required
def decline_responsibility_for_object() -> FlaskResponseT:
    def _callback(object_location_assignment_id: int) -> None:
        decline_object_responsibility(object_location_assignment_id)
        object_location_assignment = get_object_location_assignment(object_location_assignment_id)
        if object_location_assignment.user_id != object_location_assignment.responsible_user_id and object_location_assignment.user_id is not None:
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
            assert current_responsible_user_id is not None  # needed by mypy but guaranteed by the surrounding if
            # notify the currently responsible user that the assignment was declined
            create_notification_for_a_declined_responsibility_assignment(current_responsible_user_id, object_location_assignment_id)
    return _handle_object_location_assignment(
        token_salt='decline_responsibility',
        missing_token_text=_('The declination token is missing.'),
        invalid_token_text=_('The declination token is invalid.'),
        success_text=_('You have successfully declined this responsibility assignment.'),
        callback=_callback
    )


def sort_location_ids_by_name(location_ids: typing.Iterable[int], location_map: typing.Dict[int, Location]) -> typing.List[int]:
    location_ids = list(location_ids)
    location_ids.sort(key=lambda location_id: get_location_name(location_map[location_id]))
    return location_ids


def _show_location_form(
        location: typing.Optional[Location],
        parent_location: typing.Optional[Location],
        has_grant_permissions: bool
) -> FlaskResponseT:
    english = get_language(Language.ENGLISH)
    name_language_ids: typing.List[int] = []
    description_language_ids: typing.List[int] = []

    class LanguageTranslation(typing.TypedDict):
        language_id: int
        lang_name: str
        name: str
        description: str

    location_translations: typing.List[LanguageTranslation] = []
    if location is not None:
        submit_text = "Save"
        may_change_hidden = flask_login.current_user.is_admin
        may_change_enable_object_assignments = flask_login.current_user.is_admin and (location.type is None or location.type.enable_object_assignments)
    else:
        submit_text = "Create"
        may_change_hidden = False
        may_change_enable_object_assignments = False

    location_types = logic.locations.get_location_types()

    locations_map, locations_tree = get_locations_tree()
    invalid_location_ids = []
    if location is not None:
        invalid_location_ids.append(location.id)
        ancestor_ids: typing.List[int] = []
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
    location_form.topics.choices = [
        (str(topic.id), topic)
        for topic in get_topics()
    ]
    topic_ids_str = flask.request.args.get('topic_ids')
    if topic_ids_str is not None:
        valid_topic_id_strs = [
            topic_id_str
            for topic_id_str, topic in location_form.topics.choices
        ]
        location_form.topics.default = [
            topic_id_str
            for topic_id_str in topic_ids_str.split(',')
            if topic_id_str in valid_topic_id_strs
        ]
    action_types = logic.action_types.get_action_types(filter_fed_defaults=True)
    valid_action_types = [
        action_type
        for action_type in action_types
        if action_type.enable_locations and not action_type.disable_create_objects
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
        users = []
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
    location_type_enable_capacities = {
        str(location_type.id): location_type.enable_capacities
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
            location_form.topics.data = [str(topic.id) for topic in location.topics]
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
        if location is not None:
            location_form.enable_object_assignments.data = location.enable_object_assignments
        else:
            location_form.enable_object_assignments.data = True

        if location is not None:
            capacities = get_location_capacities(location.id)
            for action_type_id, capacity in capacities.items():
                location_form.capacities.append_entry({
                    'action_type_id': action_type_id,
                    'capacity': capacity
                })

    form_is_valid = False
    if location_form.validate_on_submit():
        form_is_valid = True

    for action_type in valid_action_types:
        for entry in location_form.capacities.entries:
            if entry.action_type_id.data == action_type.id:
                break
        else:
            location_form.capacities.append_entry({
                'action_type_id': action_type.id,
                'capacity': 0
            })

    if location is not None:
        if location.name is not None:
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

        if location.description is not None:
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
    else:
        location_type = None
        location_type_id = None
    if location_type is None or location_type_id is None:
        form_is_valid = False
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
        assert location_type is not None  # mypy does not infer this, but it is guaranteed by the code above
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
        assert location_type is not None  # mypy does not infer this, but it is guaranteed by the code above
        if location_type.enable_capacities:
            valid_action_type_ids = {
                action_type.id
                for action_type in valid_action_types
            }
            handled_action_types = set()
            for entry in location_form.capacities.entries:
                if entry.action_type_id.data not in valid_action_type_ids:
                    form_is_valid = False
                elif entry.action_type_id.data in handled_action_types:
                    form_is_valid = False
                else:
                    handled_action_types.add(entry.action_type_id.data)
                if entry.capacity.data is not None and not 0 <= entry.capacity.data <= 1000000000:
                    form_is_valid = False
    if form_is_valid:
        assert location_type is not None  # mypy does not infer this, but it is guaranteed by the code above
        assert location_type_id is not None  # mypy does not infer this, but it is guaranteed by the code above
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
                enable_object_assignments=location_form.enable_object_assignments.data if may_change_enable_object_assignments else location.enable_object_assignments,
            )
            flask.flash(_('The location was updated successfully.'), 'success')
        if has_grant_permissions:
            logic.locations.set_location_responsible_users(location.id, responsible_user_ids)
        if not flask.current_app.config['DISABLE_TOPICS']:
            topic_ids = [
                int(topic_id)
                for topic_id in location_form.topics.data
            ]
            set_location_topics(location.id, topic_ids)
        if location_type.enable_capacities:
            for entry in location_form.capacities.entries:
                logic.locations.set_location_capacity(location.id, entry.action_type_id.data, entry.capacity.data)
        else:
            logic.locations.clear_location_capacities(location.id)
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
        location_type_enable_capacities=location_type_enable_capacities,
        valid_action_types=valid_action_types,
        previous_parent_location_is_invalid=previous_parent_location_is_invalid,
        has_grant_permissions=has_grant_permissions,
        may_change_hidden=may_change_hidden,
        may_change_enable_object_assignments=may_change_enable_object_assignments,
    )
