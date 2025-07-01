# coding: utf-8
"""

"""
import itertools
import json
import typing

import flask
import flask_login
import markupsafe
import werkzeug
from flask_babel import _

from .. import frontend
from ... import logic
from ... import models
from ...logic import user_log, object_sorting
from ...logic.instruments import get_instruments, get_instrument
from ...logic.actions import get_action, Action
from ...logic.action_types import get_action_type
from ...logic.action_permissions import get_sorted_actions_for_user
from ...logic.object_permissions import get_objects_with_permissions, get_object_info_with_permissions, ObjectInfo
from ...logic.users import get_user, get_users, get_users_by_name, check_user_exists, User
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
from ..utils import get_locations_form_data, get_location_name, get_search_paths, get_groups_form_data, parse_filter_id_params, build_modified_url
from ...logic.utils import get_translated_text, relative_url_for
from .forms import ObjectLocationAssignmentForm, UseInActionForm, GenerateLabelsForm, EditPermissionsForm
from .permissions import get_object_if_current_user_has_read_permissions
from ..labels import PAGE_SIZES, HORIZONTAL_LABEL_MARGIN, VERTICAL_LABEL_MARGIN
from ...models import Permissions
from ...utils import FlaskResponseT

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

OBJECT_LIST_FILTER_PARAMETERS = (
    'object_list_filters',
    'action_type_ids',
    't',
    'action_ids',
    'action',
    'instrument_ids',
    'related_user',
    'related_user_ids',
    'user',
    'user_permissions',
    'all_users_permissions',
    'anonymous_permissions',
    'location_ids',
    'location',
    'doi',
    'group',
    'group_permissions',
    'project',
    'project_permissions',
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
    'topic_info',
)


