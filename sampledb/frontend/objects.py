# coding: utf-8
"""

"""

from copy import deepcopy
import datetime
import io
import json
import math
import os
import zipfile

import flask
import flask_login
import itsdangerous
import werkzeug.utils

from . import frontend
from .. import logic
from ..logic import user_log, object_log, comments, object_sorting
from ..logic.actions import ActionType, get_action
from ..logic.action_permissions import get_user_action_permissions
from ..logic.object_permissions import Permissions, get_user_object_permissions, object_is_public, get_object_permissions_for_users, set_object_public, set_user_object_permissions, set_group_object_permissions, set_project_object_permissions, get_objects_with_permissions, get_object_permissions_for_groups, get_object_permissions_for_projects, request_object_permissions
from ..logic.datatypes import JSONEncoder
from ..logic.users import get_user, get_users, get_users_by_name
from ..logic.schemas import validate, generate_placeholder
from ..logic.settings import get_user_settings, set_user_settings
from ..logic.object_search import generate_filter_func, wrap_filter_func
from ..logic.groups import get_group, get_user_groups
from ..logic.objects import create_object, create_object_batch, update_object, get_object, get_object_versions
from ..logic.object_log import ObjectLogEntryType
from ..logic.projects import get_project, get_user_projects, get_user_project_permissions
from ..logic.locations import get_location, get_object_ids_at_location, get_object_location_assignment, get_object_location_assignments, get_locations, assign_location_to_object, get_locations_tree
from ..logic.files import FileLogEntryType
from ..logic.errors import GroupDoesNotExistError, ObjectDoesNotExistError, UserDoesNotExistError, ActionDoesNotExistError, ValidationError, ProjectDoesNotExistError, LocationDoesNotExistError
from .objects_forms import ObjectPermissionsForm, ObjectForm, ObjectVersionRestoreForm, ObjectUserPermissionsForm, CommentForm, ObjectGroupPermissionsForm, ObjectProjectPermissionsForm, FileForm, FileInformationForm, FileHidingForm, ObjectLocationAssignmentForm, ExternalLinkForm, ObjectPublicationForm, CopyPermissionsForm
from ..utils import object_permissions_required
from .utils import jinja_filter, generate_qrcode
from .object_form_parser import parse_form_data
from .labels import create_labels, PAGE_SIZES, DEFAULT_PAPER_FORMAT, HORIZONTAL_LABEL_MARGIN, VERTICAL_LABEL_MARGIN, mm
from . import pdfexport
from .utils import check_current_user_is_not_readonly


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def on_unauthorized(object_id):
    permissions_by_user = get_object_permissions_for_users(object_id)
    has_grant_user = any(
        Permissions.GRANT in permissions
        for permissions in permissions_by_user.values()
    )
    return flask.render_template('objects/unauthorized.html', object_id=object_id, has_grant_user=has_grant_user), 403


@frontend.route('/objects/')
@flask_login.login_required
def objects():
    object_ids = flask.request.args.get('ids', '')
    objects = []
    if object_ids:
        object_ids = object_ids.split(',')
        try:
            object_ids = [int(object_id) for object_id in object_ids]
        except ValueError:
            object_ids = []

        readable_object_ids = []
        for object_id in object_ids:
            if Permissions.READ in get_user_object_permissions(object_id, user_id=flask_login.current_user.id):
                readable_object_ids.append(object_id)
        object_ids = readable_object_ids
        for object_id in object_ids:
            try:
                objects.append(get_object(object_id))
            except logic.errors.ObjectDoesNotExistError:
                pass
        action_id = None
        action = None
        action_type = None
        project_id = None
        location_id = None
        location = None
        user = None
        user_id = None
        doi = None
        object_ids_at_location = None
        project = None
        query_string = ''
        use_advanced_search = False
        must_use_advanced_search = False
        advanced_search_had_error = False
        search_notes = []
        search_tree = None
        limit = None
        offset = None
        pagination_enabled = True
        num_objects_found = len(objects)
        sorting_property_name = None
        sorting_order_name = None
    else:
        pagination_enabled = True
        try:
            user_id = int(flask.request.args.get('user', ''))
            user = get_user(user_id)
        except ValueError:
            user_id = None
            user = None
        except UserDoesNotExistError:
            user_id = None
            user = None
        try:
            doi = logic.publications.simplify_doi(flask.request.args.get('doi', ''))
        except logic.errors.InvalidDOIError:
            doi = None
        try:
            location_id = int(flask.request.args.get('location', ''))
            location = get_location(location_id)
            object_ids_at_location = get_object_ids_at_location(location_id)
        except ValueError:
            location_id = None
            location = None
            object_ids_at_location = None
        except LocationDoesNotExistError:
            location_id = None
            location = None
            object_ids_at_location = None
        try:
            action_id = int(flask.request.args.get('action', ''))
        except ValueError:
            action_id = None
        if action_id is not None:
            action = get_action(action_id)
            action_type = action.type
        else:
            action = None
            action_type = flask.request.args.get('t', '')
            action_type = {
                'samples': ActionType.SAMPLE_CREATION,
                'measurements': ActionType.MEASUREMENT,
                'simulations': ActionType.SIMULATION
            }.get(action_type, None)
        try:
            project_id = int(flask.request.args.get('project', ''))
        except ValueError:
            project_id = None
        if project_id is not None:
            if Permissions.READ not in get_user_project_permissions(project_id=project_id, user_id=flask_login.current_user.id, include_groups=True):
                return flask.abort(403)
            project = get_project(project_id)
        else:
            project = None

        if flask.request.args.get('limit', '') == 'all':
            limit = None
        else:
            try:
                limit = int(flask.request.args.get('limit', ''))
            except ValueError:
                limit = None
            else:
                if limit <= 0:
                    limit = None
                elif limit >= 1000:
                    limit = 1000

            # default objects per page
            if limit is None:
                limit = get_user_settings(flask_login.current_user.id)['OBJECTS_PER_PAGE']
            else:
                set_user_settings(flask_login.current_user.id, {'OBJECTS_PER_PAGE': limit})

        try:
            offset = int(flask.request.args.get('offset', ''))
        except ValueError:
            offset = None
        else:
            if offset < 0:
                offset = None
            elif offset > 100000000:
                offset = 100000000
        if limit is not None and offset is None:
            offset = 0

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
        search_tree = None
        use_advanced_search = flask.request.args.get('advanced', None) is not None
        must_use_advanced_search = use_advanced_search
        advanced_search_had_error = False
        additional_search_notes = []
        if not use_advanced_search and query_string:
            if user_id is None:
                users = get_users_by_name(query_string)
                if len(users) == 1:
                    user = users[0]
                    user_id = user.id
                    query_string = ''
                elif len(users) > 1:
                    additional_search_notes.append(('error', "There are multiple users with this name.", 0, 0))
            if doi is None and query_string.startswith('doi:'):
                try:
                    doi = logic.publications.simplify_doi(query_string)
                    query_string = ''
                except logic.errors.InvalidDOIError:
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
        if user_id is None:
            object_ids_for_user = None
        else:
            object_ids_for_user = user_log.get_user_related_object_ids(user_id)
        if doi is None:
            object_ids_for_doi = None
        else:
            object_ids_for_doi = logic.publications.get_object_ids_linked_to_doi(doi)
        if use_advanced_search and not must_use_advanced_search:
            search_notes.append(('info', "The advanced search was used automatically. Search for \"{}\" to use the simple search.".format(query_string), 0, 0))
        try:
            object_ids = None
            if object_ids_at_location is not None:
                if object_ids is None:
                    object_ids = set()
                object_ids = object_ids.union(object_ids_at_location)
            if object_ids_for_user is not None:
                if object_ids is None:
                    object_ids = set()
                object_ids = object_ids.union(object_ids_for_user)
            if object_ids_for_doi is not None:
                if object_ids is None:
                    object_ids = set()
                object_ids = object_ids.union(object_ids_for_doi)
            if object_ids:
                pagination_enabled = False
                limit = None
                offset = None
            num_objects_found_list = []
            objects = get_objects_with_permissions(
                user_id=flask_login.current_user.id,
                permissions=Permissions.READ,
                filter_func=filter_func,
                sorting_func=sorting_function,
                limit=limit,
                offset=offset,
                action_id=action_id,
                action_type=action_type,
                project_id=project_id,
                object_ids=object_ids,
                num_objects_found=num_objects_found_list
            )
            num_objects_found = num_objects_found_list[0]
        except Exception as e:
            search_notes.append(('error', "Error during search: {}".format(e), 0, 0))
            objects = []
            num_objects_found = 0
        if any(note[0] == 'error' for note in search_notes):
            objects = []
            advanced_search_had_error = True

    for i, obj in enumerate(objects):
        if obj.version_id == 0:
            original_object = obj
        else:
            original_object = get_object(object_id=obj.object_id, version_id=0)
        objects[i] = {
            'object_id': obj.object_id,
            'version_id': obj.version_id,
            'created_by': get_user(original_object.user_id),
            'created_at': original_object.utc_datetime.strftime('%Y-%m-%d'),
            'modified_by': get_user(obj.user_id),
            'last_modified_at': obj.utc_datetime.strftime('%Y-%m-%d'),
            'data': obj.data,
            'schema': obj.schema,
            'action': get_action(obj.action_id),
            'display_properties': {}
        }

    # TODO: select display_properties? nested display_properties? find common properties? use searched for properties?
    display_properties = []
    display_property_titles = {}
    sample_ids = set()
    measurement_ids = set()
    if action is not None:
        action_schema = action.schema
        display_properties = action_schema.get('displayProperties', [])
        for property_name in display_properties:
            display_property_titles[property_name] = action_schema['properties'][property_name]['title']

    for obj in objects:
        for property_name in display_properties:
            if property_name not in obj['data'] or '_type' not in obj['data'][property_name] or property_name not in obj['schema']['properties']:
                obj['display_properties'][property_name] = None
                continue
            obj['display_properties'][property_name] = (obj['data'][property_name], obj['schema']['properties'][property_name])
            if obj['schema']['properties'][property_name]['type'] == 'sample':
                sample_ids.add(obj['data'][property_name]['object_id'])
            elif obj['schema']['properties'][property_name]['type'] == 'measurement':
                measurement_ids.add(obj['data'][property_name]['object_id'])

    samples = {
        sample_id: get_object(object_id=sample_id)
        for sample_id in sample_ids
    }
    measurements = {
        measurement_id: get_object(object_id=measurement_id)
        for measurement_id in measurement_ids
    }
    if action_id is None:
        show_action = True
    else:
        show_action = False

    def build_modified_url(**kwargs):
        return flask.url_for(
            '.objects',
            **{k: v for k, v in flask.request.args.items() if k not in kwargs},
            **kwargs
        )
    return flask.render_template(
        'objects/objects.html',
        objects=objects,
        display_properties=display_properties,
        display_property_titles=display_property_titles,
        search_query=query_string,
        action=action,
        action_id=action_id,
        action_type=action_type,
        ActionType=ActionType,
        project=project,
        project_id=project_id,
        location_id=location_id,
        location=location,
        user_id=user_id,
        user=user,
        doi=doi,
        samples=samples,
        measurements=measurements,
        build_modified_url=build_modified_url,
        sorting_property=sorting_property_name,
        sorting_order=sorting_order_name,
        limit=limit,
        offset=offset,
        pagination_enabled=pagination_enabled,
        num_objects_found=num_objects_found,
        show_action=show_action,
        use_advanced_search=use_advanced_search,
        must_use_advanced_search=must_use_advanced_search,
        advanced_search_had_error=advanced_search_had_error,
        search_notes=search_notes,
        search_tree=search_tree
    )


