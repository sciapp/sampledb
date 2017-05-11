# coding: utf-8
"""

"""

import datetime
import json
import flask
import flask_login
import itsdangerous

from . import frontend
from ..logic import user_log, object_log, comments
from ..logic.permissions import get_user_object_permissions, object_is_public, get_object_permissions_for_users, set_object_public, set_user_object_permissions, set_group_object_permissions, get_objects_with_permissions, get_object_permissions_for_groups
from ..logic.datatypes import JSONEncoder
from ..logic.user import get_user
from ..logic.schemas import validate, generate_placeholder, ValidationError
from ..logic.object_search import generate_filter_func
from ..logic.instruments import get_action
from ..logic.groups import get_group, get_user_groups, GroupDoesNotExistError
from .objects_forms import ObjectPermissionsForm, ObjectForm, ObjectVersionRestoreForm, ObjectUserPermissionsForm, CommentForm, ObjectGroupPermissionsForm
from .. import db
from ..models import User, Action, Objects, Permissions, ActionType, ObjectLogEntryType
from ..utils import object_permissions_required
from .utils import jinja_filter
from .object_form_parser import parse_form_data

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/objects/')
@flask_login.login_required
def objects():
    try:
        action_id = int(flask.request.args.get('action', ''))
    except ValueError:
        action_id = None
    action_type = flask.request.args.get('t', '')
    action_type = {
        'samples': ActionType.SAMPLE_CREATION,
        'measurements': ActionType.MEASUREMENT
    }.get(action_type, None)
    query_string = flask.request.args.get('q', '')
    filter_func = generate_filter_func(query_string)
    objects = get_objects_with_permissions(
        user_id=flask_login.current_user.id,
        permissions=Permissions.READ,
        filter_func=filter_func,
        action_id=action_id,
        action_type=action_type
    )

    for i, obj in enumerate(objects):
        if obj.version_id == 0:
            original_object = obj
        else:
            original_object = Objects.get_object_version(object_id=obj.object_id, version_id=0)
        objects[i] = {
            'object_id': obj.object_id,
            'version_id': obj.version_id,
            'created_by': get_user(original_object.user_id),
            'created_at': original_object.utc_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'modified_by': get_user(obj.user_id),
            'last_modified_at': obj.utc_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'data': obj.data,
            'schema': obj.schema,
            'action': get_action(obj.action_id),
            'display_properties': {}
        }

    # TODO: select display_properties? nested display_properties? find common properties? use searched for properties?
    display_properties = []
    display_property_titles = {}
    sample_ids = set()
    if action_id is not None:
        action_schema = get_action(action_id).schema
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

    objects.sort(key=lambda obj: obj['object_id'])
    samples = {
        sample_id: Objects.get_current_object(object_id=sample_id)
        for sample_id in sample_ids
    }
    return flask.render_template('objects/objects.html', objects=objects, display_properties=display_properties, display_property_titles=display_property_titles, search_query=query_string, action_type=action_type, ActionType=ActionType, samples=samples)


@jinja_filter
def to_datatype(obj):
    return json.loads(json.dumps(obj), object_hook=JSONEncoder.object_hook)