@frontend.route('/objects/')
@flask_login.login_required
def objects() -> FlaskResponseT:

    user_settings = get_user_settings(user_id=flask_login.current_user.id)
    if any(any(flask.request.args.getlist(param)) for param in OBJECT_LIST_OPTION_PARAMETERS):
        display_properties, display_property_titles = _parse_display_properties(flask.request.args)
    else:
        display_properties = user_settings['DEFAULT_OBJECT_LIST_OPTIONS'].get('display_properties', [])
        display_property_titles = {}

    all_instruments = get_instruments()
    all_actions_including_hidden = get_sorted_actions_for_user(
        user_id=flask_login.current_user.id,
        include_hidden_actions=True
    )
    all_action_types = logic.action_types.get_action_types(
        filter_fed_defaults=True
    )
    all_actions = [
        action
        for action in all_actions_including_hidden
        if not action.is_hidden
    ]
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
            'timeseries',
            'tags',
            'file',
        )
    )

    edit_location = flask.request.args.get('edit_location', default=False, type=lambda k: k.lower() == 'true')
    create_from_objects = flask.request.args.get('create_from_objects', default=False, type=lambda k: k.lower() == 'true')
    edit_permissions = flask.request.args.get('edit_permissions', default=False, type=lambda k: k.lower() == 'true')
    use_in_action_type_id = flask.request.args.get('use_in_action_type', default=None, type=int)
    generate_labels = flask.request.args.get('generate_labels', default=False, type=lambda k: k.lower() == 'true')

    name_only = True
    implicit_action_type = None
    object_ids_str = flask.request.args.get('ids', '')
    object_ids: typing.Optional[typing.Set[int]] = None
    if object_ids_str:
        try:
            object_ids = {
                int(object_id)
                for object_id in object_ids_str.split(',')
            }
        except ValueError:
            db_objects = []
        else:
            db_objects = get_objects_with_permissions(
                user_id=flask_login.current_user.id,
                permissions=Permissions.READ,
                object_ids=list(object_ids or set())
            )
            db_objects.sort(key=lambda db_object: db_object.object_id)
        query_string = ''
        use_advanced_search = False
        must_use_advanced_search = False
        advanced_search_had_error = False
        search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]] = []
        search_tree = None
        pagination_limit = None
        pagination_offset = None
        pagination_enabled = True
        num_objects_found = len(db_objects)
        sorting_enabled = False
        sorting_property_name = None
        sorting_order_name = None
        show_filters = False
        all_actions = []
        filter_action_ids: typing.Optional[typing.List[int]] = []
        all_instruments = []
        filter_instrument_ids: typing.Optional[typing.List[int]] = []
        all_action_types = []
        filter_action_type_ids: typing.Optional[typing.List[int]] = []
        all_locations = []
        filter_location_ids: typing.Optional[typing.List[int]] = []
        filter_related_user_ids = None
        all_users = []
        filter_doi = None
        filter_user_id = None
        filter_user_permissions = None
        filter_all_users_permissions = None
        filter_anonymous_permissions = None
        filter_group_id = None
        filter_group_permissions = None
        filter_project_id = None
        filter_project_permissions = None
        filter_origin_ids: typing.Optional[typing.List[typing.Union[typing.Tuple[typing.Literal['local'], None], typing.Tuple[typing.Literal['component'], int]]]] = None
        all_publications = []
        all_components = []
    else:
        pagination_enabled = True
        sorting_enabled = True

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
            for action in all_actions_including_hidden
        ]
        valid_instrument_ids = [
            instrument.id
            for instrument in all_instruments
        ]
        all_users = get_users(exclude_hidden=True, exclude_fed=True, exclude_eln_import=True)
        valid_user_ids = [
            user.id
            for user in all_users
        ]

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

        stored_filter_origin_ids = user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_origin_ids', None)
        if stored_filter_origin_ids:
            try:
                filter_origin_ids = []
                # ensure origins are valid
                for origin in stored_filter_origin_ids:
                    origin_type, origin_id = origin
                    if origin_type == 'local' and origin_id is None:
                        filter_origin_ids.append((origin_type, origin_id))
                        continue
                    if origin_type == 'component' and type(origin_id) is int:
                        filter_origin_ids.append((origin_type, origin_id))
                        continue
                    filter_origin_ids = None
                    break
            except Exception:
                filter_origin_ids = None
        else:
            filter_origin_ids = None

        stored_related_user_ids = user_settings['DEFAULT_OBJECT_LIST_FILTERS'].get('filter_related_user_ids', None)
        if stored_related_user_ids:
            filter_related_user_ids = []
            try:
                for stored_related_user_id in stored_related_user_ids:
                    logic.users.check_user_exists(stored_related_user_id)
                    filter_related_user_ids.append(stored_related_user_id)
            except logic.errors.UserDoesNotExistError:
                filter_related_user_ids = None
        else:
            filter_related_user_ids = None
        filter_group_id = None
        filter_group_permissions = None
        filter_project_id = None
        filter_project_permissions = None

        if any(any(flask.request.args.getlist(param)) for param in OBJECT_LIST_FILTER_PARAMETERS):
            (
                success,
                args_filter_location_ids,
                args_filter_action_type_ids,
                args_filter_action_ids,
                args_filter_instrument_ids,
                args_filter_related_user_ids,
                args_filter_doi,
                args_filter_anonymous_permissions,
                args_filter_all_users_permissions,
                args_filter_user_id,
                args_filter_user_permissions,
                args_filter_group_id,
                args_filter_group_permissions,
                args_filter_project_id,
                args_filter_project_permissions,
                args_filter_origin_ids,
            ) = _parse_object_list_filters(
                params=flask.request.args,
                valid_location_ids=valid_location_ids,
                valid_action_type_ids=valid_action_type_ids,
                valid_action_ids=valid_action_ids,
                valid_instrument_ids=valid_instrument_ids,
                valid_user_ids=valid_user_ids
            )
            if not success:
                return flask.abort(400)
            passed_filter_params = {
                param
                for param in OBJECT_LIST_FILTER_PARAMETERS
                if param in flask.request.args.keys()
            }
            if {'object_list_filters', 'location_ids', 'location'} & passed_filter_params:
                filter_location_ids = args_filter_location_ids
            if {'object_list_filters', 'action_type_ids', 't'} & passed_filter_params:
                filter_action_type_ids = args_filter_action_type_ids
            if {'object_list_filters', 'action_ids', 'action'} & passed_filter_params:
                filter_action_ids = args_filter_action_ids
            if {'object_list_filters', 'instrument_ids'} & passed_filter_params:
                filter_instrument_ids = args_filter_instrument_ids
            if {'object_list_filters', 'related_user', 'related_user_ids'} & passed_filter_params:
                filter_related_user_ids = args_filter_related_user_ids
            if {'object_list_filters', 'doi'} & passed_filter_params:
                filter_doi = args_filter_doi
            if {'object_list_filters', 'anonymous_permissions'} & passed_filter_params:
                filter_anonymous_permissions = args_filter_anonymous_permissions
            if {'object_list_filters', 'all_users_permissions'} & passed_filter_params:
                filter_all_users_permissions = args_filter_all_users_permissions
            if {'object_list_filters', 'user'} & passed_filter_params:
                filter_user_id = args_filter_user_id
            if {'object_list_filters', 'user_permissions'} & passed_filter_params:
                filter_user_permissions = args_filter_user_permissions
            if {'object_list_filters', 'group'} & passed_filter_params:
                filter_group_id = args_filter_group_id
            if {'object_list_filters', 'group_permissions'} & passed_filter_params:
                filter_group_permissions = args_filter_group_permissions
            if {'object_list_filters', 'project'} & passed_filter_params:
                filter_project_id = args_filter_project_id
            if {'object_list_filters', 'project_permissions'} & passed_filter_params:
                filter_project_permissions = args_filter_project_permissions
            if {'object_list_filters', 'component_id'} & passed_filter_params:
                filter_origin_ids = args_filter_origin_ids

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
                        display_property_titles[property_name] = markupsafe.escape(get_translated_text(action_schema['properties'][property_name]['title']))

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
        if not use_advanced_search and query_string:
            if filter_related_user_ids is None:
                users = get_users_by_name(query_string)
                if users:
                    filter_related_user_ids = [user.id for user in users]
                    query_string = ''
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
            filter_func_with_notes, search_tree, use_advanced_search = generate_filter_func(query_string, use_advanced_search, use_permissions_filter_for_referenced_objects=not flask_login.current_user.has_admin_permissions)
        except Exception:
            # TODO: ensure that advanced search does not cause exceptions
            if use_advanced_search:
                advanced_search_had_error = True

                def filter_func_with_notes(data: typing.Any, search_notes: typing.List[typing.Tuple[str, str, int, typing.Optional[int]]]) -> bool:
                    """ Return all objects"""
                    search_notes.append(('error', "Unable to parse search expression", 0, len(query_string)))
                    return False
            else:
                raise
        filter_func, search_notes = wrap_filter_func(filter_func_with_notes)

        if filter_location_ids is not None:
            object_ids_at_location = set()
            for location_id in filter_location_ids:
                object_ids_at_location.update(get_object_ids_at_location(location_id))
        else:
            object_ids_at_location = None
        if not filter_related_user_ids:
            object_ids_for_user = None
        else:
            object_ids_for_user = set()
            for filter_related_user_id in filter_related_user_ids:
                object_ids_for_user.update(user_log.get_user_related_object_ids(filter_related_user_id))
        if filter_doi is None:
            object_ids_for_doi = None
        else:
            object_ids_for_doi = set(logic.publications.get_object_ids_linked_to_doi(filter_doi))
        if filter_origin_ids is None:
            object_ids_for_origin_ids = None
        else:
            filter_local_objects = ('local', None) in filter_origin_ids
            filter_component_ids = {
                typing.cast(int, origin_id)
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
            object_ids = None
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
                db_objects = []
                num_objects_found = 0
            else:
                num_objects_found_list: typing.List[int] = []
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
                db_objects = get_objects_with_permissions(
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
                    object_ids=list(object_ids) if object_ids is not None else None,
                    num_objects_found=num_objects_found_list,
                    name_only=name_only
                )
                num_objects_found = num_objects_found_list[0]
        except Exception as exc:
            search_notes.append(('error', f"Error during search: {exc}", 0, 0))
            db_objects = []
            num_objects_found = 0
        if any(note[0] == 'error' for note in search_notes):
            db_objects = []
            advanced_search_had_error = True

    cached_actions: typing.Dict[typing.Optional[int], typing.Optional[Action]] = {None: None}
    if all_actions:
        for action in all_actions:
            cached_actions[action.id] = action
    cached_users: typing.Dict[typing.Optional[int], typing.Optional[User]] = {None: None}

    objects: typing.List[typing.Dict[str, typing.Any]] = []
    for i, obj in enumerate(db_objects):
        if obj.version_id == 0:
            original_object = obj
        else:
            original_object = get_object(object_id=obj.object_id, version_id=0)
        if obj.action_id is not None and obj.action_id not in cached_actions:
            cached_actions[obj.action_id] = get_action(obj.action_id)
        if obj.user_id is not None and obj.user_id not in cached_users:
            cached_users[obj.user_id] = get_user(obj.user_id)
        if original_object.user_id is not None and original_object.user_id not in cached_users:
            cached_users[original_object.user_id] = get_user(original_object.user_id)
        objects.append({
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
            'component': obj.component,
            'eln_import_id': obj.eln_import_id,
            'eln_object_id': obj.eln_object_id,
            'eln_import': obj.eln_import,
        })

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
            for object_id in action_ids:
                property_info = search_paths_by_action.get(object_id, {}).get(property_name)
                if property_info is not None and 'titles' in property_info:
                    property_titles.update(property_info['titles'])
            if property_titles:
                property_title = ', '.join(sorted(list(property_titles)))
            elif property_name in default_property_titles:
                property_title = markupsafe.escape(default_property_titles[property_name])
            else:
                property_title = markupsafe.escape(property_name)
            display_property_titles[property_name] = property_title

    if any(param in flask.request.args for param in OBJECT_LIST_OPTION_PARAMETERS):
        creation_info, last_edit_info, action_info, other_databases_info, location_info, topic_info = _parse_object_list_options(flask.request.args)
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
        topic_info = user_settings['DEFAULT_OBJECT_LIST_OPTIONS'].get('topic_info', [])
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

    if topic_info:
        object_ids = {
            object['object_id']
            for object in objects
        }
        topic_ids_by_object_ids = logic.topics.get_topic_ids_by_object_ids(list(object_ids), flask_login.current_user.id)
        for object in objects:
            if object['object_id'] in topic_ids_by_object_ids:
                object['topic_ids'] = topic_ids_by_object_ids[object['object_id']]
            else:
                object['topic_ids'] = {}
        topics_by_id = {
            topic.id: topic
            for topic in logic.topics.get_topics()
        }
    else:
        topics_by_id = {}

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

    filter_action_infos: typing.List[typing.Dict[str, typing.Any]] = []
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
            if action.user is not None:
                filter_action_infos[-1]['user'] = action.user
            if action.instrument is not None:
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

    if filter_related_user_ids is not None:
        filter_related_user_infos = []
        for filter_related_user_id in filter_related_user_ids:
            user = get_user(filter_related_user_id)
            filter_related_user_infos.append({
                'name': user.get_name(),
                'url': flask.url_for('.user_profile', user_id=filter_related_user_id),
                'fed_id': user.fed_id,
                'component_name': user.component.get_name() if user.component is not None else None,
                'eln_import_id': user.eln_import_id,
                'eln_object_id': user.eln_object_id,
            })
    else:
        filter_related_user_infos = None

    filter_user_permissions_info: typing.Optional[typing.Dict[str, typing.Any]]
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
                if origin_type == 'component' and origin_id is not None
            ]
        }
    else:
        filter_origins_info = None

    location_form = None
    use_in_action_form = None
    generate_labels_form = None
    edit_permissions_form = None
    user_is_fed: typing.Dict[str, bool] = {}
    english = None
    all_languages = []
    objects_allowed_to_select = []
    available_action_types = []
    favorite_actions = []
    use_in_action_type = None
    current_permissions_special_groups: typing.Dict[str, typing.Dict[int, str]] = {}
    current_permissions_normal_entities: typing.Dict[str, typing.Dict[int, typing.Dict[int, str]]] = {}
    groups_treepicker_info = None
    projects_treepicker_info = None
    if edit_location:
        location_form = ObjectLocationAssignmentForm()
        all_choices, choices = get_locations_form_data(filter=lambda location: location.enable_object_assignments and (location.type is None or location.type.enable_object_assignments))
        location_form.location.all_choices = all_choices
        location_form.location.choices = choices
        possible_resposible_users = [('-1', '-')]
        user_is_fed = {}
        for user in get_users(exclude_hidden=not flask_login.current_user.is_admin or not flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN']):
            possible_resposible_users.append((str(user.id), user.get_name()))
            user_is_fed[str(user.id)] = user.fed_id is not None
        location_form.responsible_user.choices = possible_resposible_users

        english = get_language(Language.ENGLISH)
        all_languages = get_languages()

        shown_object_ids = [object['object_id'] for object in objects]
        objects_allowed_to_select = [obj.id for obj in get_objects_with_permissions(user_id=flask_login.current_user.id, permissions=Permissions.WRITE, object_ids=shown_object_ids)]
    elif create_from_objects and use_in_action_type_id:
        use_in_action_form = UseInActionForm()
        use_in_action_type = logic.action_types.get_action_type(use_in_action_type_id)

        if use_in_action_type_id == models.ActionType.MEASUREMENT and logic.action_types.is_usable_in_action_types_table_empty():
            if not flask.current_app.config['DISABLE_USE_IN_MEASUREMENT']:
                for object in objects:
                    if object['action'] and object['action'].type_id == models.ActionType.SAMPLE_CREATION:
                        objects_allowed_to_select.append(object['object_id'])

        else:
            for object in objects:
                if object['action'] is None or object['action'].type is None:
                    continue

                if use_in_action_type in object['action'].type.usable_in_action_types:
                    objects_allowed_to_select.append(object['object_id'])

        all_favorite_action_ids = logic.favorites.get_user_favorite_action_ids(flask_login.current_user.id)

        actions = all_actions
        if not actions:
            actions = logic.actions.get_actions(action_type_id=use_in_action_type_id)

        for action in actions:
            if action.type_id == use_in_action_type_id and action.id in all_favorite_action_ids and action not in favorite_actions:
                favorite_actions.append(action)

    elif generate_labels:
        generate_labels_form = GenerateLabelsForm()
        objects_allowed_to_select = [object['object_id']
                                     for object in objects
                                     if object['action'] is not None and object['action'].type is not None and object['action'].type.enable_labels]

    elif edit_permissions:
        edit_permissions_form = EditPermissionsForm()

        current_permissions_special_groups = {'signed-in-users': {}}
        current_permissions_normal_entities = {'user': {}, 'project-group': {}, 'group': {}}

        if flask.current_app.config["ENABLE_ANONYMOUS_USERS"]:
            current_permissions_special_groups['anonymous'] = {}

        for object in objects:
            object_id = object['object_id']

            if logic.object_permissions.get_user_object_permissions(object_id, user_id=flask_login.current_user.id) < Permissions.GRANT:
                continue

            objects_allowed_to_select.append(object_id)

            current_permissions_special_groups['signed-in-users'][object_id] = logic.object_permissions.get_object_permissions_for_all_users(object_id).name.lower()

            if flask.current_app.config["ENABLE_ANONYMOUS_USERS"]:
                current_permissions_special_groups['anonymous'][object_id] = logic.object_permissions.get_object_permissions_for_anonymous_users(object_id).name.lower()

            for group_id, permission in logic.object_permissions.get_object_permissions_for_groups(object_id).items():
                if group_id not in current_permissions_normal_entities['group']:
                    current_permissions_normal_entities['group'][group_id] = {}
                current_permissions_normal_entities['group'][group_id][object_id] = permission.name.lower()

            for project_id, permission in logic.object_permissions.get_object_permissions_for_projects(object_id).items():
                if project_id not in current_permissions_normal_entities['project-group']:
                    current_permissions_normal_entities['project-group'][project_id] = {}
                current_permissions_normal_entities['project-group'][project_id][object_id] = permission.name.lower()

            for user_id, permission in logic.object_permissions.get_object_permissions_for_users(object_id).items():
                if user_id not in current_permissions_normal_entities['user']:
                    current_permissions_normal_entities['user'][user_id] = {}
                current_permissions_normal_entities['user'][user_id][object_id] = permission.name.lower()

        groups_treepicker_info = get_groups_form_data(basic_group_filter=lambda group: True)[1]
        projects_treepicker_info = get_groups_form_data(project_group_filter=lambda project: True)[1]

    else:
        create_from_objects = False
        if logic.action_types.is_usable_in_action_types_table_empty():
            if not flask.current_app.config['DISABLE_USE_IN_MEASUREMENT']:
                for object in objects:
                    if object['action'] and object['action'].type_id == models.ActionType.SAMPLE_CREATION:
                        available_action_types.append(logic.action_types.get_action_type(models.ActionType.MEASUREMENT))
                        break

        else:
            tried_object_action_types = {None}
            for object in objects:
                object_action = object['action']

                if object_action and object_action.type_id not in tried_object_action_types:
                    for action_type in object_action.type.usable_in_action_types:
                        if action_type not in available_action_types:
                            available_action_types.append(action_type)
                    tried_object_action_types.add(object_action.type_id)

    sorted_action_topics = []
    sorted_instrument_topics = []
    if not flask.current_app.config['DISABLE_TOPICS']:
        sorted_topics = logic.topics.get_topics()
        for topic in sorted_topics:
            for action in all_actions:
                if topic in action.topics:
                    sorted_action_topics.append(topic)
                    break
            if not flask.current_app.config['DISABLE_INSTRUMENTS']:
                for instrument in all_instruments:
                    if topic in instrument.topics:
                        sorted_instrument_topics.append(topic)
                        break

    def _build_modified_url(
        blocked_parameters: typing.Sequence[str] = (),
        **query_parameters: typing.Any
    ) -> str:
        return build_modified_url('.objects', blocked_parameters, **query_parameters)

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
        topic_info=topic_info,
        topics_by_id=topics_by_id,
        object_name_plural=object_name_plural,
        filter_action_type_infos=filter_action_type_infos,
        filter_action_infos=filter_action_infos,
        filter_instrument_infos=filter_instrument_infos,
        filter_location_infos=filter_location_infos,
        filter_related_user_infos=filter_related_user_infos,
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
        all_users=all_users,
        filter_related_user_ids=filter_related_user_ids,
        filter_origins_info=filter_origins_info,
        filter_origin_ids=filter_origin_ids,
        all_publications=all_publications,
        all_components=all_components,
        filter_doi=filter_doi,
        get_object_if_current_user_has_read_permissions=get_object_if_current_user_has_read_permissions,
        build_modified_url=_build_modified_url,
        sorting_enabled=sorting_enabled,
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
        create_from_objects=create_from_objects,
        objects_allowed_to_select=objects_allowed_to_select,
        available_action_types=available_action_types,
        use_in_action_type=use_in_action_type,
        favorite_actions=favorite_actions,
        use_in_action_form=use_in_action_form,
        generate_labels_form=generate_labels_form,
        generate_labels=generate_labels,
        PAGE_SIZES=PAGE_SIZES,
        HORIZONTAL_LABEL_MARGIN=HORIZONTAL_LABEL_MARGIN,
        VERTICAL_LABEL_MARGIN=VERTICAL_LABEL_MARGIN,
        edit_permissions=edit_permissions,
        edit_permissions_form=edit_permissions_form,
        current_permissions_special_groups=current_permissions_special_groups,
        current_permissions_normal_entities=current_permissions_normal_entities,
        groups_treepicker_info=groups_treepicker_info,
        projects_treepicker_info=projects_treepicker_info,
        sorted_action_topics=sorted_action_topics,
        sorted_instrument_topics=sorted_instrument_topics,
    )


