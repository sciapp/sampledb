# coding: utf-8
"""

"""

from copy import deepcopy
import datetime
import io
import json
import os
import flask
import flask_login
import itsdangerous
import werkzeug.utils

from . import frontend
from .. import db
from .. import logic
from ..logic import user_log, object_log, comments
from ..logic.actions import ActionType, get_action
from ..logic.action_permissions import get_user_action_permissions
from ..logic.object_permissions import Permissions, get_user_object_permissions, object_is_public, get_object_permissions_for_users, set_object_public, set_user_object_permissions, set_group_object_permissions, set_project_object_permissions, get_objects_with_permissions, get_object_permissions_for_groups, get_object_permissions_for_projects
from ..logic.datatypes import JSONEncoder
from ..logic.users import get_user, get_users
from ..logic.schemas import validate, generate_placeholder
from ..logic.object_search import generate_filter_func, wrap_filter_func
from ..logic.groups import get_group, get_user_groups
from ..logic.objects import create_object, create_object_batch, update_object, get_object, get_object_versions
from ..logic.object_log import ObjectLogEntryType
from ..logic.projects import get_project, get_user_projects, get_user_project_permissions
from ..logic.locations import get_location, get_object_ids_at_location, get_object_location_assignment, get_object_location_assignments, get_locations, assign_location_to_object, get_locations_tree
from ..logic.files import FileLogEntryType
from ..logic.errors import GroupDoesNotExistError, ObjectDoesNotExistError, UserDoesNotExistError, ActionDoesNotExistError, ValidationError, ProjectDoesNotExistError, LocationDoesNotExistError
from .objects_forms import ObjectPermissionsForm, ObjectForm, ObjectVersionRestoreForm, ObjectUserPermissionsForm, CommentForm, ObjectGroupPermissionsForm, ObjectProjectPermissionsForm, FileForm, FileInformationForm, FileHidingForm, ObjectLocationAssignmentForm
from ..utils import object_permissions_required
from .utils import jinja_filter, generate_qrcode
from .object_form_parser import parse_form_data
from .labels import create_labels
from .pdfexport import create_pdfexport


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


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
        object_ids_at_location = None
        project = None
        query_string = ''
        use_advanced_search = False
        must_use_advanced_search = False
        advanced_search_had_error = False
        search_notes = []
        search_tree = None
    else:
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
        query_string = flask.request.args.get('q', '')
        search_tree = None
        use_advanced_search = flask.request.args.get('advanced', None) is not None
        must_use_advanced_search = use_advanced_search
        advanced_search_had_error = False
        try:
            filter_func, search_tree, use_advanced_search = generate_filter_func(query_string, use_advanced_search)
        except Exception as e:
            # TODO: ensure that advanced search does not cause exceptions
            if use_advanced_search:
                advanced_search_had_error = True

                def filter_func(data, search_notes):
                    """ Return all objects"""
                    search_notes.append(('error', "Unable to parse search expression".format(query_string), 0, len(query_string)))
                    return False
            else:
                raise
        filter_func, search_notes = wrap_filter_func(filter_func)
        if use_advanced_search and not must_use_advanced_search:
            search_notes.append(('info', "The advanced search was used automatically. Search for \"{}\" to use the simple search.".format(query_string), 0, 0))
        try:
            objects = get_objects_with_permissions(
                user_id=flask_login.current_user.id,
                permissions=Permissions.READ,
                filter_func=filter_func,
                action_id=action_id,
                action_type=action_type,
                project_id=project_id,
                object_ids=object_ids_at_location
            )
        except Exception as e:
            search_notes.append(('error', "Error during search: {}".format(e), 0, 0))
            objects = []
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

    objects.sort(key=lambda obj: obj['object_id'], reverse=True)
    samples = {
        sample_id: get_object(object_id=sample_id)
        for sample_id in sample_ids
    }
    if action_id is None:
        show_action = True
    else:
        show_action = False
    return flask.render_template('objects/objects.html', objects=objects, display_properties=display_properties, display_property_titles=display_property_titles, search_query=query_string, action=action, action_id=action_id, action_type=action_type, ActionType=ActionType, project=project, project_id=project_id, location_id=location_id, location=location, samples=samples, show_action=show_action, use_advanced_search=use_advanced_search, must_use_advanced_search=must_use_advanced_search, advanced_search_had_error=advanced_search_had_error, search_notes=search_notes, search_tree=search_tree)


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
                item_index, id_suffix = name[len(parent_id_prefix)+2:].split('__', 1)
                item_index = int(item_index)
                if item_index < deleted_item_index:
                    new_form_data[name] = form_data[name]
                if item_index > deleted_item_index:
                    new_name = parent_id_prefix + '__' + str(item_index-1) + '__' + id_suffix
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


