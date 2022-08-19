# coding: utf-8
"""

"""
import itertools
import json
import typing

import flask
import flask_login
from flask_babel import _

from .. import frontend
from ... import logic
from ... import models
from ...logic import user_log, object_sorting
from ...logic.actions import get_action, get_action_type
from ...logic.action_translations import get_action_with_translation_in_language
from ...logic.action_permissions import get_sorted_actions_for_user
from ...logic.object_permissions import Permissions, get_user_object_permissions, get_objects_with_permissions, get_object_info_with_permissions
from ...logic.users import get_user, get_users_by_name
from ...logic.settings import get_user_settings, set_user_settings
from ...logic.object_search import generate_filter_func, wrap_filter_func
from ...logic.groups import get_group
from ...logic.objects import get_object
from ...logic.projects import get_project, get_user_project_permissions
from ...logic.locations import get_location, get_object_ids_at_location
from ...logic.location_permissions import get_user_location_permissions, get_locations_with_user_permissions
from ...logic.errors import UserDoesNotExistError, LocationDoesNotExistError, ActionTypeDoesNotExistError
from ...logic.components import get_component
from ..utils import get_location_name, get_search_paths
from ...logic.utils import get_translated_text
from .permissions import get_object_if_current_user_has_read_permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/objects/')
@flask_login.login_required
def objects():
    objects = []
    display_properties = []
    display_property_titles = {}
    user_language_id = logic.languages.get_user_language(flask_login.current_user).id
    if 'display_properties' in flask.request.args:
        for property_info in itertools.chain(*[
            display_properties_str.split(',')
            for display_properties_str in flask.request.args.getlist('display_properties')
        ]):
            if ':' in property_info:
                property_name, property_title = property_info.split(':', 1)
            else:
                property_name, property_title = property_info, None
            if property_name not in display_properties:
                display_properties.append(property_name)
            if property_title is not None:
                display_property_titles[property_name] = flask.escape(property_title)

    all_actions = get_sorted_actions_for_user(
        user_id=flask_login.current_user.id
    )
    all_action_types = logic.actions.get_action_types(
        filter_fed_defaults=True
    )
    search_paths, search_paths_by_action, search_paths_by_action_type = get_search_paths(
        actions=all_actions,
        action_types=all_action_types,
        path_depth_limit=1,
        valid_property_types=(
            'text',
            'bool',
            'quantity',
            'datetime',
            'user',
            'object_reference',
            'sample',
            'measurement',
            'plotly_chart',
        )
    )

    name_only = True
    implicit_action_type = None
    object_ids_str = flask.request.args.get('ids', '')
    if object_ids_str:
        try:
            object_ids = [
                int(object_id)
                for object_id in object_ids_str.split(',')
            ]
        except ValueError:
            object_ids = []
        else:
            object_ids = [
                object_id
                for object_id in object_ids
                if Permissions.READ in get_user_object_permissions(object_id, user_id=flask_login.current_user.id)
            ]
        for object_id in object_ids:
            try:
                objects.append(get_object(object_id))
            except logic.errors.ObjectDoesNotExistError:
                pass
        query_string = ''
        use_advanced_search = False
        must_use_advanced_search = False
        advanced_search_had_error = False
        search_notes = []
        search_tree = None
        pagination_limit = None
        pagination_offset = None
        pagination_enabled = True
        num_objects_found = len(objects)
        sorting_property_name = None
        sorting_order_name = None
        show_filters = False
        all_actions = []
        filter_action_ids = []
        all_action_types = []
        filter_action_type_ids = []
        all_locations = []
        filter_location_ids = []
        filter_related_user_id = None
        filter_doi = None
        filter_user_id = None
        filter_user_permissions = None
        filter_all_users_permissions = None
        filter_anonymous_permissions = None
        filter_group_id = None
        filter_group_permissions = None
        filter_project_id = None
        filter_project_permissions = None
        all_publications = []
    else:
        pagination_enabled = True

        show_filters = True
        all_locations = get_locations_with_user_permissions(flask_login.current_user.id, Permissions.READ)
        if 'location_ids' in flask.request.args:
            try:
                filter_location_ids = [
                    int(id_str.strip())
                    for id_str in itertools.chain(*[
                        location_ids_str.split(',')
                        for location_ids_str in flask.request.args.getlist('location_ids')
                    ])
                ]
            except ValueError:
                flask.flash(_('Unable to parse location IDs.'), 'error')
                return flask.abort(400)
            all_location_ids = [
                location.id
                for location in all_locations
            ]
            if any(location_id not in all_location_ids for location_id in filter_location_ids):
                flask.flash(_('Invalid location ID.'), 'error')
                return flask.abort(400)
            if 'location' in flask.request.args:
                flask.flash(_('Only one of location_ids and location may be set.'), 'error')
                return flask.abort(400)
        else:
            filter_location_ids = None
        if 'location' in flask.request.args:
            try:
                location_id = int(flask.request.args.get('location', ''))
                if Permissions.READ in get_user_location_permissions(location_id, flask_login.current_user.id):
                    filter_location_ids = [location_id]
                else:
                    flask.flash(_('You do not have the required permissions to access this location.'), 'error')
            except ValueError:
                flask.flash(_('Unable to parse location IDs.'), 'error')
            except LocationDoesNotExistError:
                flask.flash(_('No location with the given ID exists.'), 'error')

        if 'action_ids' in flask.request.args:
            try:
                filter_action_ids = [
                    int(id_str.strip())
                    for id_str in itertools.chain(*[
                        action_ids_str.split(',')
                        for action_ids_str in flask.request.args.getlist('action_ids')
                    ])
                ]
            except ValueError:
                flask.flash(_('Unable to parse action IDs.'), 'error')
                return flask.abort(400)
            all_action_ids = [
                action.id
                for action in all_actions
            ]
            if any(action_id not in all_action_ids for action_id in filter_action_ids):
                flask.flash(_('Invalid action ID.'), 'error')
                return flask.abort(400)
            if 'action' in flask.request.args:
                flask.flash(_('Only one of action_ids and action may be set.'), 'error')
                return flask.abort(400)
        else:
            filter_action_ids = None

        if 'action_type_ids' in flask.request.args:
            try:
                filter_action_type_ids = [
                    int(id_str.strip())
                    for id_str in itertools.chain(*[
                        action_type_ids_str.split(',')
                        for action_type_ids_str in flask.request.args.getlist('action_type_ids')
                    ])
                ]
            except ValueError:
                flask.flash(_('Unable to parse action type IDs.'), 'error')
                return flask.abort(400)
            all_action_type_ids = [
                action_type.id
                for action_type in all_action_types
            ]
            if any(action_type_id not in all_action_type_ids for action_type_id in filter_action_type_ids):
                flask.flash(_('Invalid action type ID.'), 'error')
                return flask.abort(400)
            if 't' in flask.request.args:
                flask.flash(_('Only one of action_type_ids and t may be set.'), 'error')
                return flask.abort(400)
        else:
            filter_action_type_ids = None
        try:
            action_id = int(flask.request.args.get('action', ''))
        except ValueError:
            action_id = None
        if action_id is None and filter_action_ids is not None and len(filter_action_ids) == 1:
            action_id = filter_action_ids[0]
        if action_id is not None:
            action = get_action_with_translation_in_language(action_id, user_language_id, use_fallback=True)
            implicit_action_type = get_action_type(action.type_id) if action.type_id is not None else None
            action_schema = action.schema
            if action_schema:
                action_display_properties = action_schema.get('displayProperties', [])
                for property_name in action_display_properties:
                    if property_name not in display_properties:
                        display_properties.append(property_name)
                    if property_name not in display_property_titles:
                        display_property_titles[property_name] = flask.escape(get_translated_text(action_schema['properties'][property_name]['title']))
        else:
            action_type_id = flask.request.args.get('t', '')
            if action_type_id is not None:
                try:
                    action_type_id = int(action_type_id)
                except ValueError:
                    # ensure old links still function
                    action_type_id = {
                        'samples': models.ActionType.SAMPLE_CREATION,
                        'measurements': models.ActionType.MEASUREMENT,
                        'simulations': models.ActionType.SIMULATION
                    }.get(action_type_id, None)
            if action_type_id is not None:
                try:
                    action_type = get_action_type(
                        action_type_id=action_type_id
                    )
                except ActionTypeDoesNotExistError:
                    action_type = None
            else:
                action_type = None
            if filter_action_type_ids is None and action_type is not None:
                filter_action_type_ids = [action_type.id]

        if filter_action_ids is None and action_id is not None:
            filter_action_ids = [action_id]
        if display_properties:
            name_only = False

        try:
            filter_related_user_id = int(flask.request.args.get('related_user', ''))
            get_user(filter_related_user_id)
        except ValueError:
            filter_related_user_id = None
        except UserDoesNotExistError:
            filter_related_user_id = None

        all_publications = logic.publications.get_publications_for_user(flask_login.current_user.id)
        try:
            filter_doi = logic.publications.simplify_doi(flask.request.args.get('doi', ''))
        except logic.errors.InvalidDOIError:
            filter_doi = None

        filter_user_permissions = None
        try:
            filter_user_id = int(flask.request.args.get('user', ''))
            get_user(filter_user_id)
        except ValueError:
            filter_user_id = None
        except UserDoesNotExistError:
            filter_user_id = None
        else:
            filter_user_permissions = {
                'read': Permissions.READ,
                'write': Permissions.WRITE,
                'grant': Permissions.GRANT
            }.get(flask.request.args.get('user_permissions', '').lower(), Permissions.READ)

        filter_all_users_permissions = {
            'read': Permissions.READ
        }.get(flask.request.args.get('all_users_permissions', '').lower(), None)

        if flask.current_app.config['ENABLE_ANONYMOUS_USERS']:
            filter_anonymous_permissions = {
                'read': Permissions.READ
            }.get(flask.request.args.get('anonymous_permissions', '').lower(), None)
        else:
            filter_anonymous_permissions = None

        filter_group_permissions = None
        try:
            filter_group_id = int(flask.request.args.get('group', ''))
            group_member_ids = logic.groups.get_group_member_ids(filter_group_id)
        except ValueError:
            filter_group_id = None
        except logic.errors.GroupDoesNotExistError:
            filter_group_id = None
        else:
            if flask_login.current_user.id not in group_member_ids:
                return flask.abort(403)
            filter_group_permissions = {
                'read': Permissions.READ,
                'write': Permissions.WRITE,
                'grant': Permissions.GRANT
            }.get(flask.request.args.get('group_permissions', '').lower(), Permissions.READ)

        filter_project_permissions = None
        try:
            filter_project_id = int(flask.request.args.get('project', ''))
            get_project(filter_project_id)
        except ValueError:
            filter_project_id = None
        except logic.errors.ProjectDoesNotExistError:
            filter_project_id = None
        else:
            if Permissions.READ not in get_user_project_permissions(project_id=filter_project_id, user_id=flask_login.current_user.id, include_groups=True):
                return flask.abort(403)
            filter_project_permissions = {
                'read': Permissions.READ,
                'write': Permissions.WRITE,
                'grant': Permissions.GRANT
            }.get(flask.request.args.get('project_permissions', '').lower(), Permissions.READ)

        if flask.request.args.get('limit', '') == 'all':
            pagination_limit = None
        else:
            try:
                pagination_limit = int(flask.request.args.get('limit', ''))
            except ValueError:
                pagination_limit = None
            else:
                if pagination_limit <= 0:
                    pagination_limit = None
                elif pagination_limit >= 1000:
                    pagination_limit = 1000

            # default objects per page
            if pagination_limit is None:
                pagination_limit = get_user_settings(flask_login.current_user.id)['OBJECTS_PER_PAGE']
            else:
                set_user_settings(flask_login.current_user.id, {'OBJECTS_PER_PAGE': pagination_limit})

        try:
            pagination_offset = int(flask.request.args.get('offset', ''))
        except ValueError:
            pagination_offset = None
        else:
            if pagination_offset < 0:
                pagination_offset = None
            elif pagination_offset > 100000000:
                pagination_offset = 100000000
        if pagination_limit is not None and pagination_offset is None:
            pagination_offset = 0

        sorting_order_name = flask.request.args.get('order', None)
        if sorting_order_name == 'asc':
            sorting_order = object_sorting.ascending
        elif sorting_order_name == 'desc':
            sorting_order = object_sorting.descending
        else:
            sorting_order = None

        sorting_property_name = flask.request.args.get('sortby', None)

        if sorting_order is None:
            if sorting_property_name is None:
                sorting_order_name = 'desc'
                sorting_order = object_sorting.descending
            else:
                sorting_order_name = 'asc'
                sorting_order = object_sorting.ascending
        if sorting_property_name is None:
            sorting_property_name = '_object_id'
        else:
            name_only = False
        if sorting_property_name == '_object_id':
            sorting_property = object_sorting.object_id()
        elif sorting_property_name == '_creation_date':
            sorting_property = object_sorting.creation_date()
        elif sorting_property_name == '_last_modification_date':
            sorting_property = object_sorting.last_modification_date()
        else:
            sorting_property = object_sorting.property_value(sorting_property_name)

        sorting_function = sorting_order(sorting_property)

        query_string = flask.request.args.get('q', '')
        if query_string:
            name_only = False
        search_tree = None
        use_advanced_search = flask.request.args.get('advanced', None) is not None
        must_use_advanced_search = use_advanced_search
        advanced_search_had_error = False
        additional_search_notes = []
        if not use_advanced_search and query_string:
            if filter_user_id is None:
                users = get_users_by_name(query_string)
                if len(users) == 1:
                    user = users[0]
                    filter_user_id = user.id
                    query_string = ''
                elif len(users) > 1:
                    additional_search_notes.append(('error', "There are multiple users with this name.", 0, 0))
            if filter_doi is None and query_string.startswith('doi:'):
                try:
                    filter_doi = logic.publications.simplify_doi(query_string)
                    query_string = ''
                except logic.errors.InvalidDOIError:
                    pass
        if query_string and len(query_string) > 1 and query_string.startswith('#'):
            try:
                object_id = int(query_string[1:])
                if object_id > 0:
                    logic.objects.check_object_exists(object_id)
                    return flask.redirect(flask.url_for('.object', object_id=object_id))
            except ValueError:
                pass
            except logic.errors.ObjectDoesNotExistError:
                pass
        try:
            filter_func, search_tree, use_advanced_search = generate_filter_func(query_string, use_advanced_search)
        except Exception:
            # TODO: ensure that advanced search does not cause exceptions
            if use_advanced_search:
                advanced_search_had_error = True

                def filter_func(data, search_notes):
                    """ Return all objects"""
                    search_notes.append(('error', "Unable to parse search expression", 0, len(query_string)))
                    return False
            else:
                raise
        filter_func, search_notes = wrap_filter_func(filter_func)
        search_notes.extend(additional_search_notes)

        if filter_location_ids is not None:
            object_ids_at_location = set()
            for location_id in filter_location_ids:
                object_ids_at_location.update(get_object_ids_at_location(location_id))
        else:
            object_ids_at_location = None
        if filter_related_user_id is None:
            object_ids_for_user = None
        else:
            object_ids_for_user = set(user_log.get_user_related_object_ids(filter_related_user_id))
        if filter_doi is None:
            object_ids_for_doi = None
        else:
            object_ids_for_doi = set(logic.publications.get_object_ids_linked_to_doi(filter_doi))

        if use_advanced_search and not must_use_advanced_search:
            search_notes.append(('info', _("The advanced search was used automatically. Search for \"%(query_string)s\" to use the simple search.", query_string=query_string), 0, 0))
        try:
            object_ids: typing.Optional[typing.Set[int]] = None
            if object_ids_at_location is not None:
                if object_ids is None:
                    object_ids = object_ids_at_location
                else:
                    object_ids = object_ids.intersection(object_ids_at_location)
            if object_ids_for_user is not None:
                if object_ids is None:
                    object_ids = object_ids_for_user
                else:
                    object_ids = object_ids.intersection(object_ids_for_user)
            if object_ids_for_doi is not None:
                if object_ids is None:
                    object_ids = object_ids_for_doi
                else:
                    object_ids = object_ids.intersection(object_ids_for_doi)

            if object_ids is not None:
                pagination_enabled = False
                pagination_limit = None
                pagination_offset = None
            if object_ids is not None and not object_ids:
                objects = []
                num_objects_found = 0
            else:
                num_objects_found_list = []
                objects = get_objects_with_permissions(
                    user_id=flask_login.current_user.id,
                    permissions=Permissions.READ,
                    filter_func=filter_func,
                    sorting_func=sorting_function,
                    limit=pagination_limit,
                    offset=pagination_offset,
                    action_ids=filter_action_ids,
                    action_type_ids=filter_action_type_ids,
                    other_user_id=filter_user_id,
                    other_user_permissions=filter_user_permissions,
                    project_id=filter_project_id,
                    project_permissions=filter_project_permissions,
                    group_id=filter_group_id,
                    group_permissions=filter_group_permissions,
                    all_users_permissions=filter_all_users_permissions,
                    anonymous_users_permissions=filter_anonymous_permissions,
                    object_ids=object_ids,
                    num_objects_found=num_objects_found_list,
                    name_only=name_only
                )
                num_objects_found = num_objects_found_list[0]
        except Exception as e:
            search_notes.append(('error', "Error during search: {}".format(e), 0, 0))
            objects = []
            num_objects_found = 0
        if any(note[0] == 'error' for note in search_notes):
            objects = []
            advanced_search_had_error = True

    cached_actions = {None: None}
    cached_users = {None: None}

    for i, obj in enumerate(objects):
        if obj.version_id == 0:
            original_object = obj
        else:
            original_object = get_object(object_id=obj.object_id, version_id=0)
        if obj.action_id is not None and obj.action_id not in cached_actions:
            cached_actions[obj.action_id] = get_action(obj.action_id)
        if obj.user_id is not None and obj.user_id not in cached_users:
            cached_users[obj.user_id] = get_user(obj.user_id)
        if obj.user_id is not None and original_object.user_id not in cached_users:
            cached_users[original_object.user_id] = get_user(original_object.user_id)
        objects[i] = {
            'object_id': obj.object_id,
            'created_by': cached_users[original_object.user_id],
            'created_at': original_object.utc_datetime,
            'modified_by': cached_users[obj.user_id],
            'last_modified_at': obj.utc_datetime,
            'data': obj.data,
            'schema': obj.schema,
            'name': obj.name,
            'action': cached_actions[obj.action_id],
            'fed_object_id': obj.fed_object_id,
            'component_id': obj.component_id,
            'display_properties': {},
            'component': obj.component
        }

        for property_name in display_properties:
            objects[i]['display_properties'][property_name] = None
            if not objects[i]['data'] or not objects[i]['schema']:
                # object does not have any properties
                continue
            if property_name not in objects[i]['schema']['properties']:
                # object must not have this property
                continue
            property_schema = objects[i]['schema']['properties'][property_name]
            if property_name not in objects[i]['data']:
                # object does not have this property
                continue
            property_data = objects[i]['data'][property_name]
            if not isinstance(property_data, dict) or '_type' not in property_data:
                # property data cannot be displayed (e.g. None/null or array)
                continue
            objects[i]['display_properties'][property_name] = (property_data, property_schema)

    def build_modified_url(**query_parameters):
        for key in flask.request.args:
            if key not in query_parameters:
                query_parameters[key] = flask.request.args.getlist(key)
        return flask.url_for(
            '.objects',
            **query_parameters
        )

    action_ids = {
        object['action'].id for object in objects if object['action'] is not None
    }
    action_translations = {}
    for id in action_ids:
        action_translations[id] = logic.action_translations.get_action_translation_for_action_in_language(
            action_id=id,
            language_id=user_language_id,
            use_fallback=True
        )

    default_property_titles = {
        'tags': _('Tags'),
        'hazards': _('Hazards')
    }
    for property_name in display_properties:
        if display_property_titles.get(property_name) is None:
            property_titles = set()
            for id in action_ids:
                property_info = search_paths_by_action.get(id, {}).get(property_name)
                if property_info is not None and 'titles' in property_info:
                    property_titles.update(property_info['titles'])
            if property_titles:
                property_title = ', '.join(sorted(list(property_titles)))
            elif property_name in default_property_titles:
                property_title = flask.escape(default_property_titles[property_name])
            else:
                property_title = flask.escape(property_name)
            display_property_titles[property_name] = property_title

    last_edit_info = None
    creation_info = None
    action_info = None
    if 'object_list_options' in flask.request.args:
        creation_info = set()
        for creation_info_str in flask.request.args.getlist('creation_info'):
            creation_info_str = creation_info_str.strip().lower()
            if creation_info_str in {'user', 'date'}:
                creation_info.add(creation_info_str)
        creation_info = list(creation_info)

        last_edit_info = set()
        for last_edit_info_str in flask.request.args.getlist('last_edit_info'):
            last_edit_info_str = last_edit_info_str.strip().lower()
            if last_edit_info_str in {'user', 'date'}:
                last_edit_info.add(last_edit_info_str)
        last_edit_info = list(last_edit_info)

        action_info = set()
        for action_info_str in flask.request.args.getlist('action_info'):
            action_info_str = action_info_str.strip().lower()
            if action_info_str in {'instrument', 'action'}:
                action_info.add(action_info_str)
        action_info = list(action_info)

    if creation_info is None:
        creation_info = ['user', 'date']
    if last_edit_info is None:
        last_edit_info = ['user', 'date']
    if action_info is None:
        if filter_action_ids is None or len(filter_action_ids) != 1:
            action_info = ['instrument', 'action']
        else:
            action_info = []

    object_name_plural = _('Objects')

    filter_action_type_infos = []
    if filter_action_type_ids:
        for action_type_id in filter_action_type_ids:
            action_type = get_action_type(action_type_id)
            action_type_name = get_translated_text(action_type.name, user_language_id, default=_('Unnamed Action Type'))
            action_type_component = get_component(action_type.component_id) if action_type.component_id is not None else None
            filter_action_type_infos.append({
                'id': action_type_id,
                'name': action_type_name,
                'url': flask.url_for('.actions', t=action_type_id),
                'fed_id': action_type.fed_id,
                'component_name': action_type_component.get_name() if action_type_component is not None else None
            })

            if filter_action_type_ids and len(filter_action_type_ids) == 1:
                object_name_plural = get_translated_text(action_type.name, user_language_id, default=_('Objects'))
    elif implicit_action_type is not None:
        object_name_plural = get_translated_text(implicit_action_type.name, user_language_id, default=_('Objects'))

    filter_action_infos = []
    if filter_action_ids:
        for action_id in filter_action_ids:
            action = get_action_with_translation_in_language(action_id, user_language_id, use_fallback=True)
            action_name = action.translation.name
            if not action_name:
                action_name = _('Unnamed Action')
            action_name += f' (#{action_id})'
            filter_action_infos.append({
                'name': action_name,
                'url': flask.url_for('.action', action_id=action_id),
                'fed_id': action.fed_id,
                'component_name': action.component.get_name() if action.component is not None else None
            })

    filter_location_infos = []
    if filter_location_ids:
        for location_id in filter_location_ids:
            location = get_location(location_id)
            location_name = get_location_name(location_id, include_id=True)
            filter_location_infos.append({
                'name': location_name,
                'url': flask.url_for('.location', location_id=location_id),
                'fed_id': location.fed_id,
                'component_name': location.component.get_name() if location.component is not None else None
            })

    if filter_related_user_id is not None:
        user = get_user(filter_related_user_id)
        filter_related_user_info = {
            'name': user.get_name(),
            'url': flask.url_for('.user_profile', user_id=filter_related_user_id),
            'fed_id': user.fed_id,
            'component_name': user.component.get_name() if user.component is not None else None,
        }
    else:
        filter_related_user_info = None

    if filter_user_permissions is not None and filter_user_id is not None:
        filter_user_permissions_info = {
            'name': None,
            'url': None,
            'fed_id': None,
            'component_name': None,
            'permissions': _(filter_user_permissions.name.title())
        }
        if filter_user_id != flask_login.current_user.id:
            user = get_user(filter_user_id)
            filter_user_permissions_info.update({
                'name': user.get_name(),
                'url': flask.url_for('.user_profile', user_id=filter_user_id),
                'fed_id': user.fed_id,
                'component_name': user.component.get_name() if user.component is not None else None,
            })
        elif filter_user_permissions == Permissions.READ:
            # READ permissions for the current user as always necessary, so this filter does not need to be displayed
            filter_user_permissions_info = None
    else:
        filter_user_permissions_info = None

    if filter_group_permissions is not None and filter_group_id is not None:
        group = get_group(filter_group_id)
        filter_group_permissions_info = {
            'name': f'{get_translated_text(group.name)} (#{filter_group_id})',
            'url': flask.url_for('.group', group_id=filter_group_id),
            'permissions': _(filter_group_permissions.name.title())
        }
    else:
        filter_group_permissions_info = None

    if filter_project_permissions is not None and filter_project_id is not None:
        project = get_project(filter_project_id)
        filter_project_permissions_info = {
            'name': f'{get_translated_text(project.name)} (#{filter_project_id})',
            'url': flask.url_for('.project', project_id=filter_project_id),
            'permissions': _(filter_project_permissions.name.title())
        }
    else:
        filter_project_permissions_info = None

    if filter_doi:
        filter_doi_info = {
            'doi': filter_doi,
            'title': dict(all_publications).get(filter_doi)
        }
    else:
        filter_doi_info = None

    return flask.render_template(
        'objects/objects.html',
        objects=objects,
        display_properties=display_properties,
        display_property_titles=display_property_titles,
        search_query=query_string,
        use_advanced_search=use_advanced_search,
        must_use_advanced_search=must_use_advanced_search,
        advanced_search_had_error=advanced_search_had_error,
        search_notes=search_notes,
        search_tree=search_tree,
        search_paths=search_paths,
        search_paths_by_action=search_paths_by_action,
        search_paths_by_action_type=search_paths_by_action_type,
        Permissions=Permissions,
        creation_info=creation_info,
        last_edit_info=last_edit_info,
        action_info=action_info,
        action_translations=action_translations,
        object_name_plural=object_name_plural,
        filter_action_type_infos=filter_action_type_infos,
        filter_action_infos=filter_action_infos,
        filter_location_infos=filter_location_infos,
        filter_related_user_info=filter_related_user_info,
        filter_user_permissions_info=filter_user_permissions_info,
        filter_group_permissions_info=filter_group_permissions_info,
        filter_project_permissions_info=filter_project_permissions_info,
        filter_all_users_permissions=filter_all_users_permissions,
        filter_anonymous_permissions=filter_anonymous_permissions,
        filter_doi_info=filter_doi_info,
        show_filters=show_filters,
        all_actions=all_actions,
        filter_action_ids=filter_action_ids,
        all_action_types=all_action_types,
        filter_action_type_ids=filter_action_type_ids,
        all_locations=all_locations,
        filter_location_ids=filter_location_ids,
        all_publications=all_publications,
        filter_doi=filter_doi,
        get_object_if_current_user_has_read_permissions=get_object_if_current_user_has_read_permissions,
        get_instrument_translation_for_instrument_in_language=logic.instrument_translations.get_instrument_translation_for_instrument_in_language,
        build_modified_url=build_modified_url,
        sorting_property=sorting_property_name,
        sorting_order=sorting_order_name,
        limit=pagination_limit,
        offset=pagination_offset,
        pagination_enabled=pagination_enabled,
        num_objects_found=num_objects_found,
        get_user=get_user,
        get_component=get_component
    )


