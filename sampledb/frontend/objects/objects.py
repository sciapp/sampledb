# coding: utf-8
"""

"""
import itertools
import json
import typing

import flask
import flask_login
import werkzeug
from flask_babel import _

from .. import frontend
from ... import logic
from ... import models
from ...logic import user_log, object_sorting
from ...logic.instruments import get_instruments, get_instrument
from ...logic.actions import get_action, get_action_type
from ...logic.action_permissions import get_sorted_actions_for_user
from ...logic.object_permissions import Permissions, get_user_object_permissions, get_objects_with_permissions, get_object_info_with_permissions
from ...logic.users import get_user, get_users, get_users_by_name, check_user_exists
from ...logic.settings import get_user_settings, set_user_settings
from ...logic.object_search import generate_filter_func, wrap_filter_func
from ...logic.groups import get_group
from ...logic.objects import get_object
from ...logic.projects import get_project, get_user_project_permissions
from ...logic.locations import get_location, get_object_ids_at_location
from ...logic.location_permissions import get_locations_with_user_permissions
from ...logic.languages import get_language_by_lang_code, get_language, get_languages, Language
from ...logic.errors import UserDoesNotExistError
from ...logic.components import get_component, check_component_exists
from ...logic.shares import get_shares_for_object
from ..utils import get_locations_form_data, get_location_name, get_search_paths, relative_url_for
from ...logic.utils import get_translated_text
from .forms import ObjectLocationAssignmentForm
from .permissions import get_object_if_current_user_has_read_permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

OBJECT_LIST_FILTER_PARAMETERS = (
    'object_list_filters',
    'action_type_ids',
    't',
    'action_ids',
    'action',
    'instrument_ids',
    'user',
    'user_permissions',
    'all_users_permissions',
    'anonymous_permissions',
    'location_ids',
    'location',
    'doi',
    'project',
    'component_id',
)

OBJECT_LIST_OPTION_PARAMETERS = (
    'object_list_options',
    'creation_info',
    'last_edit_info',
    'other_databases_info',
    'action_info',
    'display_properties',
    'location_info',
)


