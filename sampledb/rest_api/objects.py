# coding: utf-8
"""

"""

import json
import os

import flask
import flask_login
import jsonschema

from ..logic.permissions import get_user_object_permissions
from ..logic.instruments import get_action
from ..models import Objects, Permissions
from sampledb.utils import object_permissions_required
from . import rest_api

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'schemas')

OBJECT_SCHEMA = json.load(open(os.path.join(SCHEMA_DIR, 'object.json'), 'r'))
jsonschema.Draft4Validator.check_schema(OBJECT_SCHEMA)


@rest_api.route('/objects/<int:object_id>/versions/<int:version_id>')
@object_permissions_required(Permissions.READ)
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


@rest_api.route('/objects/<int:object_id>')
@object_permissions_required(Permissions.READ)
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


@rest_api.route('/objects/')
@flask_login.login_required
def get_objects():
    # TODO: Search should be done here using query parameters
    objects = Objects.get_current_objects()
    user_id = flask_login.current_user.id
    return flask.jsonify(
        [
            {
                'object_id': obj.object_id,
                'version_id': obj.version_id,
                'user_id': obj.user_id,
                'last_modified': obj.utc_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'data': obj.data,
                'schema': obj.schema
            }
            for obj in objects
            if Permissions.READ in get_user_object_permissions(user_id=user_id, object_id=obj.object_id)
        ]
    )


@rest_api.route('/objects/', methods=['POST'])
@flask_login.login_required
def create_object():
    # TODO: set up initial permissions
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


@rest_api.route('/objects/<int:object_id>', methods=['PUT'])
@object_permissions_required(Permissions.WRITE)
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