@jinja_filter
def to_datatype(obj):
    return json.loads(json.dumps(obj), object_hook=JSONEncoder.object_hook)


def get_sub_data_and_schema(data, schema, id_prefix):
    sub_data = data
    sub_schema = schema
    try:
        for key in id_prefix.split('__'):
            if sub_schema['type'] == 'array':
                key = int(key)
                sub_schema = sub_schema['items']
            elif sub_schema['type'] == 'object':
                sub_schema = sub_schema['properties'][key]
            else:
                raise ValueError('invalid type')
            if isinstance(key, int):
                while key >= len(sub_data):
                    sub_data.append(generate_placeholder(sub_schema))
            elif key not in sub_data:
                sub_data[key] = generate_placeholder(sub_schema)
            sub_data = sub_data[key]
        if sub_schema['type'] != 'array':
            raise ValueError('invalid type')
    except (ValueError, KeyError, IndexError, TypeError):
        # TODO: error handling/logging?
        raise ValueError('invalid action')
    return sub_data, sub_schema


def apply_action_to_form_data(action, form_data):
    new_form_data = form_data
    action_id_prefix, action_index, action_type = action[len('action_'):].rsplit('__', 2)
    if action_type == 'delete':
        deleted_item_index = int(action_index)
        parent_id_prefix = action_id_prefix
        new_form_data = {}
        for name in form_data:
            if not name.startswith(parent_id_prefix):
                new_form_data[name] = form_data[name]
            else:
                item_index, id_suffix = name[len(parent_id_prefix) + 2:].split('__', 1)
                item_index = int(item_index)
                if item_index < deleted_item_index:
                    new_form_data[name] = form_data[name]
                if item_index > deleted_item_index:
                    new_name = parent_id_prefix + '__' + str(item_index - 1) + '__' + id_suffix
                    new_form_data[new_name] = form_data[name]
    return new_form_data


def apply_action_to_data(action, data, schema):
    action_id_prefix, action_index, action_type = action[len('action_'):].rsplit('__', 2)
    if action_type not in ('add', 'delete', 'addcolumn', 'deletecolumn'):
        raise ValueError('invalid action')
    sub_data, sub_schema = get_sub_data_and_schema(data, schema, action_id_prefix.split('__', 1)[1])
    if action_type in ('addcolumn', 'deletecolumn') and (sub_schema["style"] != "table" or sub_schema["items"]["type"] != "array"):
        raise ValueError('invalid action')
    num_existing_items = len(sub_data)
    if action_type == 'add':
        if 'maxItems' not in sub_schema or num_existing_items < sub_schema["maxItems"]:
            sub_data.append(generate_placeholder(sub_schema["items"]))
    elif action_type == 'delete':
        action_index = int(action_index)
        if ('minItems' not in sub_schema or num_existing_items > sub_schema["minItems"]) and action_index < num_existing_items:
            del sub_data[action_index]
    else:
        num_existing_columns = sub_schema["items"].get("minItems", 1)
        for row in sub_data:
            num_existing_columns = max(num_existing_columns, len(row))
        if action_type == 'addcolumn':
            if 'maxItems' not in sub_schema["items"] or num_existing_columns < sub_schema["items"]["maxItems"]:
                num_existing_columns += 1
                for row in sub_data:
                    while len(row) < num_existing_columns:
                        row.append(generate_placeholder(sub_schema["items"]["items"]))
        elif action_type == 'deletecolumn':
            if num_existing_columns > sub_schema.get("minItems", 1):
                num_existing_columns -= 1
                for row in sub_data:
                    while len(row) > num_existing_columns:
                        del row[-1]


