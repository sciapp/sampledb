# coding: utf-8
"""

"""

import json
import jsonschema
import flask
import flask_login
import itsdangerous

from . import frontend
from ..logic.permissions import get_user_object_permissions, object_is_public, get_object_permissions, set_object_public, set_user_object_permissions
from ..logic.datatypes import JSONEncoder
from .objects_forms import ObjectPermissionsForm
from .. import db
from ..models import User, Action, Objects, Permissions
from ..utils import object_permissions_required
from .object_form_parser import parse_form_data

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/objects/')
def objects():
    objects = Objects.get_current_objects(connection=db.engine)
    if flask_login.current_user.is_authenticated:
        user_id = flask_login.current_user.id
        objects = [obj for obj in objects if Permissions.READ in get_user_object_permissions(user_id=user_id, object_id=obj.object_id)]
    else:
        objects = [obj for obj in objects if object_is_public(obj.object_id)]
    objects = [
        {
            'object_id': obj.object_id,
            'version_id': obj.version_id,
            'user_id': obj.user_id,
            'last_modified': obj.utc_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'data': obj.data,
            'schema': obj.schema
        }
        for obj in objects
    ]
    # TODO implement view
    return flask.render_template('index.html', objects=objects)


def to_datatype(obj):
    return json.loads(json.dumps(obj), object_hook=JSONEncoder.object_hook)


def generate_placeholder_object(schema):
    if 'type' in schema and schema['type'] == 'object':
        return {
            property_name: generate_placeholder_object(property_schema)
            for property_name, property_schema in schema.get('properties', {}).items()
        }
    elif 'type' in schema and schema['type'] == 'array':
        # TODO: items / minimum length
        return []
    # TODO: other types and their defaults
    return None


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
            del sub_data[int(keys[-1])]
            # TODO: minimum length
        elif action.endswith('_add'):
            sub_data.append(generate_placeholder_object(sub_schema["items"]))
            # TODO: maximum length
    except (ValueError, KeyError, IndexError, TypeError):
        # TODO: error handling/logging?
        raise ValueError('invalid action')
    return new_form_data


def show_object_form(object, action):
    if object is None:
        data = generate_placeholder_object(action.schema)
    else:
        data = object.data
    # TODO: update schema
    # schema = Action.query.get(object.action_id).schema
    if object is not None:
        schema = object.schema
    else:
        schema = action.schema
    errors = []
    form_data = {}
    previous_actions = []
    serializer = itsdangerous.URLSafeSerializer(flask.current_app.config['SECRET_KEY'])
    if flask.request.method != 'GET':
        # TODO: csrf protection
        form_data = {k: v[0] for k, v in dict(flask.request.form).items()}

        if 'previous_actions' in flask.request.form:
            try:
                previous_actions = serializer.loads(flask.request.form['previous_actions'])
            except itsdangerous.BadData:
                flask.abort(400)

        if "action_submit" in form_data:
            object_data, errors = parse_form_data(dict(flask.request.form), schema)
            if not errors:
                try:
                    jsonschema.validate(object_data, schema)
                except jsonschema.ValidationError:
                    # TODO: proper logging
                    print('object schema validation failed')
                    # TODO: handle error
                    flask.abort(400)
                if object is None:
                    object = Objects.create_object(data=object_data, schema=schema, user_id=flask_login.current_user.id, action_id=action.id)
                    flask.flash('The object was created successfully.', 'success')
                else:
                    Objects.update_object(object_id=object.object_id, data=object_data, schema=schema, user_id=flask_login.current_user.id)
                    flask.flash('The object was updated successfully.', 'success')
                return flask.redirect(flask.url_for('.object', object_id=object.object_id))
        elif any(name.startswith('action_object_') and (name.endswith('_delete') or name.endswith('_add')) for name in form_data):
            action = [name for name in form_data if name.startswith('action_')][0]
            previous_actions.append(action)
    for action in previous_actions:
        try:
            form_data = apply_action_to_data(data, schema, action, form_data)
        except ValueError:
            flask.abort(400)
    if object is None:
        return flask.render_template('objects/forms/form_create.html', schema=schema, data=data, errors=errors, form_data=form_data, previous_actions=serializer.dumps(previous_actions))
    else:
        return flask.render_template('objects/forms/form_edit.html', schema=schema, data=data, object_id=object.object_id, errors=errors, form_data=form_data, previous_actions=serializer.dumps(previous_actions))


