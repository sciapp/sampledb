# coding: utf-8
"""
RESTful API for SampleDB
"""

import json
import flask

from flask_restful import Resource

from ...api.server.authentication import multi_auth, object_permissions_required, Permissions
from ...logic.actions import get_action, get_action_type
from ...logic.action_translations import get_action_with_translation_in_language, Language
from ...logic.action_permissions import get_user_action_permissions
from ...logic.object_search import generate_filter_func, wrap_filter_func
from ...logic.objects import get_object, update_object, create_object
from ...logic.object_permissions import get_objects_with_permissions
from ...logic import errors, users
from ... import models

from .users import user_to_json
from .actions import action_to_json

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class ObjectVersion(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, version_id: int):
        try:
            object = get_object(object_id=object_id, version_id=version_id)
        except errors.ObjectVersionDoesNotExistError:
            return {
                "message": "version {} of object {} does not exist".format(version_id, object_id)
            }, 404
        object_version_json = {
            'object_id': object.object_id,
            'version_id': object.version_id,
            'action_id': object.action_id,
            'user_id': object.user_id,
            'utc_datetime': object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'schema': object.schema,
            'data': object.data
        }
        embed_action = bool(flask.request.args.get('embed_action'))
        if embed_action:
            object_version_json['action'] = None
            try:
                if Permissions.READ in get_user_action_permissions(action_id=object.action_id, user_id=flask.g.user.id):
                    action = get_action_with_translation_in_language(
                        action_id=object.action_id,
                        language_id=Language.ENGLISH
                    )
                    object_version_json['action'] = action_to_json(action)
            except errors.ActionDoesNotExistError:
                pass
        embed_user = bool(flask.request.args.get('embed_user'))
        if embed_user:
            try:
                user = users.get_user(object.user_id)
                object_version_json['user'] = user_to_json(user)
            except errors.UserDoesNotExistError:
                object_version_json['user'] = None
        return object_version_json


class ObjectVersions(Resource):
    @object_permissions_required(Permissions.WRITE)
    def post(self, object_id: int):
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, dict):
            return {
                "message": "JSON object body required"
            }, 400
        for key in request_json:
            if key not in {'object_id', 'version_id', 'action_id', 'schema', 'data'}:
                return {
                    "message": "invalid key '{}'".format(key)
                }, 400
        object = get_object(object_id=object_id)
        action = get_action(action_id=object.action_id)
        if 'object_id' in request_json:
            if request_json['object_id'] != object.object_id:
                return {
                    "message": "object_id must be {}".format(object.object_id)
                }, 400
        if 'version_id' in request_json:
            if request_json['version_id'] != object.version_id + 1:
                return {
                    "message": "version_id must be {}".format(object.version_id + 1)
                }, 400
        if 'action_id' in request_json:
            if request_json['action_id'] != object.action_id:
                return {
                    "message": "action_id must be {}".format(object.action_id)
                }, 400
        if 'schema' in request_json:
            if request_json['schema'] != object.schema and request_json['schema'] != action.schema:
                return {
                    "message": "schema must be either:\n{}\nor:\n{}".format(json.dumps(object.schema, indent=4), json.dumps(action.schema, indent=4))
                }, 400
            schema = request_json['schema']
        else:
            schema = object.schema
        if 'data' not in request_json:
            return {
                "message": "data must be set"
            }, 400
        data = request_json['data']
        try:
            update_object(
                object_id=object.object_id,
                data=data,
                user_id=flask.g.user.id,
                schema=schema
            )
        except errors.ValidationError as e:
            messages = e.message.splitlines()
            return {
                "message": "validation failed:\n - {}".format('\n - '.join(messages))
            }, 400
        except Exception:
            return {
                "message": "failed to update object"
            }, 400
        object_version_url = flask.url_for(
            'api.object_version',
            object_id=object.object_id,
            version_id=object.version_id + 1
        )
        return flask.redirect(object_version_url, code=201)


class Object(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int):
        object = get_object(object_id=object_id)
        object_version_url = flask.url_for(
            'api.object_version',
            object_id=object.object_id,
            version_id=object.version_id
        )
        return flask.redirect(object_version_url, code=302)