def show_object_form(object, action, previous_object=None, should_upgrade_schema=False, placeholder_data=None):
    if object is None and previous_object is None:
        data = generate_placeholder(action.schema)
        if placeholder_data:
            for path, value in placeholder_data.items():
                try:
                    sub_data = data
                    for step in path[:-1]:
                        sub_data = sub_data[step]
                    sub_data[path[-1]] = value
                except Exception:
                    # Ignore invalid placeholder data
                    pass
    elif object is None and previous_object is not None:
        data = previous_object.data
    else:
        data = object.data
    previous_object_schema = None
    mode = 'edit'
    if should_upgrade_schema:
        mode = 'upgrade'
        assert object is not None
        schema = action.schema
        data, upgrade_warnings = logic.schemas.convert_to_schema(object.data, object.schema, action.schema)
        for upgrade_warning in upgrade_warnings:
            flask.flash(upgrade_warning, 'warning')
    elif object is not None:
        schema = object.schema
    elif previous_object is not None:
        schema = previous_object.schema
        previous_object_schema = schema
    else:
        schema = action.schema

    if action is not None and action.instrument is not None and flask_login.current_user in action.instrument.responsible_users:
        may_create_log_entry = True
        create_log_entry_default = action.instrument.create_log_entry_default
        instrument_log_categories = logic.instrument_log_entries.get_instrument_log_categories(action.instrument.id)
        if 'create_instrument_log_entry' in flask.request.form:
            category_ids = []
            for category_id in flask.request.form.getlist('instrument_log_categories'):
                try:
                    if int(category_id) in [category.id for category in instrument_log_categories]:
                        category_ids.append(int(category_id))
                except Exception:
                    pass
        else:
            category_ids = None
    else:
        instrument_log_categories = None
        category_ids = None
        create_log_entry_default = None
        may_create_log_entry = False

    if object is None and 'copy_permissions_from_other_object' in flask.request.form and 'copy_permissions_object_id' in flask.request.form:
        copy_permissions_object_id = flask.request.form.get('copy_permissions_object_id')
        try:
            copy_permissions_object_id = int(copy_permissions_object_id)
            if Permissions.READ not in get_user_object_permissions(copy_permissions_object_id, flask_login.current_user.id):
                copy_permissions_object_id = None
        except Exception:
            pass
    else:
        copy_permissions_object_id = None

    if previous_object is not None:
        action_id = previous_object.action_id
        previous_object_id = previous_object.id
        has_grant_for_previous_object = Permissions.GRANT in get_user_object_permissions(user_id=flask_login.current_user.id, object_id=previous_object_id)
    else:
        action_id = action.id
        previous_object_id = None
        has_grant_for_previous_object = False
    errors = []
    object_errors = {}
    form_data = {}
    previous_actions = []
    serializer = itsdangerous.URLSafeSerializer(flask.current_app.config['SECRET_KEY'])
    form = ObjectForm()
    if flask.request.method != 'GET' and form.validate_on_submit():
        raw_form_data = {key: flask.request.form.getlist(key) for key in flask.request.form}
        form_data = {k: v[0] for k, v in raw_form_data.items()}

        if 'input_num_batch_objects' in form_data:
            try:
                num_objects_in_batch = int(form_data['input_num_batch_objects'])
            except ValueError:
                try:
                    # The form allows notations like '1.2e1' for '12', however
                    # Python can only parse these as floats
                    num_objects_in_batch = float(form_data['input_num_batch_objects'])
                    if num_objects_in_batch == int(num_objects_in_batch):
                        num_objects_in_batch = int(num_objects_in_batch)
                    else:
                        raise
                except ValueError:
                    errors.append('input_num_batch_objects')
                    num_objects_in_batch = None
                else:
                    form_data['input_num_batch_objects'] = str(num_objects_in_batch)
            else:
                form_data['input_num_batch_objects'] = str(num_objects_in_batch)
        else:
            num_objects_in_batch = None

        if 'previous_actions' in flask.request.form:
            try:
                previous_actions = serializer.loads(flask.request.form['previous_actions'])
            except itsdangerous.BadData:
                flask.abort(400)

        if "action_submit" in form_data:
            # The object name might need the batch number to match the pattern
            if schema.get('batch', False) and num_objects_in_batch is not None:
                batch_base_name = form_data['object__name__text']
                name_suffix_format = schema.get('batch_name_format', '{:d}')
                try:
                    name_suffix_format.format(1)
                except (ValueError, KeyError):
                    name_suffix_format = '{:d}'
                if name_suffix_format:
                    example_name_suffix = name_suffix_format.format(1)
                else:
                    example_name_suffix = ''
                raw_form_data['object__name__text'] = [batch_base_name + example_name_suffix]
            else:
                batch_base_name = None
                name_suffix_format = None
            object_data, object_errors = parse_form_data(raw_form_data, schema)
            errors += object_errors
            if object_data is not None and not errors:
                try:
                    validate(object_data, schema)
                except ValidationError:
                    # TODO: proper logging
                    print('object schema validation failed')
                    # TODO: handle error
                    flask.abort(400)
                if object is None:
                    if schema.get('batch', False) and num_objects_in_batch is not None:
                        if 'name' in object_data and 'text' in object_data['name'] and name_suffix_format is not None and batch_base_name is not None:
                            data_sequence = []
                            for i in range(1, num_objects_in_batch + 1):
                                if name_suffix_format:
                                    name_suffix = name_suffix_format.format(i)
                                else:
                                    name_suffix = ''
                                object_data['name']['text'] = batch_base_name + name_suffix
                                data_sequence.append(deepcopy(object_data))
                        else:
                            data_sequence = [object_data] * num_objects_in_batch
                        objects = create_object_batch(action_id=action.id, data_sequence=data_sequence, user_id=flask_login.current_user.id, copy_permissions_object_id=copy_permissions_object_id)
                        object_ids = [object.id for object in objects]
                        if category_ids is not None:
                            log_entry = logic.instrument_log_entries.create_instrument_log_entry(
                                instrument_id=action.instrument.id,
                                user_id=flask_login.current_user.id,
                                content='',
                                category_ids=category_ids
                            )
                            for object_id in object_ids:
                                logic.instrument_log_entries.create_instrument_log_object_attachment(
                                    instrument_log_entry_id=log_entry.id,
                                    object_id=object_id
                                )
                        flask.flash('The objects were created successfully.', 'success')
                        return flask.redirect(flask.url_for('.objects', ids=','.join([str(object_id) for object_id in object_ids])))
                    else:
                        object = create_object(action_id=action.id, data=object_data, user_id=flask_login.current_user.id, previous_object_id=previous_object_id, schema=previous_object_schema, copy_permissions_object_id=copy_permissions_object_id)
                        if category_ids is not None:
                            log_entry = logic.instrument_log_entries.create_instrument_log_entry(
                                instrument_id=action.instrument.id,
                                user_id=flask_login.current_user.id,
                                content='',
                                category_ids=category_ids
                            )
                            logic.instrument_log_entries.create_instrument_log_object_attachment(
                                instrument_log_entry_id=log_entry.id,
                                object_id=object.id
                            )
                        flask.flash('The object was created successfully.', 'success')
                else:
                    update_object(object_id=object.id, user_id=flask_login.current_user.id, data=object_data, schema=schema)
                    flask.flash('The object was updated successfully.', 'success')
                return flask.redirect(flask.url_for('.object', object_id=object.id))
        elif any(name.startswith('action_object__') and (name.endswith('__delete') or name.endswith('__add') or name.endswith('__addcolumn') or name.endswith('__deletecolumn')) for name in form_data):
            action = [name for name in form_data if name.startswith('action_')][0]
            previous_actions.append(action)

    if previous_actions:
        try:
            for action in previous_actions:
                apply_action_to_data(action, data, schema)
            form_data = apply_action_to_form_data(previous_actions[-1], form_data)
        except ValueError:
            flask.abort(400)

    # TODO: make this search more narrow
    samples = get_objects_with_permissions(
        user_id=flask_login.current_user.id,
        permissions=Permissions.READ,
        action_type=ActionType.SAMPLE_CREATION
    )
    measurements = get_objects_with_permissions(
        user_id=flask_login.current_user.id,
        permissions=Permissions.READ,
        action_type=ActionType.MEASUREMENT
    )
    if object is not None:
        samples = [
            sample
            for sample in samples
            if sample.object_id != object.object_id
        ]
        measurements = [
            measurement
            for measurement in measurements
            if measurement.object_id != object.object_id
        ]

    existing_objects = get_objects_with_permissions(
        user_id=flask_login.current_user.id,
        permissions=Permissions.GRANT
    )

    tags = [{'name': tag.name, 'uses': tag.uses} for tag in logic.tags.get_tags()]
    if object is None:
        return flask.render_template(
            'objects/forms/form_create.html',
            action_id=action_id,
            schema=schema,
            data=data,
            errors=errors,
            object_errors=object_errors,
            form_data=form_data,
            previous_actions=serializer.dumps(previous_actions),
            form=form,
            samples=samples,
            measurements=measurements,
            can_copy_permissions=True,
            existing_objects=existing_objects,
            datetime=datetime,
            tags=tags,
            may_create_log_entry=may_create_log_entry,
            instrument_log_categories=instrument_log_categories,
            create_log_entry_default=create_log_entry_default,
            previous_object_id=previous_object_id,
            has_grant_for_previous_object=has_grant_for_previous_object
        )
    else:
        return flask.render_template(
            'objects/forms/form_edit.html',
            schema=schema,
            data=data,
            object_id=object.object_id,
            errors=errors,
            object_errors=object_errors,
            form_data=form_data,
            previous_actions=serializer.dumps(previous_actions),
            form=form,
            samples=samples,
            measurements=measurements,
            datetime=datetime,
            tags=tags,
            mode=mode
        )