@frontend.route('/objects/<int:object_id>', methods=['GET', 'POST'])
@object_permissions_required(Permissions.READ)
def object(object_id):
    object = Objects.get_current_object(object_id=object_id)

    # TODO: setup jinja env globally
    flask.current_app.jinja_env.filters['to_datatype'] = to_datatype
    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    user_may_edit = Permissions.WRITE in user_permissions
    if not user_may_edit and flask.request.args.get('mode', '') == 'edit':
        return flask.abort(403)
    if flask.request.method == 'GET' and flask.request.args.get('mode', '') != 'edit':
        return flask.render_template('objects/view/base.html', schema=object.schema, data=object.data, last_edit_datetime=object.utc_datetime, last_edit_user=User.query.get(object.user_id), object_id=object_id, user_may_edit=user_may_edit)

    return show_object_form(object, action=Action.query.get(object.action_id))


@frontend.route('/objects/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_object():
    action_id = flask.request.args.get('action_id', None)
    if action_id is None:
        # TODO: handle error
        return flask.abort(404)
    action = Action.query.get(action_id)
    if action is None:
        # TODO: handle error
        return flask.abort(404)

    # TODO: setup jinja env globally
    flask.current_app.jinja_env.filters['to_datatype'] = to_datatype
    # TODO: check instrument permissions
    return show_object_form(None, action)


@frontend.route('/objects/<int:object_id>/versions/')
@object_permissions_required(Permissions.READ)
def object_versions(object_id):
    object = Objects.get_current_object(object_id=object_id)
    if object is None:
        return flask.abort(404)
    object_versions = Objects.get_object_versions(object_id=object_id)
    return flask.render_template('objects/object_versions.html', User=User, object=object, object_versions=object_versions)


@frontend.route('/objects/<int:object_id>/versions/<int:version_id>')
@object_permissions_required(Permissions.READ)
def object_version(object_id, version_id):
    object = Objects.get_object_version(object_id=object_id, version_id=version_id)

    flask.current_app.jinja_env.filters['to_datatype'] = to_datatype
    return flask.render_template('objects/view/base.html', schema=object.schema, data=object.data, last_edit_datetime=object.utc_datetime, last_edit_user=User.query.get(object.user_id), object_id=object_id)


@frontend.route('/objects/<int:object_id>/permissions')
@object_permissions_required(Permissions.READ)
def object_permissions(object_id):
    object = Objects.get_current_object(object_id, connection=db.engine)
    action = Action.query.get(object.action_id)
    instrument = action.instrument
    object_permissions = get_object_permissions(object_id=object_id, include_instrument_responsible_users=False)
    if Permissions.GRANT in get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id):
        public_permissions = 'none'
        if Permissions.READ in object_permissions[None]:
            public_permissions = 'read'
        user_permissions = []
        for user_id, permissions in object_permissions.items():
            if user_id is None:
                continue
            user_permissions.append({'user_id': user_id, 'permissions': permissions.name.lower()})
        form = ObjectPermissionsForm(public_permissions=public_permissions, user_permissions=user_permissions)
    else:
        form = None
    return flask.render_template('objects/object_permissions.html', instrument=instrument, action=action, object=object, object_permissions=object_permissions, User=User, Permissions=Permissions, form=form)


@frontend.route('/objects/<int:object_id>/permissions', methods=['POST'])
@object_permissions_required(Permissions.GRANT)
def update_object_permissions(object_id):
    form = ObjectPermissionsForm()
    if form.validate_on_submit():
        set_object_public(object_id, form.public_permissions.data == 'read')
        for user_permissions_data in form.user_permissions.data:
            user_id = user_permissions_data['user_id']
            user = User.query.get(user_id)
            if user is None:
                continue
            permissions = Permissions.from_name(user_permissions_data['permissions'])
            set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=permissions)
        flask.flash("Successfully updated object permissions.", 'success')
    else:
        flask.flash("A problem occurred while changing the object permissions. Please try again.", 'error')
    return flask.redirect(flask.url_for('.object_permissions', object_id=object_id))