@frontend.route('/objects/')
@flask_login.login_required
def objects():
    objects = []

    user_settings = get_user_settings(user_id=flask_login.current_user.id)
    if any(any(flask.request.args.getlist(param)) for param in OBJECT_LIST_OPTION_PARAMETERS):
        display_properties, display_property_titles = _parse_display_properties(flask.request.args)
    else:
        display_properties = user_settings['DEFAULT_OBJECT_LIST_OPTIONS'].get('display_properties', [])
        display_property_titles = {}

    all_instruments = get_instruments()
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

    edit_location = flask.request.args.get('edit_location', default=False, type=lambda k: k.lower() == 'true')

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
        all_instruments = []
        filter_instrument_ids = []
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
        filter_origin_ids = None
        all_publications = []
        all_components = []
    else:
        pagination_enabled = True

        show_filters = True
        all_locations = get_locations_with_user_permissions(flask_login.current_user.id, Permissions.READ)

        valid_location_ids = [
            location.id
            for location in all_locations
        ]
        valid_action_type_ids = [
            action_type.id
            for action_type in all_action_types
        ]
        valid_action_ids = [
            action.id
            for action in all_actions
        ]
        valid_instrument_ids = [
            instrument.id
            for instrument in all_instruments
        ]

        if any(any(flask.request.args.getlist(param)) for param in OBJECT_LIST_FILTER_PARAMETERS):
            (
                success,
                filter_location_ids,
                filter_action_type_ids,
                filter_action_ids,
                filter_instrument_ids,
                filter_related_user_id,
                filter_doi,
                filter_anonymous_permissions,
                filter_all_users_permissions,
                filter_user_id,
                filter_user_permissions,
                filter_group_id,
                filter_group_permissions,
                filter_project_id,
                filter_project_permissions,
                filter_origin_ids,
            ) = _parse_object_list_filters(
                params=flask.request.args,
                valid_location_ids=valid_location_ids,
                valid_action_type_ids=valid_action_type_ids,
                valid_action_ids=valid_action_ids,
                valid_instrument_ids=valid_instrument_ids
            )
            if not success:
                return flask.abort(400)
        else:
            filter_location_ids = user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_location_ids')
            if filter_location_ids is not None:
                # remove location IDs which may have become invalid
                filter_location_ids = [
                    location_id
                    for location_id in filter_location_ids
                    if location_id in valid_location_ids
                ]

            filter_action_type_ids = user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_action_type_ids')
            if filter_action_type_ids is not None:
                # remove action type IDs which may have become invalid
                filter_action_type_ids = [
                    action_type_id
                    for action_type_id in filter_action_type_ids
                    if action_type_id in valid_action_type_ids
                ]

            filter_action_ids = user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_action_ids')
            if filter_action_ids is not None:
                # remove action IDs which may have become invalid
                filter_action_ids = [
                    action_id
                    for action_id in filter_action_ids
                    if action_id in valid_action_ids
                ]

            filter_instrument_ids = user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_instrument_ids')
            if filter_instrument_ids is not None:
                # remove action IDs which may have become invalid
                filter_instrument_ids = [
                    instrument_id
                    for instrument_id in filter_instrument_ids
                    if instrument_id in valid_instrument_ids
                ]

            filter_doi = user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_doi')

            filter_anonymous_permissions = {
                'read': Permissions.READ
            }.get(user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_anonymous_permissions'), None)

            filter_all_users_permissions = {
                'read': Permissions.READ
            }.get(user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_all_users_permissions'), None)

            filter_user_id = user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_user_id')

            filter_user_permissions = {
                'read': Permissions.READ,
                'write': Permissions.WRITE,
                'grant': Permissions.GRANT
            }.get(user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_user_permissions'), None)

            filter_origin_ids = user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_origin_ids', None)
            if filter_origin_ids:
                try:
                    # ensure origins are valid
                    for origin in filter_origin_ids:
                        origin_type, origin_id = origin
                        if origin_type == 'local' and origin_id is None:
                            continue
                        if origin_type == 'component' and type(origin_id) == int:
                            continue
                        filter_origin_ids = None
                        break
                    else:
                        # convert origins back to tuples
                        filter_origin_ids = [
                            tuple(origin)
                            for origin in filter_origin_ids
                        ]
                except Exception:
                    filter_origin_ids = None
            else:
                filter_origin_ids = None

            filter_related_user_id = None
            filter_group_id = None
            filter_group_permissions = None
            filter_project_id = None
            filter_project_permissions = None

        if filter_action_ids is not None and len(filter_action_ids) == 1:
            action_id = filter_action_ids[0]
        else:
            action_id = None
        if action_id is not None:
            action = get_action(action_id)
            implicit_action_type = get_action_type(action.type_id) if action.type_id is not None else None
            action_schema = action.schema
            if action_schema:
                action_display_properties = action_schema.get('displayProperties', [])
                for property_name in action_display_properties:
                    if property_name not in display_properties:
                        display_properties.append(property_name)
                    if property_name not in display_property_titles:
                        display_property_titles[property_name] = flask.escape(get_translated_text(action_schema['properties'][property_name]['title']))

        if display_properties:
            name_only = False

        all_publications = logic.publications.get_publications_for_user(flask_login.current_user.id)
        all_components = logic.components.get_components()

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
                pagination_limit = user_settings['OBJECTS_PER_PAGE']
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
        if filter_origin_ids is None:
            object_ids_for_origin_ids = None
        else:
            filter_local_objects = ('local', None) in filter_origin_ids
            filter_component_ids = {
                origin_id
                for origin_type, origin_id in filter_origin_ids
                if origin_type == 'component'
            }
            if filter_local_objects and len(filter_component_ids) == len(all_components):
                object_ids_for_origin_ids = None
            elif len(filter_component_ids) == len(all_components):
                object_ids_for_origin_ids = logic.components.get_object_ids_for_components()
            else:
                object_ids_for_origin_ids = set()
                if filter_local_objects:
                    object_ids_for_origin_ids = object_ids_for_origin_ids.union(logic.components.get_local_object_ids())
                for component_id in filter_component_ids:
                    object_ids_for_origin_ids = object_ids_for_origin_ids.union(logic.components.get_object_ids_for_component_id(component_id))

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
            if object_ids_for_origin_ids is not None:
                if object_ids is None:
                    object_ids = object_ids_for_origin_ids
                else:
                    object_ids = object_ids.intersection(object_ids_for_origin_ids)

            if object_ids is not None:
                pagination_enabled = False
                pagination_limit = None
                pagination_offset = None
            if object_ids is not None and not object_ids:
                objects = []
                num_objects_found = 0
            else:
                num_objects_found_list = []
                # do not actually filter by permissions for an administrator
                # with GRANT permissions for all objects
                if filter_user_id == flask_login.current_user.id and flask_login.current_user.has_admin_permissions:
                    actual_filter_user_id = None
                    actual_filter_user_permissions = None
                else:
                    actual_filter_user_id = filter_user_id
                    actual_filter_user_permissions = filter_user_permissions
                if not filter_instrument_ids:
                    actual_filter_action_ids = filter_action_ids
                else:
                    actual_filter_action_ids = []
                    for action in all_actions:
                        if not filter_action_ids or action.id in filter_action_ids:
                            if action.instrument_id in filter_instrument_ids:
                                actual_filter_action_ids.append(action.id)
                objects = get_objects_with_permissions(
                    user_id=flask_login.current_user.id,
                    permissions=Permissions.READ,
                    filter_func=filter_func,
                    sorting_func=sorting_function,
                    limit=pagination_limit,
                    offset=pagination_offset,
                    action_ids=actual_filter_action_ids,
                    action_type_ids=filter_action_type_ids,
                    other_user_id=actual_filter_user_id,
                    other_user_permissions=actual_filter_user_permissions,
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
    if all_actions:
        for action in all_actions:
            cached_actions[action.id] = action
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
            'fed_id': obj.fed_object_id,
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

    action_ids = {
        object['action'].id for object in objects if object['action'] is not None
    }

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

    if any(param in flask.request.args for param in OBJECT_LIST_OPTION_PARAMETERS):
        creation_info, last_edit_info, action_info, other_databases_info, location_info = _parse_object_list_options(flask.request.args)
    else:
        creation_info = user_settings['DEFAULT_OBJECT_LIST_OPTIONS'].get('creation_info', ['user', 'date'])
        last_edit_info = user_settings['DEFAULT_OBJECT_LIST_OPTIONS'].get('last_edit_info', ['user', 'date'])
        if filter_action_ids is None or len(filter_action_ids) != 1:
            action_info = user_settings['DEFAULT_OBJECT_LIST_OPTIONS'].get('action_info', ['instrument', 'action'])
        else:
            action_info = []
        other_databases_info = user_settings['DEFAULT_OBJECT_LIST_OPTIONS'].get('other_databases_info', False)
        if not edit_location:
            location_info = user_settings['DEFAULT_OBJECT_LIST_OPTIONS'].get('location_info', [])
        else:
            location_info = ['location', 'responsible_user']
    if not flask.current_app.config['FEDERATION_UUID']:
        other_databases_info = False

    if location_info:
        object_location_assignments = logic.locations.get_current_object_location_assignments(
            [
                object['object_id']
                for object in objects
            ]
        )
        for object in objects:
            object_location_assignment = object_location_assignments.get(object['object_id'])
            if object_location_assignment is None:
                object['location_id'] = None
                object['responsible_user_id'] = None
            else:
                object['location_id'] = object_location_assignment.location_id
                object['responsible_user_id'] = object_location_assignment.responsible_user_id

    object_name_plural = _('Objects')

    filter_action_type_infos = []
    if filter_action_type_ids:
        for action_type_id in filter_action_type_ids:
            action_type = get_action_type(action_type_id)
            action_type_name = get_translated_text(action_type.name, default=_('Unnamed Action Type'))
            action_type_component = get_component(action_type.component_id) if action_type.component_id is not None else None
            filter_action_type_infos.append({
                'id': action_type_id,
                'name': action_type_name,
                'url': flask.url_for('.actions', t=action_type_id),
                'fed_id': action_type.fed_id,
                'component_name': action_type_component.get_name() if action_type_component is not None else None
            })

            if filter_action_type_ids and len(filter_action_type_ids) == 1:
                object_name_plural = get_translated_text(action_type.object_name_plural, default=_('Objects'))
    elif implicit_action_type is not None:
        object_name_plural = get_translated_text(implicit_action_type.object_name_plural, default=_('Objects'))

    filter_action_infos = []
    if filter_action_ids:
        for action_id in filter_action_ids:
            action = get_action(action_id)
            action_name = get_translated_text(action.name, default=_('Unnamed Action'))
            action_name += f' (#{action_id})'
            filter_action_infos.append({
                'name': action_name,
                'url': flask.url_for('.action', action_id=action_id),
                'fed_id': action.fed_id,
                'component_name': action.component.get_name() if action.component is not None else None
            })
            if action.user:
                filter_action_infos[-1]['user'] = action.user
            if action.instrument:
                filter_action_infos[-1]['instrument'] = action.instrument
            if action.component and action.component.address:
                component_address = action.component.address
                if not component_address.endswith('/'):
                    component_address = component_address + '/'
                filter_action_infos[-1]['fed_url'] = component_address + relative_url_for('.action',
                                                                                          action_id=action.fed_id)

    filter_instrument_infos = []
    if filter_instrument_ids:
        for instrument_id in filter_instrument_ids:
            instrument = get_instrument(instrument_id)
            instrument_name = get_translated_text(instrument.name, default=_('Unnamed Instrument'))
            instrument_name += f' (#{instrument_id})'
            filter_instrument_infos.append({
                'name': instrument_name,
                'url': flask.url_for('.instrument', instrument_id=instrument_id),
                'fed_id': instrument.fed_id,
                'component_name': instrument.component.get_name() if instrument.component is not None else None
            })
            if instrument.component and instrument.component.address:
                component_address = instrument.component.address
                if not component_address.endswith('/'):
                    component_address = component_address + '/'
                filter_instrument_infos[-1]['fed_url'] = component_address + relative_url_for('.instrument', instrument_id=instrument.fed_id)

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

    if filter_origin_ids:
        filter_origins_info = {
            'local': ('local', None) in filter_origin_ids,
            'components': [
                get_component(component_id=origin_id)
                for origin_type, origin_id in filter_origin_ids
                if origin_type == 'component'
            ]
        }
    else:
        filter_origins_info = None

    if edit_location:
        location_form = ObjectLocationAssignmentForm()
        all_choices, choices = get_locations_form_data(filter=lambda location: location.type is None or location.type.enable_object_assignments)
        location_form.location.all_choices = all_choices
        location_form.location.choices = choices
        possible_resposible_users = [('-1', '-')]
        user_is_fed = {}
        for user in get_users(exclude_hidden=not flask_login.current_user.is_admin):
            possible_resposible_users.append((str(user.id), user.get_name()))
            user_is_fed[str(user.id)] = user.fed_id is not None
        location_form.responsible_user.choices = possible_resposible_users

        english = get_language(Language.ENGLISH)
        all_languages = get_languages()

        shown_object_ids = [object['object_id'] for object in objects]
        objects_with_write_permission = [obj.id for obj in get_objects_with_permissions(user_id=flask_login.current_user.id, permissions=Permissions.WRITE, object_ids=shown_object_ids)]
    else:
        location_form = None
        user_is_fed = {}
        english = None
        all_languages = []
        objects_with_write_permission = []

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
        other_databases_info=other_databases_info,
        location_info=location_info,
        object_name_plural=object_name_plural,
        filter_action_type_infos=filter_action_type_infos,
        filter_action_infos=filter_action_infos,
        filter_instrument_infos=filter_instrument_infos,
        filter_location_infos=filter_location_infos,
        filter_related_user_info=filter_related_user_info,
        filter_user_permissions_info=filter_user_permissions_info,
        filter_group_permissions_info=filter_group_permissions_info,
        filter_project_permissions_info=filter_project_permissions_info,
        filter_all_users_permissions=filter_all_users_permissions,
        filter_anonymous_permissions=filter_anonymous_permissions,
        filter_user_permissions=filter_user_permissions,
        filter_doi_info=filter_doi_info,
        show_filters=show_filters,
        all_actions=all_actions,
        filter_action_ids=filter_action_ids,
        all_instruments=all_instruments,
        filter_instrument_ids=filter_instrument_ids,
        all_action_types=all_action_types,
        filter_action_type_ids=filter_action_type_ids,
        all_locations=all_locations,
        filter_location_ids=filter_location_ids,
        filter_origins_info=filter_origins_info,
        filter_origin_ids=filter_origin_ids,
        all_publications=all_publications,
        all_components=all_components,
        filter_doi=filter_doi,
        get_object_if_current_user_has_read_permissions=get_object_if_current_user_has_read_permissions,
        build_modified_url=_build_modified_url,
        sorting_property=sorting_property_name,
        sorting_order=sorting_order_name,
        limit=pagination_limit,
        offset=pagination_offset,
        pagination_enabled=pagination_enabled,
        num_objects_found=num_objects_found,
        get_user=get_user,
        get_location=get_location,
        get_component=get_component,
        get_shares_for_object=get_shares_for_object,
        edit_location=edit_location,
        location_form=location_form,
        user_is_fed=user_is_fed,
        ENGLISH=english,
        all_languages=all_languages,
        objects_with_write_permission=objects_with_write_permission,
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
            'text': '{} (#{})'.format(flask.escape(get_translated_text(x.name_json)) or '—', x.object_id) if x.component_name is None
            else '{} (#{}, #{} @ {})'.format(flask.escape(get_translated_text(x.name_json)) or '—', x.object_id, x.fed_object_id, flask.escape(x.component_name)),
            'unescaped_text': '{} (#{})'.format(get_translated_text(x.name_json) or '—', x.object_id) if x.component_name is None
            else '{} (#{}, #{} @ {})'.format(get_translated_text(x.name_json) or '—', x.object_id, x.fed_object_id, x.component_name),
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


def _parse_filter_id_params(
        params: werkzeug.datastructures.ImmutableMultiDict,
        param_aliases: typing.List[str],
        valid_ids: typing.List[int],
        id_map: typing.Dict[str, int],
        multi_params_error: str,
        parse_error: str,
        invalid_id_error: str
) -> typing.Tuple[bool, typing.Optional[typing.List[int]]]:
    num_used_param_aliases = sum(param_alias in params for param_alias in param_aliases)
    if num_used_param_aliases == 0:
        return True, None
    if num_used_param_aliases > 1:
        flask.flash(multi_params_error, 'error')
        return False, None
    try:
        filter_ids = set()
        for param_alias in param_aliases:
            for ids_str in params.getlist(param_alias):
                for id_str in ids_str.split(','):
                    id_str = id_str.strip()
                    if not id_str:
                        continue
                    if id_str in id_map:
                        filter_ids.add(id_map[id_str])
                    else:
                        filter_ids.add(int(id_str))
    except ValueError:
        flask.flash(parse_error, 'error')
        return False, None
    if any(id not in valid_ids for id in filter_ids):
        flask.flash(invalid_id_error, 'error')
        return False, None
    return True, list(filter_ids)


def _parse_object_list_filters(
        params: werkzeug.datastructures.ImmutableMultiDict,
        valid_location_ids: typing.List[int],
        valid_action_type_ids: typing.List[int],
        valid_action_ids: typing.List[int],
        valid_instrument_ids: typing.List[int]
) -> typing.Tuple[
    bool,
    typing.Optional[typing.List[int]],
    typing.Optional[typing.List[int]],
    typing.Optional[typing.List[int]],
    typing.Optional[typing.List[int]],
    typing.Optional[int],
    typing.Optional[str],
    typing.Optional[Permissions],
    typing.Optional[Permissions],
    typing.Optional[int],
    typing.Optional[Permissions],
    typing.Optional[int],
    typing.Optional[Permissions],
    typing.Optional[int],
    typing.Optional[Permissions],
    typing.Optional[typing.List[typing.Union[typing.Tuple[typing.Literal['local'], None], typing.Tuple[typing.Literal['component'], int]]]]
]:
    FALLBACK_RESULT = False, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None
    success, filter_location_ids = _parse_filter_id_params(
        params=params,
        param_aliases=['location_ids', 'location'],
        valid_ids=valid_location_ids,
        id_map={},
        multi_params_error=_('Only one of location_ids and location may be set.'),
        parse_error=_('Unable to parse location IDs.'),
        invalid_id_error=_('Invalid location ID.')
    )
    if not success:
        return FALLBACK_RESULT

    success, filter_action_ids = _parse_filter_id_params(
        params=params,
        param_aliases=['action_ids', 'action'],
        valid_ids=valid_action_ids,
        id_map={},
        multi_params_error=_('Only one of action_ids and action may be set.'),
        parse_error=_('Unable to parse action IDs.'),
        invalid_id_error=_('Invalid action ID.')
    )
    if not success:
        return FALLBACK_RESULT

    success, filter_instrument_ids = _parse_filter_id_params(
        params=params,
        param_aliases=['instrument_ids'],
        valid_ids=valid_instrument_ids,
        id_map={},
        multi_params_error='',
        parse_error=_('Unable to parse instrument IDs.'),
        invalid_id_error=_('Invalid instrument ID.')
    )
    if not success:
        return FALLBACK_RESULT

    success, filter_action_type_ids = _parse_filter_id_params(
        params=params,
        param_aliases=['action_type_ids', 't'],
        valid_ids=valid_action_type_ids,
        id_map={
            'samples': models.ActionType.SAMPLE_CREATION,
            'measurements': models.ActionType.MEASUREMENT,
            'simulations': models.ActionType.SIMULATION
        },
        multi_params_error=_('Only one of action_type_ids and t may be set.'),
        parse_error=_('Unable to parse action type IDs.'),
        invalid_id_error=_('Invalid action type ID.')
    )
    if not success:
        return FALLBACK_RESULT

    if 'related_user' in params:
        try:
            filter_related_user_id = int(params.get('related_user'))
            check_user_exists(filter_related_user_id)
        except ValueError:
            flask.flash(_('Unable to parse related user ID.'), 'error')
            return FALLBACK_RESULT
        except UserDoesNotExistError:
            flask.flash(_('Invalid related user ID.'), 'error')
            return FALLBACK_RESULT
    else:
        filter_related_user_id = None

    try:
        filter_doi = logic.publications.simplify_doi(params.get('doi', ''))
    except logic.errors.InvalidDOIError:
        filter_doi = None

    if flask.current_app.config['ENABLE_ANONYMOUS_USERS']:
        filter_anonymous_permissions = {
            'read': Permissions.READ
        }.get(params.get('anonymous_permissions', '').lower(), None)
    else:
        filter_anonymous_permissions = None

    filter_all_users_permissions = {
        'read': Permissions.READ
    }.get(params.get('all_users_permissions', '').lower(), None)

    if 'user' in params:
        try:
            filter_user_id = int(params.get('user'))
            check_user_exists(filter_user_id)
        except ValueError:
            flask.flash(_('Unable to parse user ID.'), 'error')
            return FALLBACK_RESULT
        except UserDoesNotExistError:
            flask.flash(_('Invalid user ID.'), 'error')
            return FALLBACK_RESULT
        else:
            filter_user_permissions = {
                'read': Permissions.READ,
                'write': Permissions.WRITE,
                'grant': Permissions.GRANT
            }.get(params.get('user_permissions', '').lower(), Permissions.READ)
    else:
        filter_user_id = None
        filter_user_permissions = None

    if 'group' in params:
        try:
            filter_group_id = int(params.get('group'))
            group_member_ids = logic.groups.get_group_member_ids(filter_group_id)
        except ValueError:
            flask.flash(_('Unable to parse group ID.'), 'error')
            return FALLBACK_RESULT
        except logic.errors.GroupDoesNotExistError:
            flask.flash(_('Invalid group ID.'), 'error')
            return FALLBACK_RESULT
        else:
            if flask_login.current_user.id not in group_member_ids:
                flask.flash(_('You need to be a member of this group to list its objects.'), 'error')
                return FALLBACK_RESULT
            filter_group_permissions = {
                'read': Permissions.READ,
                'write': Permissions.WRITE,
                'grant': Permissions.GRANT
            }.get(params.get('group_permissions', '').lower(), Permissions.READ)
    else:
        filter_group_id = None
        filter_group_permissions = None

    if 'project' in params:
        try:
            filter_project_id = int(params.get('project'))
            get_project(filter_project_id)
        except ValueError:
            flask.flash(_('Unable to parse project ID.'), 'error')
            return FALLBACK_RESULT
        except logic.errors.ProjectDoesNotExistError:
            flask.flash(_('Invalid project ID.'), 'error')
            return FALLBACK_RESULT
        else:
            if Permissions.READ not in get_user_project_permissions(
                    project_id=filter_project_id,
                    user_id=flask_login.current_user.id,
                    include_groups=True
            ):
                flask.flash(_('You need to be a member of this project group to list its objects.'), 'error')
                return FALLBACK_RESULT
            filter_project_permissions = {
                'read': Permissions.READ,
                'write': Permissions.WRITE,
                'grant': Permissions.GRANT
            }.get(params.get('project_permissions', '').lower(), Permissions.READ)
    else:
        filter_project_id = None
        filter_project_permissions = None

    if params.getlist('origins'):
        filter_origin_ids = []
        for origin_id_str in params.getlist('origins'):
            if origin_id_str == 'local':
                filter_origin_ids.append(('local', None))
            elif origin_id_str.startswith('component_'):
                try:
                    component_id = int(origin_id_str.split('_', 1)[1])
                    check_component_exists(component_id)
                except ValueError:
                    flask.flash(_('Unable to parse database ID.'), 'error')
                    return FALLBACK_RESULT
                except logic.errors.ComponentDoesNotExistError:
                    flask.flash(_('Invalid database ID.'), 'error')
                    return FALLBACK_RESULT
                filter_origin_ids.append(('component', component_id))
            else:
                flask.flash(_('Unable to parse origin ID.'), 'error')
                return FALLBACK_RESULT
    else:
        filter_origin_ids = None

    return (
        True,
        filter_location_ids,
        filter_action_type_ids,
        filter_action_ids,
        filter_instrument_ids,
        filter_related_user_id,
        filter_doi,
        filter_anonymous_permissions,
        filter_all_users_permissions,
        filter_user_id,
        filter_user_permissions,
        filter_group_id,
        filter_group_permissions,
        filter_project_id,
        filter_project_permissions,
        filter_origin_ids,
    )


def _parse_object_list_options(
        params: werkzeug.datastructures.ImmutableMultiDict,
) -> typing.Tuple[
    typing.List[str],
    typing.List[str],
    typing.List[str],
    bool,
    typing.List[str],
]:
    creation_info = set()
    for creation_info_str in params.getlist('creation_info'):
        creation_info_str = creation_info_str.strip().lower()
        if creation_info_str in {'user', 'date'}:
            creation_info.add(creation_info_str)
    creation_info = list(creation_info)

    last_edit_info = set()
    for last_edit_info_str in params.getlist('last_edit_info'):
        last_edit_info_str = last_edit_info_str.strip().lower()
        if last_edit_info_str in {'user', 'date'}:
            last_edit_info.add(last_edit_info_str)
    last_edit_info = list(last_edit_info)

    action_info = set()
    for action_info_str in params.getlist('action_info'):
        action_info_str = action_info_str.strip().lower()
        if action_info_str in {'instrument', 'action'}:
            action_info.add(action_info_str)
    action_info = list(action_info)

    location_info = set()
    for location_info_str in params.getlist('location_info'):
        location_info_str = location_info_str.strip().lower()
        if location_info_str in {'location', 'responsible_user'}:
            location_info.add(location_info_str)
    location_info = list(location_info)

    other_databases_info = 'other_databases_info' in params
    return creation_info, last_edit_info, action_info, other_databases_info, location_info


def _parse_display_properties(
        params: werkzeug.datastructures.ImmutableMultiDict,
) -> typing.Tuple[
    typing.List[str],
    typing.Dict[str, str],
]:
    display_properties = []
    display_property_titles = {}
    for property_info in itertools.chain(*[
        display_properties_str.split(',')
        for display_properties_str in params.getlist('display_properties')
    ]):
        if ':' in property_info:
            property_name, property_title = property_info.split(':', 1)
        else:
            property_name, property_title = property_info, None
        if property_name not in display_properties:
            display_properties.append(property_name)
        if property_title is not None:
            display_property_titles[property_name] = flask.escape(property_title)
    return display_properties, display_property_titles


def _build_modified_url(
        blocked_parameters: typing.Sequence[str] = (),
        **query_parameters: typing.Any
) -> str:
    for param in flask.request.args:
        if param not in query_parameters:
            query_parameters[param] = flask.request.args.getlist(param)
    for param in blocked_parameters:
        if param in query_parameters:
            del query_parameters[param]
    return flask.url_for(
        '.objects',
        **query_parameters
    )


@frontend.route('/objects/', methods=['POST'])
@flask_login.login_required
def save_object_list_defaults():
    if 'save_default_filters' in flask.request.form:
        all_locations = get_locations_with_user_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.READ
        )
        all_action_types = logic.actions.get_action_types(
            filter_fed_defaults=True
        )
        all_actions = get_sorted_actions_for_user(
            user_id=flask_login.current_user.id
        )
        all_instruments = get_instruments()
        (
            success,
            filter_location_ids,
            filter_action_type_ids,
            filter_action_ids,
            filter_instrument_ids,
            filter_related_user_id,
            filter_doi,
            filter_anonymous_permissions,
            filter_all_users_permissions,
            filter_user_id,
            filter_user_permissions,
            filter_group_id,
            filter_group_permissions,
            filter_project_id,
            filter_project_permissions,
            filter_origin_ids,
        ) = _parse_object_list_filters(
            params=flask.request.form,
            valid_location_ids=[
                location.id
                for location in all_locations
            ],
            valid_action_type_ids=[
                action_type.id
                for action_type in all_action_types
            ],
            valid_action_ids=[
                action.id
                for action in all_actions
            ],
            valid_instrument_ids=[
                instrument.id
                for instrument in all_instruments
            ]
        )
        if not success:
            return flask.abort(400)
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_OBJECT_LIST_FILTERS': {
                    'filter_location_ids': filter_location_ids,
                    'filter_action_type_ids': filter_action_type_ids,
                    'filter_action_ids': filter_action_ids,
                    'filter_instrument_ids': filter_instrument_ids,
                    'filter_doi': filter_doi,
                    'filter_anonymous_permissions': None if filter_anonymous_permissions is None else filter_anonymous_permissions.name.lower(),
                    'filter_all_users_permissions': None if filter_all_users_permissions is None else filter_all_users_permissions.name.lower(),
                    'filter_user_id': filter_user_id,
                    'filter_user_permissions': None if filter_user_permissions is None else filter_user_permissions.name.lower(),
                    'filter_origin_ids': filter_origin_ids
                }
            }
        )
        return flask.redirect(_build_modified_url(blocked_parameters=OBJECT_LIST_FILTER_PARAMETERS))
    if 'save_default_options' in flask.request.form:
        (
            creation_info,
            last_edit_info,
            action_info,
            other_databases_info,
            location_info,
        ) = _parse_object_list_options(
            params=flask.request.form
        )
        display_properties, display_property_titles = _parse_display_properties(
            params=flask.request.form
        )
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_OBJECT_LIST_OPTIONS': {
                    'creation_info': creation_info,
                    'last_edit_info': last_edit_info,
                    'action_info': action_info,
                    'other_databases_info': other_databases_info,
                    'location_info': location_info,
                    'display_properties': display_properties
                }
            }
        )
        return flask.redirect(_build_modified_url(blocked_parameters=OBJECT_LIST_OPTION_PARAMETERS))
    if 'clear_default_filters' in flask.request.form:
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_OBJECT_LIST_FILTERS': {}
            }
        )
        return flask.redirect(_build_modified_url(blocked_parameters=OBJECT_LIST_FILTER_PARAMETERS))
    if 'clear_default_options' in flask.request.form:
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_OBJECT_LIST_OPTIONS': {}
            }
        )
        return flask.redirect(_build_modified_url(blocked_parameters=OBJECT_LIST_OPTION_PARAMETERS))