@frontend.route('/objects/<int:object_id>', methods=['GET', 'POST'])
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object(object_id):
    object = get_object(object_id=object_id)
    related_objects_tree = logic.object_relationships.build_related_objects_tree(object_id, flask_login.current_user.id)

    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    user_may_edit = Permissions.WRITE in user_permissions
    user_may_grant = Permissions.GRANT in user_permissions
    action = get_action(object.action_id)
    if action.schema != object.schema:
        new_schema_available = True
    else:
        new_schema_available = False
    if not user_may_edit and flask.request.args.get('mode', '') == 'edit':
        return flask.abort(403)
    if not user_may_edit and flask.request.args.get('mode', '') == 'upgrade':
        return flask.abort(403)
    if flask.request.method == 'GET' and flask.request.args.get('mode', '') not in ('edit', 'upgrade'):
        # TODO: make this search more narrow
        samples = get_objects_with_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.READ,
            action_type=ActionType.SAMPLE_CREATION
        )
        measurements = get_objects_with_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.READ,
            action_type=ActionType.MEASUREMENT
        )
        instrument = action.instrument
        object_type = {
            ActionType.SAMPLE_CREATION: "Sample",
            ActionType.MEASUREMENT: "Measurement",
            ActionType.SIMULATION: "Simulation"
        }.get(action.type, "Object")
        object_log_entries = object_log.get_object_log_entries(object_id=object_id, user_id=flask_login.current_user.id)

        if user_may_edit:
            serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
            token = serializer.dumps([flask_login.current_user.id, object_id])
            mobile_upload_url = flask.url_for('.mobile_file_upload', object_id=object_id, token=token, _external=True)
            mobile_upload_qrcode = generate_qrcode(mobile_upload_url, should_cache=False)
        else:
            mobile_upload_url = None
            mobile_upload_qrcode = None

        object_url = flask.url_for('.object', object_id=object_id, _external=True)
        object_qrcode = generate_qrcode(object_url, should_cache=True)

        location_form = ObjectLocationAssignmentForm()
        locations_map, locations_tree = get_locations_tree()
        locations = [('-1', '—')]
        unvisited_location_ids_prefixes_and_subtrees = [(location_id, '', locations_tree[location_id]) for location_id in locations_tree]
        while unvisited_location_ids_prefixes_and_subtrees:
            location_id, prefix, subtree = unvisited_location_ids_prefixes_and_subtrees.pop(0)
            location = locations_map[location_id]
            locations.append((str(location_id), '{}{} (#{})'.format(prefix, location.name, location.id)))
            for location_id in sorted(subtree, key=lambda location_id: locations_map[location_id].name, reverse=True):
                unvisited_location_ids_prefixes_and_subtrees.insert(0, (location_id, '{}{} / '.format(prefix, location.name), subtree[location_id]))

        location_form.location.choices = locations
        possible_responsible_users = [('-1', '—')]
        for user in logic.users.get_users(exclude_hidden=True):
            possible_responsible_users.append((str(user.id), '{} (#{})'.format(user.name, user.id)))
        location_form.responsible_user.choices = possible_responsible_users

        measurement_actions = logic.actions.get_actions(logic.actions.ActionType.MEASUREMENT)
        favorite_action_ids = logic.favorites.get_user_favorite_action_ids(flask_login.current_user.id)
        favorite_measurement_actions = [
            action
            for action in measurement_actions
            if action.id in favorite_action_ids and not action.is_hidden
        ]
        # Sort by: instrument name (independent actions first), action name
        favorite_measurement_actions.sort(key=lambda action: (
            action.user.name.lower() if action.user else '',
            action.instrument.name.lower() if action.instrument else '',
            action.name.lower()
        ))

        publication_form = ObjectPublicationForm()

        object_publications = logic.publications.get_publications_for_object(object_id=object.id)
        user_may_link_publication = Permissions.WRITE in user_permissions

        notebook_templates = object.schema.get('notebookTemplates', [])
        for notebook_template in notebook_templates:
            for parameter, parameter_value in notebook_template['params'].items():
                if parameter_value == 'object_id':
                    notebook_template['params'][parameter] = object_id
                elif isinstance(parameter_value, list):
                    parameter_data = object.data
                    for step in parameter_value:
                        if isinstance(step, str) and isinstance(parameter_data, dict) and step in parameter_data:
                            parameter_data = parameter_data[step]
                        elif isinstance(step, int) and isinstance(parameter_data, list) and 0 <= step < len(parameter_data):
                            parameter_data = parameter_data[step]
                        else:
                            parameter_data = None
                    notebook_template['params'][parameter] = parameter_data
                else:
                    notebook_template['params'][parameter] = None

        def build_object_location_assignment_confirmation_url(object_location_assignment_id: int) -> None:
            confirmation_url = flask.url_for(
                'frontend.accept_responsibility_for_object',
                t=logic.security_tokens.generate_token(
                    object_location_assignment_id,
                    salt='confirm_responsibility',
                    secret_key=flask.current_app.config['SECRET_KEY']
                ),
                _external=True
            )
            return confirmation_url

        return flask.render_template(
            'objects/view/base.html',
            object_type=object_type,
            action=action,
            instrument=instrument,
            schema=object.schema,
            data=object.data,
            object_log_entries=object_log_entries,
            ObjectLogEntryType=ObjectLogEntryType,
            last_edit_datetime=object.utc_datetime,
            last_edit_user=get_user(object.user_id),
            object_id=object_id,
            user_may_edit=user_may_edit,
            user_may_comment=user_may_edit,
            comments=comments.get_comments_for_object(object_id),
            comment_form=CommentForm(),
            files=logic.files.get_files_for_object(object_id),
            file_source_instrument_exists=False,
            file_source_jupyterhub_exists=False,
            file_form=FileForm(),
            external_link_form=ExternalLinkForm(),
            external_link_invalid='invalid_link' in flask.request.args,
            mobile_upload_url=mobile_upload_url,
            mobile_upload_qrcode=mobile_upload_qrcode,
            notebook_templates=notebook_templates,
            object_qrcode=object_qrcode,
            object_url=object_url,
            restore_form=None,
            version_id=object.version_id,
            user_may_grant=user_may_grant,
            samples=samples,
            measurements=measurements,
            favorite_measurement_actions=favorite_measurement_actions,
            FileLogEntryType=FileLogEntryType,
            file_information_form=FileInformationForm(),
            file_hiding_form=FileHidingForm(),
            new_schema_available=new_schema_available,
            related_objects_tree=related_objects_tree,
            object_publications=object_publications,
            user_may_link_publication=user_may_link_publication,
            publication_form=publication_form,
            get_object=get_object,
            get_object_location_assignment=get_object_location_assignment,
            get_user=get_user,
            get_location=get_location,
            PAGE_SIZES=PAGE_SIZES,
            HORIZONTAL_LABEL_MARGIN=HORIZONTAL_LABEL_MARGIN,
            VERTICAL_LABEL_MARGIN=VERTICAL_LABEL_MARGIN,
            mm=mm,
            object_location_assignments=get_object_location_assignments(object_id),
            build_object_location_assignment_confirmation_url=build_object_location_assignment_confirmation_url,
            user_may_assign_location=user_may_edit,
            location_form=location_form
        )
    check_current_user_is_not_readonly()
    if flask.request.args.get('mode', '') == 'upgrade':
        should_upgrade_schema = True
    else:
        should_upgrade_schema = False
    return show_object_form(object, action=get_action(object.action_id), should_upgrade_schema=should_upgrade_schema)