@frontend.route('/objects/referencable')
@flask_login.login_required
def referencable_objects() -> FlaskResponseT:
    required_perm = Permissions.READ
    if 'required_perm' in flask.request.args:
        try:
            required_perm = Permissions.from_name(flask.request.args['required_perm'])
        except ValueError:
            try:
                required_perm = Permissions(int(flask.request.args['required_perm']))
            except ValueError:
                return flask.jsonify({
                    "message": f"argument {flask.request.args['required_perm']} is not a valid permission."
                }), 400

    action_ids = None
    if 'action_ids' in flask.request.args:
        action_ids_str = flask.request.args['action_ids']
        try:
            action_ids = json.loads(action_ids_str)
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

    def dictify(x: ObjectInfo) -> typing.Dict[str, typing.Any]:
        name = get_translated_text(x.name_json) or '—'
        if x.component_name is not None:
            name += f' (#{x.object_id}, #{x.fed_object_id} @ {x.component_name})'
        elif x.eln_import_id is not None:
            name += f' (#{x.object_id}, {x.eln_object_id} @ {_(".eln file")}) #{x.eln_import_id}'
        else:
            name += f' (#{x.object_id})'
        return {
            'id': x.object_id,
            'text': markupsafe.escape(name),
            'unescaped_text': name,
            'action_id': x.action_id,
            'max_permission': x.max_permission,
            'tags': [markupsafe.escape(tag) for tag in x.tags['tags']] if x.tags and isinstance(x.tags, dict) and x.tags.get('_type') == 'tags' and x.tags.get('tags') else [],
            'is_fed': x.fed_object_id is not None,
            'is_eln_imported': x.eln_import_id is not None,
        }

    return flask.jsonify({
        'referencable_objects': [
            dictify(object)
            for object in referencable_objects
        ]
    })