def show_object_form(object, action, previous_object=None, should_upgrade_schema=False):
    if object is None and previous_object is None:
        data = generate_placeholder(action.schema)
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

    if previous_object is not None:
        action_id = previous_object.action_id
        previous_object_id = previous_object.id
    else:
        action_id = action.id
        previous_object_id = None
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
                            for i in range(1, num_objects_in_batch+1):
                                if name_suffix_format:
                                    name_suffix = name_suffix_format.format(i)
                                else:
                                    name_suffix = ''
                                object_data['name']['text'] = batch_base_name + name_suffix
                                data_sequence.append(deepcopy(object_data))
                        else:
                            data_sequence = [object_data] * num_objects_in_batch
                        objects = create_object_batch(action_id=action.id, data_sequence=data_sequence, user_id=flask_login.current_user.id)
                        object_ids = [object.id for object in objects]
                        flask.flash('The objects were created successfully.', 'success')
                        return flask.redirect(flask.url_for('.objects', ids=','.join([str(object_id) for object_id in object_ids])))
                    else:
                        object = create_object(action_id=action.id, data=object_data, user_id=flask_login.current_user.id, previous_object_id=previous_object_id, schema=previous_object_schema)
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

    tags = [{'name': tag.name, 'uses': tag.uses} for tag in logic.tags.get_tags()]
    if object is None:
        return flask.render_template('objects/forms/form_create.html', action_id=action_id, schema=schema, data=data, errors=errors, object_errors=object_errors, form_data=form_data, previous_actions=serializer.dumps(previous_actions), form=form, samples=samples, datetime=datetime, tags=tags, previous_object_id=previous_object_id)
    else:
        return flask.render_template('objects/forms/form_edit.html', schema=schema, data=data, object_id=object.object_id, errors=errors, object_errors=object_errors, form_data=form_data, previous_actions=serializer.dumps(previous_actions), form=form, samples=samples, datetime=datetime, tags=tags, mode=mode)


@frontend.route('/objects/<int:object_id>', methods=['GET', 'POST'])
@object_permissions_required(Permissions.READ)
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
        for user in logic.users.get_users():
            possible_responsible_users.append((str(user.id), '{} (#{})'.format(user.name, user.id)))
        location_form.responsible_user.choices = possible_responsible_users

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
            mobile_upload_url=mobile_upload_url,
            mobile_upload_qrcode=mobile_upload_qrcode,
            object_qrcode=object_qrcode,
            object_url=object_url,
            restore_form=None,
            version_id=object.version_id,
            user_may_grant=user_may_grant,
            samples=samples,
            FileLogEntryType=FileLogEntryType,
            file_information_form=FileInformationForm(),
            file_hiding_form=FileHidingForm(),
            new_schema_available=new_schema_available,
            related_objects_tree=related_objects_tree,
            get_object=get_object,
            get_object_location_assignment=get_object_location_assignment,
            get_user=get_user,
            get_location=get_location,
            object_location_assignments=get_object_location_assignments(object_id),
            user_may_assign_location=user_may_edit,
            location_form=location_form
        )
    if flask.request.args.get('mode', '') == 'upgrade':
        should_upgrade_schema = True
    else:
        should_upgrade_schema = False
    return show_object_form(object, action=get_action(object.action_id), should_upgrade_schema=should_upgrade_schema)


@frontend.route('/objects/<int:object_id>/label')
@object_permissions_required(Permissions.READ)
def print_object_label(object_id):
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
        ghs_classes=hazards
    )
    return flask.send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        cache_timeout=-1
    )