@frontend.route('/objects/<int:object_id>/dc.rdf')
@frontend.route('/objects/<int:object_id>/versions/<int:version_id>/dc.rdf')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_rdf(object_id, version_id=None):
    rdf_xml = logic.rdf.generate_rdf(flask_login.current_user.id, object_id, version_id)
    return flask.Response(
        rdf_xml,
        mimetype='application/rdf+xml',
    )


@frontend.route('/objects/<int:object_id>/label')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def print_object_label(object_id):
    mode = flask.request.args.get('mode', 'mixed')
    if mode == 'fixed-width':
        create_mixed_labels = False
        create_long_labels = False
        include_qrcode_in_long_labels = None
        paper_format = flask.request.args.get('width-paper-format', '')
        if paper_format not in PAGE_SIZES:
            paper_format = DEFAULT_PAPER_FORMAT
        maximum_width = math.floor(PAGE_SIZES[paper_format][0] / mm - 2 * HORIZONTAL_LABEL_MARGIN)
        maximum_height = math.floor(PAGE_SIZES[paper_format][1] / mm - 2 * VERTICAL_LABEL_MARGIN)
        ghs_classes_side_by_side = 'side-by-side' in flask.request.args
        label_minimum_width = 20
        if ghs_classes_side_by_side:
            label_minimum_width = 40
        try:
            label_width = float(flask.request.args.get('label-width', '20'))
        except ValueError:
            label_width = 0
        if math.isnan(label_width):
            label_width = 0
        if label_width < label_minimum_width:
            label_width = label_minimum_width
        if label_width > maximum_width:
            label_width = maximum_width
        try:
            label_minimum_height = float(flask.request.args.get('label-minimum-height', '0'))
        except ValueError:
            label_minimum_height = 0
        if math.isnan(label_minimum_height):
            label_minimum_height = 0
        if label_minimum_height < 0:
            label_minimum_height = 0
        if label_minimum_height > maximum_height:
            label_minimum_height = maximum_height
        qrcode_width = 18
        centered = 'centered' in flask.request.args
    elif mode == 'minimum-height':
        create_mixed_labels = False
        create_long_labels = True
        paper_format = flask.request.args.get('height-paper-format', '')
        if paper_format not in PAGE_SIZES:
            paper_format = DEFAULT_PAPER_FORMAT
        maximum_width = math.floor(PAGE_SIZES[paper_format][0] / mm - 2 * HORIZONTAL_LABEL_MARGIN)
        include_qrcode_in_long_labels = 'include-qrcode' in flask.request.args
        label_width = 0
        label_minimum_height = 0
        try:
            label_minimum_width = float(flask.request.args.get('label-minimum-width', '0'))
        except ValueError:
            label_minimum_width = 0
        if math.isnan(label_minimum_width):
            label_minimum_width = 0
        if label_minimum_width < 0:
            label_minimum_width = 0
        if label_minimum_width > maximum_width:
            label_minimum_width = maximum_width
        qrcode_width = 0
        ghs_classes_side_by_side = None
        centered = None
    else:
        create_mixed_labels = True
        create_long_labels = None
        include_qrcode_in_long_labels = None
        paper_format = flask.request.args.get('mixed-paper-format', '')
        if paper_format not in PAGE_SIZES:
            paper_format = DEFAULT_PAPER_FORMAT
        label_width = 0
        label_minimum_height = 0
        qrcode_width = 0
        label_minimum_width = 0
        ghs_classes_side_by_side = None
        centered = None

    object = get_object(object_id=object_id)
    object_log_entries = object_log.get_object_log_entries(object_id=object_id, user_id=flask_login.current_user.id)
    for object_log_entry in object_log_entries:
        if object_log_entry.type in (ObjectLogEntryType.CREATE_OBJECT, ObjectLogEntryType.CREATE_BATCH):
            creation_date = object_log_entry.utc_datetime.strftime('%Y-%m-%d')
            creation_user = get_user(object_log_entry.user_id).name
            break
    else:
        creation_date = 'Unknown'
        creation_user = 'Unknown'
    if 'created' in object.data and '_type' in object.data['created'] and object.data['created']['_type'] == 'datetime':
        creation_date = object.data['created']['utc_datetime'].split(' ')[0]
    if 'name' in object.data and '_type' in object.data['name'] and object.data['name']['_type'] == 'text':
        object_name = object.data['name']['text']
    else:
        object_name = 'Unknown Sample'

    object_url = flask.url_for('.object', object_id=object_id, _external=True)

    if 'hazards' in object.data and '_type' in object.data['hazards'] and object.data['hazards']['_type'] == 'hazards':
        hazards = object.data['hazards']['hazards']
    else:
        hazards = []

    pdf_data = create_labels(
        object_id=object_id,
        object_name=object_name,
        object_url=object_url,
        creation_user=creation_user,
        creation_date=creation_date,
        ghs_classes=hazards,
        paper_format=paper_format,
        create_mixed_labels=create_mixed_labels,
        create_long_labels=create_long_labels,
        include_qrcode_in_long_labels=include_qrcode_in_long_labels,
        label_width=label_width,
        label_minimum_height=label_minimum_height,
        label_minimum_width=label_minimum_width,
        qrcode_width=qrcode_width,
        ghs_classes_side_by_side=ghs_classes_side_by_side,
        centered=centered
    )
    return flask.send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        cache_timeout=-1
    )