def _parse_object_list_filters(
        params: werkzeug.datastructures.MultiDict[str, str],
        valid_location_ids: typing.List[int],
        valid_action_type_ids: typing.List[int],
        valid_action_ids: typing.List[int],
        valid_instrument_ids: typing.List[int],
        valid_user_ids: typing.List[int]
) -> typing.Tuple[
    bool,
    typing.Optional[typing.List[int]],
    typing.Optional[typing.List[int]],
    typing.Optional[typing.List[int]],
    typing.Optional[typing.List[int]],
    typing.Optional[typing.List[int]],
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
    success, filter_location_ids = parse_filter_id_params(
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

    success, filter_action_ids = parse_filter_id_params(
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

    success, filter_instrument_ids = parse_filter_id_params(
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

    success, filter_action_type_ids = parse_filter_id_params(
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

    success, filter_related_user_ids = parse_filter_id_params(
        params=params,
        param_aliases=['related_user_ids', 'related_user'],
        valid_ids=valid_user_ids,
        id_map={},
        multi_params_error=_('Only one of related_user_ids and related_user may be set.'),
        parse_error=_('Unable to parse related user IDs.'),
        invalid_id_error=_('Invalid related user ID.')
    )
    if not success:
        return FALLBACK_RESULT

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
            filter_user_id = int(params['user'])
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
            filter_group_id = int(params['group'])
            group_member_ids = logic.groups.get_group_member_ids(filter_group_id)
        except ValueError:
            flask.flash(_('Unable to parse group ID.'), 'error')
            return FALLBACK_RESULT
        except logic.errors.GroupDoesNotExistError:
            flask.flash(_('Invalid group ID.'), 'error')
            return FALLBACK_RESULT
        else:
            if flask_login.current_user.id not in group_member_ids and not flask_login.current_user.has_admin_permissions:
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
            filter_project_id = int(params['project'])
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
            ) and not flask_login.current_user.has_admin_permissions:
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

    filter_origin_ids: typing.Optional[typing.List[typing.Union[typing.Tuple[typing.Literal['local'], None], typing.Tuple[typing.Literal['component'], int]]]]
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
        filter_related_user_ids,
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
        params: werkzeug.datastructures.MultiDict[str, str],
) -> typing.Tuple[
    typing.List[str],
    typing.List[str],
    typing.List[str],
    bool,
    typing.List[str],
    typing.List[str],
]:
    creation_info_set = set()
    for creation_info_str in params.getlist('creation_info'):
        creation_info_str = creation_info_str.strip().lower()
        if creation_info_str in {'user', 'date'}:
            creation_info_set.add(creation_info_str)
    creation_info = list(creation_info_set)

    last_edit_info_set = set()
    for last_edit_info_str in params.getlist('last_edit_info'):
        last_edit_info_str = last_edit_info_str.strip().lower()
        if last_edit_info_str in {'user', 'date'}:
            last_edit_info_set.add(last_edit_info_str)
    last_edit_info = list(last_edit_info_set)

    action_info_set = set()
    for action_info_str in params.getlist('action_info'):
        action_info_str = action_info_str.strip().lower()
        if action_info_str in {'instrument', 'action'}:
            action_info_set.add(action_info_str)
    action_info = list(action_info_set)

    location_info_set = set()
    for location_info_str in params.getlist('location_info'):
        location_info_str = location_info_str.strip().lower()
        if location_info_str in {'location', 'responsible_user'}:
            location_info_set.add(location_info_str)
    location_info = list(location_info_set)

    topic_info_set = set()
    for topic_info_str in params.getlist('topic_info'):
        topic_info_str = topic_info_str.strip().lower()
        if topic_info_str in {'topics'}:
            topic_info_set.add(topic_info_str)
    topic_info = list(topic_info_set)

    other_databases_info = 'other_databases_info' in params
    return creation_info, last_edit_info, action_info, other_databases_info, location_info, topic_info


def _parse_display_properties(
        params: werkzeug.datastructures.MultiDict[str, str],
) -> typing.Tuple[
    typing.List[str],
    typing.Dict[str, typing.Union[str, markupsafe.Markup]],
]:
    display_properties = []
    display_property_titles: typing.Dict[str, typing.Union[str, markupsafe.Markup]] = {}
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
            display_property_titles[property_name] = markupsafe.escape(property_title)
    return display_properties, display_property_titles


@frontend.route('/objects/', methods=['POST'])
@flask_login.login_required
def save_object_list_defaults() -> FlaskResponseT:
    if 'save_default_filters' in flask.request.form:
        all_locations = get_locations_with_user_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.READ
        )
        all_action_types = logic.action_types.get_action_types(
            filter_fed_defaults=True
        )
        all_actions = get_sorted_actions_for_user(
            user_id=flask_login.current_user.id,
            include_hidden_actions=True
        )
        all_instruments = get_instruments()
        all_users = get_users(exclude_hidden=True, exclude_fed=True, exclude_eln_import=True)
        (
            success,
            filter_location_ids,
            filter_action_type_ids,
            filter_action_ids,
            filter_instrument_ids,
            filter_related_user_ids,
            filter_doi,
            filter_anonymous_permissions,
            filter_all_users_permissions,
            filter_user_id,
            filter_user_permissions,
            _filter_group_id,
            _filter_group_permissions,
            _filter_project_id,
            _filter_project_permissions,
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
            ],
            valid_user_ids=[
                user.id
                for user in all_users
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
                    'filter_origin_ids': filter_origin_ids,
                    'filter_related_user_ids': filter_related_user_ids
                }
            }
        )
        return flask.redirect(build_modified_url('.objects', blocked_parameters=OBJECT_LIST_FILTER_PARAMETERS))
    if 'save_default_options' in flask.request.form:
        (
            creation_info,
            last_edit_info,
            action_info,
            other_databases_info,
            location_info,
            topic_info,
        ) = _parse_object_list_options(
            params=flask.request.form
        )
        display_properties, _display_property_titles = _parse_display_properties(
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
                    'topic_info': topic_info,
                    'display_properties': display_properties
                }
            }
        )
        return flask.redirect(build_modified_url('.objects', blocked_parameters=OBJECT_LIST_OPTION_PARAMETERS))
    if 'clear_default_filters' in flask.request.form:
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_OBJECT_LIST_FILTERS': {}
            }
        )
        return flask.redirect(build_modified_url('.objects', blocked_parameters=OBJECT_LIST_FILTER_PARAMETERS))
    if 'clear_default_options' in flask.request.form:
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_OBJECT_LIST_OPTIONS': {}
            }
        )
        return flask.redirect(build_modified_url('.objects', blocked_parameters=OBJECT_LIST_OPTION_PARAMETERS))
    return flask.abort(400)


