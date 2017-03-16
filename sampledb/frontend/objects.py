# coding: utf-8
"""

"""

import json
import jsonschema
import flask
import flask_login

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


@frontend.route('/objects/<int:object_id>', methods=['GET', 'POST'])
@object_permissions_required(Permissions.READ)
def object(object_id):
    object = Objects.get_current_object(object_id=object_id)

    flask.current_app.jinja_env.filters['to_datatype'] = to_datatype
    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    user_may_edit = Permissions.WRITE in user_permissions

    errors = []
    form_data = {}
    if flask.request.method != 'GET':
        if not user_may_edit:
            return flask.abort(403)
        # TODO: csrf protection
        # TODO: update schema
        # schema = Action.query.get(object.action_id).schema
        schema = object.schema
        object_data, errors = parse_form_data(dict(flask.request.form), schema)
        if not errors:
            try:
                jsonschema.validate(object_data, schema)
            except jsonschema.ValidationError:
                print('validation failed')
                # TODO: handle error
                flask.abort(400)
            Objects.update_object(object_id=object_id, data=object_data, schema=schema, user_id=flask_login.current_user.id)
            flask.flash('The object was updated successfully.', 'success')
            return flask.redirect(flask.url_for('.object', object_id=object_id))
        else:
            form_data = {k: v[0] for k, v in dict(flask.request.form).items()}
    if flask.request.args.get('mode') == 'edit':
        if user_may_edit:
            return flask.render_template('objects/forms/form_base.html', schema=object.schema, data=object.data, object_id=object_id, errors=errors, form_data=form_data)
        else:
            return flask.abort(403)
    return flask.render_template('objects/view/base.html', schema=object.schema, data=object.data, last_edit_datetime=object.utc_datetime, last_edit_user=User.query.get(object.user_id), object_id=object_id, user_may_edit=user_may_edit)


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