@frontend.route('/objects/<int:object_id>/comments/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_comments(object_id):
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        content = comment_form.content.data
        comments.create_comment(object_id=object_id, user_id=flask_login.current_user.id, content=content)
        flask.flash('Successfully posted a comment.', 'success')
    else:
        flask.flash('Please enter a comment text.', 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/objects/<int:object_id>/locations/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_location(object_id):
    location_form = ObjectLocationAssignmentForm()
    location_form.location.choices = [('-1', '—')] + [
        (str(location.id), '{} (#{})'.format(location.name, location.id))
        for location in get_locations()
    ]
    possible_responsible_users = [('-1', '—')]
    for user in logic.users.get_users():
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


@frontend.route('/objects/<int:object_id>/pdf')
@object_permissions_required(Permissions.READ)
def export_to_pdf(object_id):
    object_ids = [object_id]
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
    pdf_data = create_pdfexport(object_ids)

    return flask.send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        cache_timeout=-1
    )


@frontend.route('/files/')
@flask_login.login_required
def existing_files_from_source():
    if 'file_source' not in flask.request.args:
        return flask.abort(400)
    file_source = flask.request.args['file_source']
    relative_path = flask.request.args.get('relative_path', '')
    while relative_path.startswith('/'):
        relative_path = relative_path[1:]
    try:
        return json.dumps(logic.files.get_existing_files_for_source(file_source, flask_login.current_user.id, relative_path, max_depth=2))
    except (logic.errors.InvalidFileSourceError, FileNotFoundError) as e:
        return flask.abort(404)


@frontend.route('/objects/<int:object_id>/files/<int:file_id>', methods=['GET'])
@object_permissions_required(Permissions.READ)
def object_file(object_id, file_id):
    file = logic.files.get_file_for_object(object_id, file_id)
    if file is None:
        return flask.abort(404)
    if file.is_hidden:
        return flask.abort(403)
    if 'preview' in flask.request.args:
        file_extension = os.path.splitext(file.original_file_name)[1]
        mime_type = flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, None)
        if mime_type is not None:
            return flask.send_file(file.open(), mimetype=mime_type, last_modified=file.utc_datetime)
    return flask.send_file(file.open(), as_attachment=True, attachment_filename=file.original_file_name, last_modified=file.utc_datetime)