def apply_action_to_data(data, schema, action, form_data):
    new_form_data = form_data
    if action.endswith('_delete'):
        id_prefix = action[len('action_object_'):-len('_delete')]
        deleted_item_index = int(id_prefix.split('_')[-1])
        parent_id_prefix = 'object_'+'_'.join(id_prefix.split('_')[:-1]) + '_'
        new_form_data = {}
        for name in form_data:
            if not name.startswith(parent_id_prefix):
                new_form_data[name] = form_data[name]
            else:
                item_index = int(name[len(parent_id_prefix):].split('_')[0])
                if item_index < deleted_item_index:
                    new_form_data[name] = form_data[name]
                if item_index > deleted_item_index:
                    new_name = parent_id_prefix + str(item_index-1) + name[len(parent_id_prefix+str(item_index)):]
                    new_form_data[new_name] = form_data[name]
    elif action.endswith('_add'):
        id_prefix = action[len('action_object_'):-len('_add')]
    else:
        raise ValueError('invalid action')
    keys = id_prefix.split('_')
    sub_data = data
    sub_schema = schema
    try:
        for key in keys[:-1]:
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
        if action.endswith('_delete'):
            if 'minItems' not in sub_schema or len(sub_data) > sub_schema["minItems"]:
                del sub_data[int(keys[-1])]
        elif action.endswith('_add'):
            if 'maxItems' not in sub_schema or len(sub_data) < sub_schema["maxItems"]:
                sub_data.append(generate_placeholder(sub_schema["items"]))
    except (ValueError, KeyError, IndexError, TypeError):
        # TODO: error handling/logging?
        raise ValueError('invalid action')
    return new_form_data


def show_object_form(object, action):
    if object is None:
        data = generate_placeholder(action.schema)
    else:
        data = object.data
    # TODO: update schema
    # schema = get_action(object.action_id).schema
    if object is not None:
        schema = object.schema
    else:
        schema = action.schema
    action_id = action.id
    errors = []
    form_data = {}
    previous_actions = []
    serializer = itsdangerous.URLSafeSerializer(flask.current_app.config['SECRET_KEY'])
    form = ObjectForm()
    if flask.request.method != 'GET' and form.validate_on_submit():
        form_data = {k: v[0] for k, v in dict(flask.request.form).items()}

        if 'previous_actions' in flask.request.form:
            try:
                previous_actions = serializer.loads(flask.request.form['previous_actions'])
            except itsdangerous.BadData:
                flask.abort(400)

        if "action_submit" in form_data:
            object_data, errors = parse_form_data(dict(flask.request.form), schema)
            if object_data is not None  and not errors:
                try:
                    validate(object_data, schema)
                except ValidationError:
                    # TODO: proper logging
                    print('object schema validation failed')
                    # TODO: handle error
                    flask.abort(400)
                if object is None:
                    object = Objects.create_object(data=object_data, schema=schema, user_id=flask_login.current_user.id, action_id=action.id)
                    user_log.create_object(user_id=flask_login.current_user.id, object_id=object.object_id)
                    object_log.create_object(object_id=object.object_id, user_id=flask_login.current_user.id)
                    flask.flash('The object was created successfully.', 'success')
                else:
                    object = Objects.update_object(object_id=object.object_id, data=object_data, schema=schema, user_id=flask_login.current_user.id)
                    user_log.edit_object(user_id=flask_login.current_user.id, object_id=object.object_id, version_id=object.version_id)
                    object_log.edit_object(object_id=object.object_id, user_id=flask_login.current_user.id, version_id=object.version_id)
                    flask.flash('The object was updated successfully.', 'success')

                # TODO: gather references to other objects more effectively
                if get_action(object.action_id).type == ActionType.MEASUREMENT:
                    if 'sample' in object.schema.get('properties', {}) and object.schema['properties']['sample']['type'] == 'sample':
                        if 'sample' in object.data and object.data['sample'] is not None:
                            sample_id = object.data['sample']['object_id']
                            previous_sample_id = None
                            if object.version_id > 0:
                                previous_object_version = Objects.get_object_version(object.object_id, object.version_id-1)
                                if 'sample' in previous_object_version.schema.get('properties', {}) and previous_object_version.schema['properties']['sample']['type'] == 'sample':
                                    if 'sample' in previous_object_version.data and previous_object_version.data['sample'] is not None:
                                        previous_sample_id = previous_object_version.data['sample']['object_id']
                            if sample_id != previous_sample_id:
                                object_log.use_object_in_measurement(object_id=sample_id, user_id=flask_login.current_user.id, measurement_id=object.object_id)

                return flask.redirect(flask.url_for('.object', object_id=object.object_id))
        elif any(name.startswith('action_object_') and (name.endswith('_delete') or name.endswith('_add')) for name in form_data):
            action = [name for name in form_data if name.startswith('action_')][0]
            previous_actions.append(action)
    for action in previous_actions:
        try:
            form_data = apply_action_to_data(data, schema, action, form_data)
        except ValueError:
            flask.abort(400)

    # TODO: make this search more narrow
    samples = get_objects_with_permissions(
        user_id=flask_login.current_user.id,
        permissions=Permissions.READ,
        action_type=ActionType.SAMPLE_CREATION
    )
    if object is None:
        return flask.render_template('objects/forms/form_create.html', action_id=action_id, schema=schema, data=data, errors=errors, form_data=form_data, previous_actions=serializer.dumps(previous_actions), form=form, samples=samples, datetime=datetime)
    else:
        return flask.render_template('objects/forms/form_edit.html', schema=schema, data=data, object_id=object.object_id, errors=errors, form_data=form_data, previous_actions=serializer.dumps(previous_actions), form=form, samples=samples, datetime=datetime)


