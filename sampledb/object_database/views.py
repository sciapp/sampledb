# coding: utf-8
"""

"""

import json
import os

import flask
import flask_login
import jsonschema

from . import datatypes
from .models import Objects
from ..instruments.logic import get_action

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

object_api = flask.Blueprint('object_api', __name__, template_folder='templates')

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schemas')

OBJECT_SCHEMA = json.load(open(os.path.join(SCHEMA_DIR, 'object.json'), 'r'))
jsonschema.Draft4Validator.check_schema(OBJECT_SCHEMA)


@object_api.route('/<int:object_id>/versions/<int:version_id>')
def get_object_version(object_id, version_id):
    obj = Objects.get_object_version(object_id, version_id)
    if obj is None:
        flask.abort(404)
    return flask.jsonify({
        'object_id': obj.object_id,
        'version_id': obj.version_id,
        'user_id': obj.user_id,
        'last_modified': obj.utc_datetime.strftime('%Y-%m-%d %H:%M:%S'),
        'data': obj.data,
        'schema': obj.schema
    })


@object_api.route('/<int:object_id>')
def get_object(object_id):
    obj = Objects.get_current_object(object_id)
    if obj is None:
        flask.abort(404)
    return flask.jsonify({
        'object_id': obj.object_id,
        'version_id': obj.version_id,
        'user_id': obj.user_id,
        'last_modified': obj.utc_datetime.strftime('%Y-%m-%d %H:%M:%S'),
        'data': obj.data,
        'schema': obj.schema
    })


@object_api.route('/')
def get_objects():
    objects = Objects.get_current_objects()
    # Search should be done here using query parameters
    return flask.jsonify([{
        'object_id': obj.object_id,
        'version_id': obj.version_id,
        'user_id': obj.user_id,
        'last_modified': obj.utc_datetime.strftime('%Y-%m-%d %H:%M:%S'),
        'data': obj.data,
        'schema': obj.schema
    } for obj in objects])


@object_api.route('/', methods=['POST'])
@flask_login.login_required
def create_object():
    user_id = flask_login.current_user.id
    if not flask.request.is_json:
        flask.abort(400)
    obj = flask.request.json
    try:
        jsonschema.validate(obj, OBJECT_SCHEMA)
    except jsonschema.ValidationError:
        flask.abort(400)
    if 'action_id' not in obj:
        flask.abort(400)
    action = get_action(action_id=obj['action_id'])
    if action is None:
        flask.abort(400)
    if obj['schema'] != action.schema:
        flask.abort(400)
    if 'object_id' in obj:
        flask.abort(400)
    if 'user_id' in obj and obj['user_id'] != user_id:
        flask.abort(400)
    if 'last_modified' in obj:
        # TODO: possibly allow setting last modified?
        flask.abort(400)
    if 'version_id' in obj and obj['version_id'] != 0:
        flask.abort(400)
    obj = Objects.create_object(
        action_id=obj['action_id'],
        data=obj['data'],
        schema=obj['schema'],
        user_id=user_id
    )
    return '', 201, {'Location': flask.url_for('.get_object', object_id=obj.object_id)}


@object_api.route('/<int:object_id>', methods=['PUT'])
@flask_login.login_required
def update_object(object_id):
    current_object = Objects.get_current_object(object_id)
    if current_object is None:
        flask.abort(404)
    user_id = flask_login.current_user.id
    if not flask.request.is_json:
        flask.abort(400)
    obj = flask.request.json
    try:
        jsonschema.validate(obj, OBJECT_SCHEMA)
    except jsonschema.ValidationError:
        flask.abort(400)
    if 'object_id' in obj and obj['object_id'] != object_id:
        flask.abort(400)
    if 'action_id' in obj and obj['action_id'] != current_object.action_id:
        flask.abort(400)
    if 'user_id' in obj and obj['user_id'] != user_id:
        flask.abort(400)
    if 'last_modified' in obj:
        # TODO: possibly allow setting last modified?
        flask.abort(400)
    if 'version_id' in obj and obj['version_id'] != current_object.version_id+1:
        flask.abort(400)
    obj = Objects.update_object(object_id, obj['data'], obj['schema'], user_id=user_id)
    return '', 200, {'Location': flask.url_for('.get_object', object_id=obj.object_id)}

from .form_template_demo import render_schema