@frontend.route("/edit_locations", methods=["POST"])
def edit_multiple_locations():
    location_form = ObjectLocationAssignmentForm()
    selected_object_ids = flask.request.form["selected_objects"]
    selected_object_ids = list(map(int, selected_object_ids.split(","))) if selected_object_ids else []

    if not selected_object_ids:
        return flask.abort(400)

    for object_id in selected_object_ids:
        if logic.object_permissions.get_user_object_permissions(object_id, flask_login.current_user.id) < Permissions.WRITE:
            return flask.abort(403)

    location_form.location.choices = [('-1', '—')] + [
        (str(location.id), get_location_name(location, include_id=True))
        for location in get_locations_with_user_permissions(flask_login.current_user.id, Permissions.READ)
        if location.type is None or location.type.enable_object_assignments
    ]

    possible_resposible_users = [('-1', '-')]
    for user in get_users(exclude_hidden=not flask_login.current_user.is_admin):
        possible_resposible_users.append((str(user.id), user.get_name()))
    location_form.responsible_user.choices = possible_resposible_users

    if location_form.validate_on_submit():
        location_id = int(location_form.location.data)
        if location_id < 0:
            location_id = None
        responsible_user_id = int(location_form.responsible_user.data)
        if responsible_user_id < 0:
            responsible_user_id = None
        description = location_form.description.data
        try:
            description = json.loads(description)
        except Exception:
            description = {}
        valid_description = {'en': ''}
        for language_code, description_text in description.items():
            if not isinstance(language_code, str):
                continue
            try:
                language = get_language_by_lang_code(language_code)
            except logic.errors.LanguageDoesNotExistError:
                continue
            if not language.enabled_for_input:
                continue
            valid_description[language_code] = description_text
        description = valid_description
        if location_id is not None or responsible_user_id is not None:
            for object_id in selected_object_ids:
                logic.locations.assign_location_to_object(object_id, location_id, responsible_user_id, flask_login.current_user.id, description)
            flask.flash(_('Successfully assigned a new location to objects.'), 'success')
            return flask.redirect(flask.url_for('.objects', ids=','.join(map(str, selected_object_ids))))

    flask.flash(_('Please select a location or a responsible user.'), 'error')
    return flask.redirect(flask.url_for('.objects'))