@frontend.route('/objects/<int:object_id>', methods=['GET', 'POST'])
@object_permissions_required(Permissions.READ)
def object(object_id):
    object = Objects.get_current_object(object_id=object_id)

    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    user_may_edit = Permissions.WRITE in user_permissions
    user_may_grant = Permissions.GRANT in user_permissions
    if not user_may_edit and flask.request.args.get('mode', '') == 'edit':
        return flask.abort(403)
    if flask.request.method == 'GET' and flask.request.args.get('mode', '') != 'edit':
        # TODO: make this search more narrow
        samples = get_objects_with_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.READ,
            action_type=ActionType.SAMPLE_CREATION
        )
        action = get_action(object.action_id)
        instrument = action.instrument
        object_type = {
            ActionType.SAMPLE_CREATION: "Sample",
            ActionType.MEASUREMENT: "Measurement"
        }.get(action.type, "Object")
        object_log_entries = object_log.get_object_log_entries(object_id=object_id, user_id=flask_login.current_user.id)
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
            restore_form=None,
            version_id=object.version_id,
            user_may_grant=user_may_grant,
            samples=samples
        )

    return show_object_form(object, action=get_action(object.action_id))


@frontend.route('/objects/<int:object_id>/comments/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_comments(object_id):
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        content = comment_form.content.data
        comments.create_comment(object_id=object_id, user_id=flask_login.current_user.id, content=content)
        flask.flash('Successfully posted a comment.', 'success')
    else:
        print(comment_form.errors)
        flask.flash('Please enter a comment text.', 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))



