# coding: utf-8
"""

"""

import json
import jsonschema.exceptions
import flask
import flask_login

from . import logic

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

instrument_api = flask.Blueprint('instrument_api', __name__)


@instrument_api.route('/instruments/', methods=['GET'])
@flask_login.login_required
def get_instruments():
    instruments = logic.get_instruments()
    return flask.jsonify([
        {
            'id': instrument.id,
            'name': instrument.name,
            'description': instrument.description,
            'responsible_users': [
                user.id for user in instrument.responsible_users
            ]
        }
        for instrument in instruments
    ])


@instrument_api.route('/instruments/', methods=['POST'])
@flask_login.login_required
def create_instrument():
    try:
        data = json.loads(flask.request.data.decode('utf-8'))
    except json.JSONDecodeError:
        return flask.abort(400)
    # TODO: validate using schema
    if not isinstance(data, dict):
        return flask.abort(400)
    if {'name', 'description'} != set(data.keys()):
        return flask.abort(400)
    name = data['name']
    description = data['description']
    instrument = logic.create_instrument(name=name, description=description)
    return flask.jsonify({
        'id': instrument.id,
        'name': instrument.name,
        'description': instrument.description,
        'responsible_users': [
            user.id for user in instrument.responsible_users
        ]
    }), 201, {'Location': flask.url_for('.get_instrument', instrument_id=instrument.id)}


@instrument_api.route('/instruments/<int:instrument_id>', methods=['GET'])
@flask_login.login_required
def get_instrument(instrument_id):
    instrument = logic.get_instrument(instrument_id=instrument_id)
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


@instrument_api.route('/instruments/<int:instrument_id>', methods=['PUT'])
@flask_login.login_required
def update_instrument(instrument_id):
    instrument = logic.get_instrument(instrument_id=instrument_id)
    if instrument is None:
        return flask.abort(404)
    try:
        data = json.loads(flask.request.data.decode('utf-8'))
    except json.JSONDecodeError:
        return flask.abort(400)
    # TODO: validate using schema
    if not isinstance(data, dict):
        return flask.abort(400)
    if {'id', 'name', 'description', 'responsible_users'} != set(data.keys()):
        return flask.abort(400)
    if data['id'] != instrument_id:
        return flask.abort(400)
    if not isinstance(data['responsible_users'], list):
        flask.abort(400)
    name = data['name']
    description = data['description']
    instrument = logic.update_instrument(instrument_id=instrument_id, name=name, description=description)
    removed_responsible_user_ids = {user.id for user in instrument.responsible_users} - set(data['responsible_users'])
    for removed_responsible_user_id in removed_responsible_user_ids:
        logic.remove_instrument_responsible_user(instrument_id=instrument.id, user_id=removed_responsible_user_id)
    added_responsible_user_ids = set(data['responsible_users']) - {user.id for user in instrument.responsible_users}
    for added_responsible_user_id in added_responsible_user_ids:
        logic.add_instrument_responsible_user(instrument_id=instrument.id, user_id=added_responsible_user_id)
    return flask.jsonify({
        'id': instrument.id,
        'name': instrument.name,
        'description': instrument.description,
        'responsible_users': [
            user.id for user in instrument.responsible_users
        ]
    })


@instrument_api.route('/actions/', methods=['GET'])
@flask_login.login_required
def get_actions():
    actions = logic.get_actions()
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


@instrument_api.route('/actions/<int:action_id>', methods=['GET'])
@flask_login.login_required
def get_action(action_id):
    action = logic.get_action(action_id=action_id)
    if action is None:
        return flask.abort(404)
    return flask.jsonify({
        'id': action.id,
        'instrument_id': action.instrument_id,
        'name': action.name,
        'description': action.description,
        'schema': action.schema
    })


@instrument_api.route('/actions/<int:action_id>', methods=['PUT'])
@flask_login.login_required
def update_action(action_id):
    action = logic.get_action(action_id=action_id)
    if action is None:
        return flask.abort(404)
    try:
        data = json.loads(flask.request.data.decode('utf-8'))
    except json.JSONDecodeError:
        return flask.abort(400)
    # TODO: validate using schema
    if not isinstance(data, dict):
        return flask.abort(400)
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
        action = logic.update_action(action_id=action_id, name=name, description=description, schema=schema)
    except jsonschema.exceptions.SchemaError:
        return flask.abort(400)
    return flask.jsonify({
        'id': action.id,
        'instrument_id': action.instrument_id,
        'name': action.name,
        'description': action.description,
        'schema': action.schema
    })


@instrument_api.route('/actions/', methods=['POST'])
@flask_login.login_required
def create_action():
    try:
        data = json.loads(flask.request.data.decode('utf-8'))
    except json.JSONDecodeError:
        return flask.abort(400)
    # TODO: validate using schema
    if not isinstance(data, dict):
        return flask.abort(400)
    if {'name', 'description', 'instrument_id', 'schema'} != set(data.keys()):
        return flask.abort(400)
    instrument_id = data['instrument_id']
    name = data['name']
    description = data['description']
    schema = data['schema']
    try:
        action = logic.create_action(name=name, description=description, schema=schema, instrument_id=instrument_id)
    except jsonschema.exceptions.SchemaError:
        return flask.abort(400)
    return flask.jsonify({
        'id': action.id,
        'instrument_id': action.instrument_id,
        'name': action.name,
        'description': action.description,
        'schema': action.schema
    }), 201, {'Location': flask.url_for('.get_action', action_id=action.id)}