@frontend.route('/objects/<int:object_id>/comments/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_comments(object_id):
    check_current_user_is_not_readonly()
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        content = comment_form.content.data
        comments.create_comment(object_id=object_id, user_id=flask_login.current_user.id, content=content)
        flask.flash('Successfully posted a comment.', 'success')
    else:
        flask.flash('Please enter a comment text.', 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/objects/search/')
@flask_login.login_required
def search():
    return flask.render_template('search.html')


@frontend.route('/objects/<int:object_id>/permissions/request', methods=['POST'])
@flask_login.login_required
def object_permissions_request(object_id):
    current_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    if Permissions.READ in current_permissions:
        flask.flash('You already have permissions to access this object.', 'error')
        return flask.redirect(flask.url_for('.object', object_id=object_id))
    request_object_permissions(flask_login.current_user.id, object_id)
    flask.flash('Your request for permissions has been sent.', 'success')
    return flask.redirect(flask.url_for('.objects'))


@frontend.route('/objects/<int:object_id>/locations/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_location(object_id):
    check_current_user_is_not_readonly()
    location_form = ObjectLocationAssignmentForm()
    location_form.location.choices = [('-1', '—')] + [
        (str(location.id), '{} (#{})'.format(location.name, location.id))
        for location in get_locations()
    ]
    possible_responsible_users = [('-1', '—')]
    for user in logic.users.get_users(exclude_hidden=True):
        possible_responsible_users.append((str(user.id), '{} (#{})'.format(user.name, user.id)))
    location_form.responsible_user.choices = possible_responsible_users
    if location_form.validate_on_submit():
        location_id = int(location_form.location.data)
        if location_id < 0:
            location_id = None
        responsible_user_id = int(location_form.responsible_user.data)
        if responsible_user_id < 0:
            responsible_user_id = None
        description = location_form.description.data
        if location_id is not None or responsible_user_id is not None:
            assign_location_to_object(object_id, location_id, responsible_user_id, flask_login.current_user.id, description)
            flask.flash('Successfully assigned a new location to this object.', 'success')
        else:
            flask.flash('Please select a location or a responsible user.', 'error')
    else:
        flask.flash('Please select a location or a responsible user.', 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/objects/<int:object_id>/publications/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_publication(object_id):
    check_current_user_is_not_readonly()
    publication_form = ObjectPublicationForm()
    if publication_form.validate_on_submit():
        doi = publication_form.doi.data
        title = publication_form.title.data
        object_name = publication_form.object_name.data
        if title is not None:
            title = title.strip()
        if not title:
            title = None
        if object_name is not None:
            object_name = object_name.strip()
        if not object_name:
            object_name = None
        existing_publication = ([
            publication
            for publication in logic.publications.get_publications_for_object(object_id)
            if publication.doi == doi
        ] or [None])[0]
        if existing_publication is not None and existing_publication.title == title and existing_publication.object_name == object_name:
            flask.flash('This object has already been linked to this publication.', 'info')
        else:
            logic.publications.link_publication_to_object(user_id=flask_login.current_user.id, object_id=object_id, doi=doi, title=title, object_name=object_name)
            if existing_publication is None:
                flask.flash('Successfully linked this object to a publication.', 'success')
            else:
                flask.flash('Successfully updated the information for this publication.', 'success')
    else:
        flask.flash('Please enter a valid DOI for the publication you want to link this object to.', 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/objects/<int:object_id>/export')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def export_data(object_id):
    object_ids = [object_id]
    file_extension = flask.request.args.get('format', '.pdf')
    if file_extension != '.pdf' and file_extension not in logic.export.FILE_FORMATS:
        return flask.abort(400)
    if 'object_ids' in flask.request.args:
        try:
            object_ids = json.loads(flask.request.args['object_ids'])
            object_ids = [int(i) for i in object_ids]
            if any((Permissions.READ not in get_user_object_permissions(i, flask_login.current_user.id)) for i in object_ids):
                return flask.abort(400)
        except Exception:
            return flask.abort(400)
        if not object_ids:
            return flask.abort(400)
    if file_extension == '.pdf':
        sections = pdfexport.SECTIONS
        if 'sections' in flask.request.args:
            try:
                sections = sections.intersection(json.loads(flask.request.args['sections']))
            except Exception:
                return flask.abort(400)
        pdf_data = pdfexport.create_pdfexport(object_ids, sections)
        file_bytes = io.BytesIO(pdf_data)
    elif file_extension in logic.export.FILE_FORMATS:
        file_bytes = logic.export.FILE_FORMATS[file_extension][1](flask_login.current_user.id, object_ids=object_ids)
    else:
        file_bytes = None
    if file_bytes:
        return flask.Response(
            file_bytes,
            200,
            headers={
                'Content-Disposition': f'attachment; filename=sampledb_export{file_extension}',
                'Content-Type': 'application/pdf' if file_extension == '.pdf' else logic.export.FILE_FORMATS[file_extension][2]
            }
        )
    return flask.abort(500)


@frontend.route('/objects/<int:object_id>/files/')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_files(object_id):
    files = logic.files.get_files_for_object(object_id)
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, 'w') as zip_file:
        for file in files:
            if file.is_hidden:
                continue
            if file.storage == 'local':
                try:
                    file_bytes = file.open(read_only=True).read()
                except Exception:
                    pass
                else:
                    zip_file.writestr(os.path.basename(file.original_file_name), file_bytes)
    return flask.Response(
        zip_bytes.getvalue(),
        200,
        headers={
            'Content-Type': 'application/zip',
            'Content-Disposition': f'attachment; filename=object_{object_id}_files.zip'
        }
    )


@frontend.route('/objects/<int:object_id>/files/<int:file_id>', methods=['GET'])
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_file(object_id, file_id):
    file = logic.files.get_file_for_object(object_id, file_id)
    if file is None:
        return flask.abort(404)
    if file.is_hidden:
        return flask.abort(403)
    if file.storage == 'local':
        if 'preview' in flask.request.args:
            file_extension = os.path.splitext(file.original_file_name)[1]
            mime_type = flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, None)
            if mime_type is not None:
                return flask.send_file(file.open(), mimetype=mime_type, last_modified=file.utc_datetime)
        return flask.send_file(file.open(), as_attachment=True, attachment_filename=file.original_file_name, last_modified=file.utc_datetime)
    # TODO: better error handling
    return flask.abort(404)


@frontend.route('/objects/<int:object_id>/files/<int:file_id>', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def update_file_information(object_id, file_id):
    check_current_user_is_not_readonly()
    form = FileInformationForm()
    if not form.validate_on_submit():
        return flask.abort(400)
    title = form.title.data
    description = form.description.data
    try:
        logic.files.update_file_information(
            object_id=object_id,
            file_id=file_id,
            user_id=flask_login.current_user.id,
            title=title,
            description=description
        )
    except logic.errors.FileDoesNotExistError:
        return flask.abort(404)
    return flask.redirect(flask.url_for('.object', object_id=object_id, _anchor='file-{}'.format(file_id)))


@frontend.route('/objects/<int:object_id>/files/<int:file_id>/hide', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def hide_file(object_id, file_id):
    check_current_user_is_not_readonly()
    form = FileHidingForm()
    if not form.validate_on_submit():
        return flask.abort(400)
    reason = form.reason.data
    try:
        logic.files.hide_file(
            object_id=object_id,
            file_id=file_id,
            user_id=flask_login.current_user.id,
            reason=reason
        )
    except logic.errors.FileDoesNotExistError:
        return flask.abort(404)
    flask.flash('The file was hidden successfully.', 'success')
    return flask.redirect(flask.url_for('.object', object_id=object_id, _anchor='file-{}'.format(file_id)))


@frontend.route('/objects/<int:object_id>/files/mobile_upload/<token>', methods=['GET'])
def mobile_file_upload(object_id: int, token: str):
    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
    try:
        user_id, object_id = serializer.loads(token, max_age=15 * 60)
    except itsdangerous.BadSignature:
        return flask.abort(400)
    try:
        user = logic.users.get_user(user_id)
    except UserDoesNotExistError:
        return flask.abort(403)
    if user.is_readonly:
        return flask.abort(403)
    return flask.render_template('mobile_upload.html')


@frontend.route('/objects/<int:object_id>/files/mobile_upload/<token>', methods=['POST'])
def post_mobile_file_upload(object_id: int, token: str):
    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
    try:
        user_id, object_id = serializer.loads(token, max_age=15 * 60)
    except itsdangerous.BadSignature:
        return flask.abort(400)
    try:
        user = logic.users.get_user(user_id)
    except UserDoesNotExistError:
        return flask.abort(403)
    if user.is_readonly:
        return flask.abort(403)
    files = flask.request.files.getlist('file_input')
    if not files:
        return flask.redirect(
            flask.url_for(
                '.mobile_file_upload',
                object_id=object_id,
                token=token
            )
        )
    for file_storage in files:
        file_name = werkzeug.utils.secure_filename(file_storage.filename)
        logic.files.create_local_file(object_id, user_id, file_name, lambda stream: file_storage.save(dst=stream))
    return flask.render_template('mobile_upload_success.html')


@frontend.route('/objects/<int:object_id>/files/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_files(object_id):
    check_current_user_is_not_readonly()
    external_link_form = ExternalLinkForm()
    file_form = FileForm()
    if file_form.validate_on_submit():
        file_source = file_form.file_source.data
        if file_source == 'local':
            files = flask.request.files.getlist(file_form.local_files.name)
            for file_storage in files:
                file_name = werkzeug.utils.secure_filename(file_storage.filename)
                logic.files.create_local_file(object_id, flask_login.current_user.id, file_name, lambda stream: file_storage.save(dst=stream))
            flask.flash('Successfully uploaded files.', 'success')
        else:
            flask.flash('Failed to upload files.', 'error')
    elif external_link_form.validate_on_submit():
        url = external_link_form.url.data
        logic.files.create_url_file(object_id, flask_login.current_user.id, url)
        flask.flash('Successfully posted link.', 'success')
    elif external_link_form.errors:
        flask.flash('Failed to post link.', 'error')
        return flask.redirect(flask.url_for('.object', object_id=object_id, invalid_link=True, _anchor='anchor-post-link'))
    else:
        flask.flash('Failed to upload files.', 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/objects/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_object():
    check_current_user_is_not_readonly()
    action_id = flask.request.args.get('action_id', None)
    previous_object_id = flask.request.args.get('previous_object_id', None)
    if not action_id and not previous_object_id:
        # TODO: handle error
        return flask.abort(404)

    sample_id = flask.request.args.get('sample_id', None)

    previous_object = None
    action = None
    if action_id:
        try:
            action = get_action(action_id)
        except ActionDoesNotExistError:
            return flask.abort(404)
        if Permissions.READ not in get_user_action_permissions(action_id, user_id=flask_login.current_user.id):
            return flask.abort(404)
    if previous_object_id:
        try:
            previous_object = get_object(previous_object_id)
        except ObjectDoesNotExistError:
            return flask.abort(404)
        if Permissions.READ not in get_user_object_permissions(user_id=flask_login.current_user.id, object_id=previous_object_id):
            return flask.abort(404)

    placeholder_data = {}

    if sample_id is not None:
        try:
            sample_id = int(sample_id)
        except ValueError:
            sample_id = None
        else:
            if sample_id <= 0:
                sample_id = None
    if sample_id is not None:
        try:
            logic.objects.get_object(sample_id)
        except logic.errors.ObjectDoesNotExistError:
            sample_id = None
    if sample_id is not None:
        if action.schema.get('properties', {}).get('sample', {}).get('type', '') == 'sample':
            placeholder_data = {
                ('sample', ): {'_type': 'sample', 'object_id': sample_id}
            }

    # TODO: check instrument permissions
    return show_object_form(None, action, previous_object, placeholder_data=placeholder_data)


@frontend.route('/objects/<int:object_id>/versions/')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_versions(object_id):
    object = get_object(object_id=object_id)
    if object is None:
        return flask.abort(404)
    object_versions = get_object_versions(object_id=object_id)
    object_versions.sort(key=lambda object_version: -object_version.version_id)
    return flask.render_template('objects/object_versions.html', get_user=get_user, object=object, object_versions=object_versions)


@frontend.route('/objects/<int:object_id>/versions/<int:version_id>')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_version(object_id, version_id):
    object = get_object(object_id=object_id, version_id=version_id)
    form = None
    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    if Permissions.WRITE in user_permissions:
        current_object = get_object(object_id=object_id)
        if current_object.version_id != version_id:
            form = ObjectVersionRestoreForm()
    user_may_grant = Permissions.GRANT in user_permissions
    action = get_action(object.action_id)
    instrument = action.instrument
    object_type = {
        ActionType.SAMPLE_CREATION: "Sample",
        ActionType.MEASUREMENT: "Measurement",
        ActionType.SIMULATION: "Simulation"
    }.get(action.type, "Object")
    return flask.render_template(
        'objects/view/base.html',
        is_archived=True,
        object_type=object_type,
        action=action,
        instrument=instrument,
        schema=object.schema,
        data=object.data,
        last_edit_datetime=object.utc_datetime,
        last_edit_user=get_user(object.user_id),
        object_id=object_id,
        version_id=version_id,
        link_version_specific_rdf=True,
        restore_form=form,
        user_may_grant=user_may_grant
    )


@frontend.route('/objects/<int:object_id>/versions/<int:version_id>/restore', methods=['GET', 'POST'])
@object_permissions_required(Permissions.WRITE)
def restore_object_version(object_id, version_id):
    if version_id < 0 or object_id < 0:
        return flask.abort(404)
    try:
        current_object = get_object(object_id=object_id)
    except ObjectDoesNotExistError:
        return flask.abort(404)
    if current_object.version_id <= version_id:
        return flask.abort(404)
    form = ObjectVersionRestoreForm()
    if form.validate_on_submit():
        logic.objects.restore_object_version(object_id=object_id, version_id=version_id, user_id=flask_login.current_user.id)
        return flask.redirect(flask.url_for('.object', object_id=object_id))
    return flask.render_template('objects/restore_object_version.html', object_id=object_id, version_id=version_id, restore_form=form)


@frontend.route('/objects/<int:object_id>/permissions')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_permissions(object_id):
    check_current_user_is_not_readonly()
    object = get_object(object_id)
    action = get_action(object.action_id)
    instrument = action.instrument
    user_permissions = get_object_permissions_for_users(object_id=object_id, include_instrument_responsible_users=False, include_groups=False, include_projects=False, include_readonly=False, include_admin_permissions=False)
    group_permissions = get_object_permissions_for_groups(object_id=object_id, include_projects=False)
    project_permissions = get_object_permissions_for_projects(object_id=object_id)
    public_permissions = Permissions.READ if object_is_public(object_id) else Permissions.NONE
    suggested_user_id = flask.request.args.get('add_user_id', '')
    try:
        suggested_user_id = int(suggested_user_id)
    except ValueError:
        suggested_user_id = None
    if Permissions.GRANT in get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id):
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
        project_permission_form_data = []
        for project_id, permissions in project_permissions.items():
            if project_id is None:
                continue
            project_permission_form_data.append({'project_id': project_id, 'permissions': permissions.name.lower()})
        edit_user_permissions_form = ObjectPermissionsForm(public_permissions=public_permissions.name.lower(), user_permissions=user_permission_form_data, group_permissions=group_permission_form_data, project_permissions=project_permission_form_data)
        users = get_users(exclude_hidden=True)
        users = [user for user in users if user.id not in user_permissions]
        add_user_permissions_form = ObjectUserPermissionsForm()
        groups = get_user_groups(flask_login.current_user.id)
        groups = [group for group in groups if group.id not in group_permissions]
        add_group_permissions_form = ObjectGroupPermissionsForm()
        projects = get_user_projects(flask_login.current_user.id, include_groups=True)
        projects = [project for project in projects if project.id not in project_permissions]
        add_project_permissions_form = ObjectProjectPermissionsForm()
        copy_permissions_form = CopyPermissionsForm()
        existing_objects = get_objects_with_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.GRANT
        )
        copy_permissions_form.object_id.choices = [
            (str(existing_object.id), existing_object.data['name']['text'])
            for existing_object in existing_objects
            if existing_object.id != object_id
        ]
    else:
        edit_user_permissions_form = None
        add_user_permissions_form = None
        add_group_permissions_form = None
        add_project_permissions_form = None
        copy_permissions_form = None
        users = []
        groups = []
        projects = []
    return flask.render_template(
        'objects/object_permissions.html',
        instrument=instrument,
        action=action,
        object=object,
        user_permissions=user_permissions,
        group_permissions=group_permissions,
        project_permissions=project_permissions,
        public_permissions=public_permissions,
        get_user=get_user,
        Permissions=Permissions,
        form=edit_user_permissions_form,
        users=users,
        groups=groups,
        projects=projects,
        add_user_permissions_form=add_user_permissions_form,
        add_group_permissions_form=add_group_permissions_form,
        get_group=get_group,
        add_project_permissions_form=add_project_permissions_form,
        copy_permissions_form=copy_permissions_form,
        get_project=get_project,
        suggested_user_id=suggested_user_id
    )


@frontend.route('/objects/<int:object_id>/permissions', methods=['POST'])
@object_permissions_required(Permissions.GRANT)
def update_object_permissions(object_id):
    edit_user_permissions_form = ObjectPermissionsForm()
    add_user_permissions_form = ObjectUserPermissionsForm()
    add_group_permissions_form = ObjectGroupPermissionsForm()
    add_project_permissions_form = ObjectProjectPermissionsForm()
    copy_permissions_form = CopyPermissionsForm()
    if 'copy_permissions' in flask.request.form:

        existing_objects = get_objects_with_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.GRANT
        )
        copy_permissions_form.object_id.choices = [
            (str(existing_object.id), existing_object.data['name']['text'])
            for existing_object in existing_objects
            if existing_object.id != object_id
        ]
        if copy_permissions_form.validate_on_submit():
            logic.object_permissions.copy_permissions(object_id, int(copy_permissions_form.object_id.data))
            logic.object_permissions.set_user_object_permissions(object_id, flask_login.current_user.id, Permissions.GRANT)
            flask.flash("Successfully copied object permissions.", 'success')
    elif 'edit_user_permissions' in flask.request.form and edit_user_permissions_form.validate_on_submit():
        set_object_public(object_id, edit_user_permissions_form.public_permissions.data == 'read')
        for user_permissions_data in edit_user_permissions_form.user_permissions.data:
            user_id = user_permissions_data['user_id']
            try:
                get_user(user_id)
            except UserDoesNotExistError:
                continue
            permissions = Permissions.from_name(user_permissions_data['permissions'])
            set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=permissions)
        for group_permissions_data in edit_user_permissions_form.group_permissions.data:
            group_id = group_permissions_data['group_id']
            try:
                get_group(group_id)
            except GroupDoesNotExistError:
                continue
            permissions = Permissions.from_name(group_permissions_data['permissions'])
            set_group_object_permissions(object_id=object_id, group_id=group_id, permissions=permissions)
        for project_permissions_data in edit_user_permissions_form.project_permissions.data:
            project_id = project_permissions_data['project_id']
            try:
                get_project(project_id)
            except ProjectDoesNotExistError:
                continue
            permissions = Permissions.from_name(project_permissions_data['permissions'])
            set_project_object_permissions(object_id=object_id, project_id=project_id, permissions=permissions)
        user_log.edit_object_permissions(user_id=flask_login.current_user.id, object_id=object_id)
        flask.flash("Successfully updated object permissions.", 'success')
    elif 'add_user_permissions' in flask.request.form and add_user_permissions_form.validate_on_submit():
        user_id = add_user_permissions_form.user_id.data
        permissions = Permissions.from_name(add_user_permissions_form.permissions.data)
        object_permissions = get_object_permissions_for_users(object_id=object_id, include_instrument_responsible_users=False, include_groups=False, include_projects=False, include_admin_permissions=False)
        assert permissions in [Permissions.READ, Permissions.WRITE, Permissions.GRANT]
        assert user_id not in object_permissions
        user_log.edit_object_permissions(user_id=flask_login.current_user.id, object_id=object_id)
        set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=permissions)
        flask.flash("Successfully updated object permissions.", 'success')
    elif 'add_group_permissions' in flask.request.form and add_group_permissions_form.validate_on_submit():
        group_id = add_group_permissions_form.group_id.data
        permissions = Permissions.from_name(add_group_permissions_form.permissions.data)
        object_permissions = get_object_permissions_for_groups(object_id=object_id)
        assert permissions in [Permissions.READ, Permissions.WRITE, Permissions.GRANT]
        assert group_id not in object_permissions
        user_log.edit_object_permissions(user_id=flask_login.current_user.id, object_id=object_id)
        set_group_object_permissions(object_id=object_id, group_id=group_id, permissions=permissions)
        flask.flash("Successfully updated object permissions.", 'success')
    elif 'add_project_permissions' in flask.request.form and add_project_permissions_form.validate_on_submit():
        project_id = add_project_permissions_form.project_id.data
        permissions = Permissions.from_name(add_project_permissions_form.permissions.data)
        object_permissions = get_object_permissions_for_projects(object_id=object_id)
        assert permissions in [Permissions.READ, Permissions.WRITE, Permissions.GRANT]
        assert project_id not in object_permissions
        user_log.edit_object_permissions(user_id=flask_login.current_user.id, object_id=object_id)
        set_project_object_permissions(object_id=object_id, project_id=project_id, permissions=permissions)
        flask.flash("Successfully updated object permissions.", 'success')
    else:
        flask.flash("A problem occurred while changing the object permissions. Please try again.", 'error')
    return flask.redirect(flask.url_for('.object_permissions', object_id=object_id))