@frontend.route('/objects/referencable')
@flask_login.login_required
def referencable_objects():
    required_perm = Permissions.READ
    if 'required_perm' in flask.request.args:
        try:
            required_perm = Permissions.from_name(flask.request.args['required_perm'])
        except ValueError:
            try:
                required_perm = Permissions(int(flask.request.args['required_perm']))
            except ValueError:
                return {
                    "message": "argument {} is not a valid permission.".format(flask.request.args['required_perm'])
                }, 400

    action_ids = None
    if 'action_ids' in flask.request.args:
        action_ids = flask.request.args['action_ids']
        try:
            action_ids = json.loads(action_ids)
        except Exception:
            action_ids = None
        else:
            if type(action_ids) is not list:
                action_ids = None
            elif -1 in action_ids:
                action_ids = None
            elif not all(type(action_id) is int for action_id in action_ids):
                action_ids = None

    referencable_objects = get_object_info_with_permissions(
        user_id=flask_login.current_user.id,
        permissions=required_perm,
        action_ids=action_ids
    )

    def dictify(x):
        return {
            'id': x.object_id,
            'text': '{} (#{})'.format(flask.escape(get_translated_text(x.name_json)) or '&mdash;', x.object_id) if x.component_name is None
            else '{} (#{}, #{} @ {})'.format(flask.escape(get_translated_text(x.name_json)) or '&mdash;', x.object_id, x.fed_object_id, flask.escape(x.component_name)),
            'action_id': x.action_id,
            'max_permission': x.max_permission,
            'tags': [flask.escape(tag) for tag in x.tags['tags']] if x.tags and isinstance(x.tags, dict) and x.tags.get('_type') == 'tags' and x.tags.get('tags') else [],
            'is_fed': x.fed_object_id is not None
        }

    return {
        'referencable_objects': [
            dictify(object)
            for object in referencable_objects
        ]
    }
