# coding: utf-8
"""

"""

import json
import os
import jsonschema.exceptions
import flask
import flask_login

from ..logic import instruments
from ..logic import schemas
from ..utils import http_auth_required

from . import rest_api

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'schemas')

INSTRUMENT_SCHEMA = json.load(open(os.path.join(SCHEMA_DIR, 'instrument.json'), 'r'))
ACTION_SCHEMA = json.load(open(os.path.join(SCHEMA_DIR, 'action.json'), 'r'))
jsonschema.Draft4Validator.check_schema(INSTRUMENT_SCHEMA)
jsonschema.Draft4Validator.check_schema(ACTION_SCHEMA)

# TODO: instrument permissions


@rest_api.route('/instruments/', methods=['GET'])
@http_auth_required
def get_instruments():
    return flask.jsonify([
        {
            'id': instrument.id,
            'name': instrument.name,
            'description': instrument.description,
            'responsible_users': [
                user.id for user in instrument.responsible_users
            ]
        }
        for instrument in instruments.get_instruments()
    ])


@rest_api.route('/instruments/', methods=['POST'])
@http_auth_required
def create_instrument():
    try:
        data = json.loads(flask.request.data.decode('utf-8'))
    except json.JSONDecodeError:
        return flask.abort(400)
    try:
        jsonschema.validate(data, INSTRUMENT_SCHEMA)
    except jsonschema.ValidationError:
        flask.abort(400)
    if {'name', 'description'} != set(data.keys()):
        return flask.abort(400)
    name = data['name']
    description = data['description']
    instrument = instruments.create_instrument(name=name, description=description)
    return flask.jsonify({
        'id': instrument.id,
        'name': instrument.name,
        'description': instrument.description,
        'responsible_users': [
            user.id for user in instrument.responsible_users
        ]
    }), 201, {'Location': flask.url_for('.get_instrument', instrument_id=instrument.id)}


@rest_api.route('/instruments/<int:instrument_id>', methods=['GET'])
@http_auth_required
def get_instrument(instrument_id):
    instrument = instruments.get_instrument(instrument_id=instrument_id)
    if instrument is None:
        return flask.abort(404)
    return flask.jsonify({
        'id': instrument.id,
        'name': instrument.name,
        'description': instrument.description,
        'responsible_users': [
            user.id for user in instrument.responsible_users
        ]
    })


@rest_api.route('/instruments/<int:instrument_id>', methods=['PUT'])
@http_auth_required
def update_instrument(instrument_id):
    instrument = instruments.get_instrument(instrument_id=instrument_id)
    if instrument is None:
        return flask.abort(404)
    try:
        data = json.loads(flask.request.data.decode('utf-8'))
    except json.JSONDecodeError:
        return flask.abort(400)
    try:
        jsonschema.validate(data, INSTRUMENT_SCHEMA)
    except jsonschema.ValidationError:
        flask.abort(400)
    if {'id', 'name', 'description', 'responsible_users'} != set(data.keys()):
        return flask.abort(400)
    if data['id'] != instrument_id:
        return flask.abort(400)
    name = data['name']
    description = data['description']
    instrument = instruments.update_instrument(instrument_id=instrument_id, name=name, description=description)
    removed_responsible_user_ids = {user.id for user in instrument.responsible_users} - set(data['responsible_users'])
    for removed_responsible_user_id in removed_responsible_user_ids:
        instruments.remove_instrument_responsible_user(instrument_id=instrument.id, user_id=removed_responsible_user_id)
    added_responsible_user_ids = set(data['responsible_users']) - {user.id for user in instrument.responsible_users}
    for added_responsible_user_id in added_responsible_user_ids:
        instruments.add_instrument_responsible_user(instrument_id=instrument.id, user_id=added_responsible_user_id)
    return flask.jsonify({
        'id': instrument.id,
        'name': instrument.name,
        'description': instrument.description,
        'responsible_users': [
            user.id for user in instrument.responsible_users
        ]
    })


@rest_api.route('/actions/', methods=['GET'])
@http_auth_required
def get_actions():
    actions = instruments.get_actions()
    return flask.jsonify([
        {
            'id': action.id,
            'instrument_id': action.instrument_id,
            'name': action.name,
            'description': action.description,
            'schema': action.schema
        }
        for action in actions
    ])


@rest_api.route('/actions/<int:action_id>', methods=['GET'])
@http_auth_required
def get_action(action_id):
    action = instruments.get_action(action_id=action_id)
    if action is None:
        return flask.abort(404)
    return flask.jsonify({
        'id': action.id,
        'instrument_id': action.instrument_id,
        'name': action.name,
        'description': action.description,
        'schema': action.schema
    })


@rest_api.route('/actions/<int:action_id>', methods=['PUT'])
@http_auth_required
def update_action(action_id):
    action = instruments.get_action(action_id=action_id)
    if action is None:
        return flask.abort(404)
    try:
        data = json.loads(flask.request.data.decode('utf-8'))
    except json.JSONDecodeError:
        return flask.abort(400)
    try:
        jsonschema.validate(data, ACTION_SCHEMA)
    except jsonschema.ValidationError:
        flask.abort(400)
    if {'id', 'name', 'description', 'schema', 'instrument_id'} != set(data.keys()):
        return flask.abort(400)
    if data['id'] != action_id:
        return flask.abort(400)
    if data['instrument_id'] != action.instrument_id:
        return flask.abort(400)
    name = data['name']
    description = data['description']
    schema = data['schema']
    try:
        action = instruments.update_action(action_id=action_id, name=name, description=description, schema=schema)
    except schemas.ValidationError:
        return flask.abort(400)
    return flask.jsonify({
        'id': action.id,
        'instrument_id': action.instrument_id,
        'name': action.name,
        'description': action.description,
        'schema': action.schema
    })


@rest_api.route('/actions/', methods=['POST'])
@http_auth_required
def create_action():
    try:
        data = json.loads(flask.request.data.decode('utf-8'))
    except json.JSONDecodeError:
        return flask.abort(400)
    try:
        jsonschema.validate(data, ACTION_SCHEMA)
    except jsonschema.ValidationError:
        flask.abort(400)
    if {'name', 'description', 'instrument_id', 'schema'} != set(data.keys()):
        return flask.abort(400)
    instrument_id = data['instrument_id']
    name = data['name']
    description = data['description']
    schema = data['schema']
    try:
        action = instruments.create_action(name=name, description=description, schema=schema, instrument_id=instrument_id)
    except schemas.ValidationError:
        return flask.abort(400)
    return flask.jsonify({
        'id': action.id,
        'instrument_id': action.instrument_id,
        'name': action.name,
        'description': action.description,
        'schema': action.schema
    }), 201, {'Location': flask.url_for('.get_action', action_id=action.id)}