@frontend.route('/objects/<int:object_id>/files/<int:file_id>', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def update_file_information(object_id, file_id):
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
        user_id, object_id = serializer.loads(token, max_age=15*60)
    except itsdangerous.BadSignature:
        return flask.abort(400)
    return flask.render_template('mobile_upload.html', user_id=logic.users.get_user(user_id), object=logic.objects.get_object(object_id))


@frontend.route('/objects/<int:object_id>/files/mobile_upload/<token>', methods=['POST'])
def post_mobile_file_upload(object_id: int, token: str):
    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
    try:
        user_id, object_id = serializer.loads(token, max_age=15*60)
    except itsdangerous.BadSignature:
        return flask.abort(400)
    files = flask.request.files.getlist('file_input')
    for file_storage in files:
        file_name = werkzeug.utils.secure_filename(file_storage.filename)
        logic.files.create_file(object_id, user_id, file_name, lambda stream: file_storage.save(dst=stream))
    return flask.render_template('mobile_upload_success.html', num_files=len(files))


@frontend.route('/objects/<int:object_id>/files/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_files(object_id):
    file_form = FileForm()
    if file_form.validate_on_submit():
        file_source = file_form.file_source.data
        if file_source == 'local':
            files = flask.request.files.getlist(file_form.local_files.name)
            for file_storage in files:
                file_name = werkzeug.utils.secure_filename(file_storage.filename)
                logic.files.create_file(object_id, flask_login.current_user.id, file_name, lambda stream: file_storage.save(dst=stream))
            flask.flash('Successfully uploaded files.', 'success')
        elif file_source in logic.files.FILE_SOURCES.keys():
            file_names = file_form.file_names.data
            try:
                file_names = json.loads(file_names)
            except json.JSONDecodeError:
                flask.flash('Failed to upload files.', 'error')
                return flask.redirect(flask.url_for('.object', object_id=object_id))
            for file_name in file_names:
                try:
                    logic.files.copy_file(object_id, flask_login.current_user.id, file_source, file_name)
                except (FileNotFoundError, logic.errors.InvalidFileSourceError):
                    flask.flash('Failed to upload files.', 'error')
                    return flask.redirect(flask.url_for('.object', object_id=object_id))
            flask.flash('Successfully uploaded files.', 'success')
        else:
            flask.flash('Failed to upload files.', 'error')
    else:
        flask.flash('Failed to upload files.', 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/objects/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_object():
    action_id = flask.request.args.get('action_id', None)
    previous_object_id = flask.request.args.get('previous_object_id', None)
    if not action_id and not previous_object_id:
        # TODO: handle error
        return flask.abort(404)

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

    # TODO: check instrument permissions
    return show_object_form(None, action, previous_object)


@frontend.route('/objects/<int:object_id>/versions/')
@object_permissions_required(Permissions.READ)
def object_versions(object_id):
    object = get_object(object_id=object_id)
    if object is None:
        return flask.abort(404)
    object_versions = get_object_versions(object_id=object_id)
    object_versions.sort(key=lambda object_version: -object_version.version_id)
    return flask.render_template('objects/object_versions.html', get_user=get_user, object=object, object_versions=object_versions)


@frontend.route('/objects/<int:object_id>/versions/<int:version_id>')
@object_permissions_required(Permissions.READ)
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
@object_permissions_required(Permissions.READ)
def object_permissions(object_id):
    object = get_object(object_id)
    action = get_action(object.action_id)
    instrument = action.instrument
    user_permissions = get_object_permissions_for_users(object_id=object_id, include_instrument_responsible_users=False, include_groups=False, include_projects=False)
    group_permissions = get_object_permissions_for_groups(object_id=object_id, include_projects=False)
    project_permissions = get_object_permissions_for_projects(object_id=object_id)
    public_permissions = Permissions.READ if object_is_public(object_id) else Permissions.NONE
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
        users = get_users()
        users = [user for user in users if user.id not in user_permissions]
        add_user_permissions_form = ObjectUserPermissionsForm()
        groups = get_user_groups(flask_login.current_user.id)
        groups = [group for group in groups if group.id not in group_permissions]
        add_group_permissions_form = ObjectGroupPermissionsForm()
        projects = get_user_projects(flask_login.current_user.id, include_groups=True)
        projects = [project for project in projects if project.id not in project_permissions]
        add_project_permissions_form = ObjectProjectPermissionsForm()
    else:
        edit_user_permissions_form = None
        add_user_permissions_form = None
        add_group_permissions_form = None
        add_project_permissions_form = None
        users = []
        groups = []
        projects = []
    return flask.render_template('objects/object_permissions.html', instrument=instrument, action=action, object=object, user_permissions=user_permissions, group_permissions=group_permissions, project_permissions=project_permissions, public_permissions=public_permissions, get_user=get_user, Permissions=Permissions, form=edit_user_permissions_form, users=users, groups=groups, projects=projects, add_user_permissions_form=add_user_permissions_form, add_group_permissions_form=add_group_permissions_form, get_group=get_group, add_project_permissions_form=add_project_permissions_form, get_project=get_project)


@frontend.route('/objects/<int:object_id>/permissions', methods=['POST'])
@object_permissions_required(Permissions.GRANT)
def update_object_permissions(object_id):
    edit_user_permissions_form = ObjectPermissionsForm()
    add_user_permissions_form = ObjectUserPermissionsForm()
    add_group_permissions_form = ObjectGroupPermissionsForm()
    add_project_permissions_form = ObjectProjectPermissionsForm()
    if 'edit_user_permissions' in flask.request.form and edit_user_permissions_form.validate_on_submit():
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
        object_permissions = get_object_permissions_for_users(object_id=object_id, include_instrument_responsible_users=False, include_groups=False, include_projects=False)
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