class Objects(Resource):
    @multi_auth.login_required
    def get(self):
        action_id = flask.request.args.get('action_id', '')
        if action_id:
            try:
                action_id = int(action_id)
            except ValueError:
                return {
                    'message': 'Unable to parse action_id'
                }, 400
            try:
                get_action(action_id)
            except errors.ActionDoesNotExistError:
                return {
                    'message': 'No action with the given action_id exists.'
                }, 400
        else:
            action_id = None
        action_type_id = flask.request.args.get('action_type_id', flask.request.args.get('action_type', None))
        if action_type_id is not None:
            try:
                action_type_id = int(action_type_id)
            except ValueError:
                # ensure old links still function
                action_type_id = {
                    'sample': models.ActionType.SAMPLE_CREATION,
                    'measurement': models.ActionType.MEASUREMENT,
                    'simulation': models.ActionType.SIMULATION
                }.get(action_type_id, None)
            else:
                try:
                    get_action_type(action_type_id)
                except errors.ActionTypeDoesNotExistError:
                    action_type_id = None
            if action_type_id is None:
                return {
                    'message': 'No matching action type exists.'
                }, 400
        else:
            action_type_id = None
        project_id = None
        limit = flask.request.args.get('limit')
        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                limit = None
        if limit is not None and not 1 <= limit < 1e15:
            limit = None
        offset = flask.request.args.get('offset')
        if offset is not None:
            try:
                offset = int(offset)
            except ValueError:
                offset = None
        if offset is not None and not 0 <= offset < 1e15:
            offset = None
        name_only = bool(flask.request.args.get('name_only'))
        query_string = flask.request.args.get('q', '')
        if query_string:
            try:
                filter_func, search_tree, use_advanced_search = generate_filter_func(query_string, True)
            except Exception:
                # TODO: ensure that advanced search does not cause exceptions
                def filter_func(data, search_notes):
                    """ Return all objects"""
                    search_notes.append(('error', "Unable to parse search expression", 0, len(query_string)))
                    return False
            filter_func, search_notes = wrap_filter_func(filter_func)
        else:
            search_notes = []

            def filter_func(data):
                return True
        try:
            objects = get_objects_with_permissions(
                user_id=flask.g.user.id,
                permissions=Permissions.READ,
                filter_func=filter_func,
                action_id=action_id,
                action_type_id=action_type_id,
                project_id=project_id,
                limit=limit,
                offset=offset,
                name_only=name_only
            )
        except Exception as e:
            search_notes.append(('error', "Error during search: {}".format(e), 0, 0))
            objects = []
        if any(search_note[0] == 'error' for search_note in search_notes):
            return {
                'message': '\n'.join(
                    'Error: ' + search_note[1]
                    for search_note in search_notes
                    if search_note[0] == 'error'
                )
            }, 400
        else:
            return [
                {
                    'object_id': object.object_id,
                    'version_id': object.version_id,
                    'action_id': object.action_id,
                    'schema': object.schema,
                    'data': object.data
                }
                for object in objects
            ], 200

    @multi_auth.login_required
    def post(self):
        if flask.g.user.is_readonly:
            return {
                'message': 'user has been marked as read only'
            }, 400
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, dict):
            return {
                "message": "JSON object body required"
            }, 400
        for key in request_json:
            if key not in {'object_id', 'version_id', 'action_id', 'schema', 'data'}:
                return {
                    "message": "invalid key '{}'".format(key)
                }, 400
        if 'object_id' in request_json:
            return {
                "message": "object_id cannot be set"
            }, 400
        if 'version_id' in request_json:
            if request_json['version_id'] != 0:
                return {
                    "message": "version_id must be 0"
                }, 400
        if 'action_id' in request_json:
            if not isinstance(request_json['action_id'], int):
                return {
                    "message": "action_id must be an integer"
                }, 400
            action_id = request_json['action_id']
            try:
                action = get_action(action_id=action_id)
            except errors.ActionDoesNotExistError:
                return {
                    "message": "action {} does not exist".format(action_id)
                }, 400
        else:
            return {
                "message": "action_id must be set"
            }, 400
        if 'schema' in request_json:
            if request_json['schema'] != action.schema:
                return {
                    "message": "schema must be:\n{}".format(json.dumps(action.schema, indent=4))
                }, 400
        schema = action.schema
        if 'data' not in request_json:
            return {
                "message": "data must be set"
            }, 400
        data = request_json['data']
        try:
            object = create_object(
                action_id=action_id,
                data=data,
                user_id=flask.g.user.id,
                schema=schema
            )
        except errors.ValidationError as e:
            messages = e.message.splitlines()
            return {
                "message": "validation failed:\n - {}".format('\n - '.join(messages))
            }, 400
        except Exception:
            return {
                "message": "failed to create object"
            }, 400
        object_version_url = flask.url_for(
            'api.object_version',
            object_id=object.object_id,
            version_id=object.version_id
        )
        return flask.redirect(object_version_url, code=201)