@frontend.route("/edit_locations", methods=["POST"])
@flask_login.login_required
def edit_multiple_locations() -> FlaskResponseT:
    location_form = ObjectLocationAssignmentForm()
    selected_object_ids_str = flask.request.form["selected_objects"]
    selected_object_ids = list(map(int, selected_object_ids_str.split(","))) if selected_object_ids_str else []

    if not selected_object_ids:
        return flask.abort(400)

    for object_id in selected_object_ids:
        if logic.object_permissions.get_user_object_permissions(object_id, flask_login.current_user.id) < Permissions.WRITE:
            return flask.abort(403)

    location_form.location.choices = [('-1', '—')] + [
        (str(location.id), get_location_name(location, include_id=True))
        for location in get_locations_with_user_permissions(flask_login.current_user.id, Permissions.READ)
        if location.enable_object_assignments and (location.type is None or location.type.enable_object_assignments)
    ]

    possible_resposible_users = [('-1', '-')]
    for user in get_users(exclude_hidden=not flask_login.current_user.is_admin or not flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN']):
        possible_resposible_users.append((str(user.id), user.get_name()))
    location_form.responsible_user.choices = possible_resposible_users

    location_id: typing.Optional[int]
    responsible_user_id: typing.Optional[int]
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
        if location_id is not None:
            location = get_location(location_id)
            if location.type.enable_capacities:
                action_ids_for_object_ids = logic.objects.get_action_ids_for_object_ids(selected_object_ids)
                selected_action_ids = [
                    typing.cast(int, action_ids_for_object_ids[object_id])
                    for object_id in selected_object_ids
                    if action_ids_for_object_ids.get(object_id) is not None
                ]
                action_type_ids_for_action_ids = logic.actions.get_action_type_ids_for_action_ids(selected_action_ids)
                selected_action_type_ids = [
                    typing.cast(int, action_type_ids_for_action_ids[action_id])
                    for action_id in selected_action_ids
                    if action_type_ids_for_action_ids.get(action_id) is not None
                ]
                action_types = logic.action_types.get_action_types()
                action_type_id_aliases = {
                    action_type.id: action_type.fed_id
                    for action_type in action_types
                    if action_type.fed_id is not None and action_type.fed_id < 0
                }
                selected_action_type_ids = [
                    action_type_id_aliases.get(action_type_id, action_type_id)
                    for action_type_id in selected_action_type_ids
                ]
                location_capacities = logic.locations.get_location_capacities(location_id)
                num_stored_objects = logic.locations.get_assigned_object_count_by_action_types(location_id, ignored_object_ids=selected_object_ids)
                for action_type_id in set(selected_action_type_ids):
                    location_capacity = location_capacities.get(action_type_id, 0)
                    if location_capacity is not None and num_stored_objects.get(action_type_id, 0) + selected_action_type_ids.count(action_type_id) > location_capacity:
                        flask.flash(_('The selected location does not have the capacity to store these objects.'), 'error')
                        return flask.redirect(flask.url_for('.objects'))
        if location_id is not None or responsible_user_id is not None:
            for object_id in selected_object_ids:
                logic.locations.assign_location_to_object(object_id, location_id, responsible_user_id, flask_login.current_user.id, description)
            flask.flash(_('Successfully assigned a new location to objects.'), 'success')
            return flask.redirect(flask.url_for('.objects', ids=','.join(map(str, selected_object_ids))))

    flask.flash(_('Please select a location or a responsible user.'), 'error')
    return flask.redirect(flask.url_for('.objects'))


@frontend.route("/multiselect_action", methods=["POST"])
@flask_login.login_required
def multiselect_action() -> FlaskResponseT:
    use_in_action_form = UseInActionForm()

    try:
        object_ids = list(map(int, use_in_action_form.objects.data.split(',')))
    except ValueError:
        object_ids = []

    if use_in_action_form.action_id.data:
        return flask.redirect(flask.url_for('.new_object', action_id=use_in_action_form.action_id.data, object_id=object_ids))

    return flask.redirect(flask.url_for('.actions', t=use_in_action_form.action_type_id.data, object_id=object_ids))


@frontend.route("/multiselect_permissions", methods=["POST"])
@flask_login.login_required
def multiselect_permissions() -> FlaskResponseT:
    edit_permissions_form = EditPermissionsForm()

    if edit_permissions_form.validate_on_submit():
        object_ids = list(map(int, edit_permissions_form.objects.data.split(',')))
        permission = Permissions.from_name(edit_permissions_form.permission.data)
        update_mode = edit_permissions_form.update_mode.data
        current_permission: typing.Optional[Permissions] = None

        for object_id in object_ids:
            if logic.object_permissions.get_user_object_permissions(object_id, flask_login.current_user.id) < Permissions.GRANT:
                flask.abort(403)

        if edit_permissions_form.target_type.data == 'anonymous':
            if permission > Permissions.READ:
                flask.flash(_('It is not allowed to use permissions higher than read for special groups.'), 'error')
                return flask.redirect(flask.url_for('.objects'))

            for object_id in object_ids:
                current_permission = logic.object_permissions.get_object_permissions_for_anonymous_users(object_id)
                if update_mode == 'set-min' and current_permission < permission or update_mode == 'set-max' and current_permission > permission:
                    logic.object_permissions.set_object_permissions_for_anonymous_users(object_id, permission)

        elif edit_permissions_form.target_type.data == 'signed-in-users':
            if permission > Permissions.READ:
                flask.flash(_('It is not allowed to use permissions higher than read for special groups.'), 'error')
                return flask.redirect(flask.url_for('.objects'))
            for object_id in object_ids:
                current_permission = logic.object_permissions.get_object_permissions_for_all_users(object_id)
                if update_mode == 'set-min' and current_permission < permission or update_mode == 'set-max' and current_permission > permission:
                    logic.object_permissions.set_object_permissions_for_all_users(object_id, permission)

        elif edit_permissions_form.target_type.data == 'group':
            try:
                group_id = int(edit_permissions_form.groups.data)
            except ValueError:
                flask.abort(400)

            for object_id in object_ids:
                current_permission = logic.object_permissions.get_object_permissions_for_groups(object_id).get(group_id)
                if current_permission is None:
                    current_permission = Permissions.NONE
                if update_mode == 'set-min' and current_permission < permission or update_mode == 'set-max' and current_permission > permission:
                    logic.object_permissions.set_group_object_permissions(object_id, group_id, permission)

        elif edit_permissions_form.target_type.data == 'project-group':
            try:
                project_id = int(edit_permissions_form.project_groups.data)
            except ValueError:
                flask.abort(400)

            for object_id in object_ids:
                current_permission = logic.object_permissions.get_object_permissions_for_projects(object_id).get(project_id)
                if current_permission is None:
                    current_permission = Permissions.NONE
                if update_mode == 'set-min' and current_permission < permission or update_mode == 'set-max' and current_permission > permission:
                    logic.object_permissions.set_project_object_permissions(object_id, project_id, permission)
        elif edit_permissions_form.target_type.data == 'user':
            try:
                user_id = int(edit_permissions_form.users.data)
            except ValueError:
                flask.abort(400)

            for object_id in object_ids:
                current_permission = logic.object_permissions.get_object_permissions_for_users(object_id).get(user_id)
                if current_permission is None:
                    current_permission = Permissions.NONE
                if (update_mode == 'set-min' and current_permission < permission) or (update_mode == 'set-max' and current_permission > permission):
                    logic.object_permissions.set_user_object_permissions(object_id, user_id, permission)

        flask.flash(_('Updated permissions successfully.'), 'success')
        return flask.redirect(flask.url_for('.objects', ids=edit_permissions_form.objects.data))
    return flask.redirect(flask.url_for('.objects'))