@frontend.route('/objects/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_object():
    action_id = flask.request.args.get('action_id', None)
    if action_id is None or action_id == '':
        # TODO: handle error
        return flask.abort(404)
    action = get_action(action_id)
    if action is None:
        # TODO: handle error
        return flask.abort(404)

    # TODO: check instrument permissions
    return show_object_form(None, action)


@frontend.route('/objects/<int:object_id>/versions/')
@object_permissions_required(Permissions.READ)
def object_versions(object_id):
    object = Objects.get_current_object(object_id=object_id)
    if object is None:
        return flask.abort(404)
    object_versions = Objects.get_object_versions(object_id=object_id)
    object_versions.sort(key=lambda object_version: -object_version.version_id)
    return flask.render_template('objects/object_versions.html', User=User, object=object, object_versions=object_versions)


@frontend.route('/objects/<int:object_id>/versions/<int:version_id>')
@object_permissions_required(Permissions.READ)
def object_version(object_id, version_id):
    object = Objects.get_object_version(object_id=object_id, version_id=version_id)
    form = None
    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    if Permissions.WRITE in user_permissions:
        current_object = Objects.get_current_object(object_id=object_id)
        if current_object.version_id != version_id:
            form = ObjectVersionRestoreForm()
    user_may_grant = Permissions.GRANT in user_permissions
    action = get_action(object.action_id)
    instrument = action.instrument
    object_type = {
        ActionType.SAMPLE_CREATION: "Sample",
        ActionType.MEASUREMENT: "Measurement"
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
    object_version = Objects.get_object_version(object_id=object_id, version_id=version_id)
    if object_version is None:
        return flask.abort(404)
    current_object = Objects.get_current_object(object_id=object_id)
    if current_object.version_id == version_id:
        return flask.abort(404)
    form = ObjectVersionRestoreForm()
    if form.validate_on_submit():
        object = Objects.restore_object_version(object_id=object_id, version_id=version_id, user_id=flask_login.current_user.id)
        user_log.restore_object_version(user_id=flask_login.current_user.id, object_id=object_id, restored_version_id=version_id, version_id=object.version_id)
        object_log.restore_object_version(object_id=object_id, user_id=flask_login.current_user.id, restored_version_id=version_id, version_id=object.version_id)
        return flask.redirect(flask.url_for('.object', object_id=object_id))
    return flask.render_template('objects/restore_object_version.html', object_id=object_id, version_id=version_id, restore_form=form)


@frontend.route('/objects/<int:object_id>/permissions')
@object_permissions_required(Permissions.READ)
def object_permissions(object_id):
    object = Objects.get_current_object(object_id, connection=db.engine)
    action = get_action(object.action_id)
    instrument = action.instrument
    user_permissions = get_object_permissions_for_users(object_id=object_id, include_instrument_responsible_users=False, include_groups=False)
    group_permissions = get_object_permissions_for_groups(object_id=object_id)
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
        edit_user_permissions_form = ObjectPermissionsForm(public_permissions=public_permissions.name.lower(), user_permissions=user_permission_form_data, group_permissions=group_permission_form_data)
        users = User.query.all()
        users = [user for user in users if user.id not in user_permissions]
        add_user_permissions_form = ObjectUserPermissionsForm()
        groups = get_user_groups(flask_login.current_user.id)
        groups = [group for group in groups if group.id not in group_permissions]
        add_group_permissions_form = ObjectGroupPermissionsForm()
    else:
        edit_user_permissions_form = None
        add_user_permissions_form = None
        add_group_permissions_form = None
        users = []
        groups = []
    return flask.render_template('objects/object_permissions.html', instrument=instrument, action=action, object=object, user_permissions=user_permissions, group_permissions=group_permissions, public_permissions=public_permissions, User=User, Permissions=Permissions, form=edit_user_permissions_form, users=users, groups=groups, add_user_permissions_form=add_user_permissions_form, add_group_permissions_form=add_group_permissions_form, get_group=get_group)


@frontend.route('/objects/<int:object_id>/permissions', methods=['POST'])
@object_permissions_required(Permissions.GRANT)
def update_object_permissions(object_id):

    edit_user_permissions_form = ObjectPermissionsForm()
    add_user_permissions_form = ObjectUserPermissionsForm()
    add_group_permissions_form = ObjectGroupPermissionsForm()
    if 'edit_user_permissions' in flask.request.form and edit_user_permissions_form.validate_on_submit():
        set_object_public(object_id, edit_user_permissions_form.public_permissions.data == 'read')
        for user_permissions_data in edit_user_permissions_form.user_permissions.data:
            user_id = user_permissions_data['user_id']
            user = get_user(user_id)
            if user is None:
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
        user_log.edit_object_permissions(user_id=flask_login.current_user.id, object_id=object_id)
        flask.flash("Successfully updated object permissions.", 'success')
    elif 'add_user_permissions' in flask.request.form and add_user_permissions_form.validate_on_submit():
        user_id = add_user_permissions_form.user_id.data
        permissions = Permissions.from_name(add_user_permissions_form.permissions.data)
        object_permissions = get_object_permissions_for_users(object_id=object_id, include_instrument_responsible_users=False, include_groups=False)
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
    else:
        flask.flash("A problem occurred while changing the object permissions. Please try again.", 'error')
    return flask.redirect(flask.url_for('.object_permissions', object_id=object_id))
