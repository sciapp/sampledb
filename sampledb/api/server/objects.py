# coding: utf-8
"""
RESTful API for iffSamples
"""

import json
import flask

from flask_restful import Resource

from sampledb.api.server.authentication import multi_auth, object_permissions_required, Permissions
from sampledb.logic.actions import get_action
from sampledb.logic.objects import get_object, update_object, create_object
from sampledb.logic.object_permissions import get_objects_with_permissions
from sampledb.logic import errors

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
        return {
            'object_id': object.object_id,
            'version_id': object.version_id,
            'action_id': object.action_id,
            'schema': object.schema,
            'data': object.data
        }


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
        # TODO: implement filters
        def filter_func(data):
            return True
        action_id = None
        action_type = None
        project_id = None
        search_notes = []
        try:
            objects = get_objects_with_permissions(
                user_id=flask.g.user.id,
                permissions=Permissions.READ,
                filter_func=filter_func,
                action_id=action_id,
                action_type=action_type,
                project_id=project_id
            )
        except Exception as e:
            search_notes.append(('error', "Error during search: {}".format(e), 0, 0))
            objects = []
        # TODO handle search notes and set error code
        return [
            {
                'object_id': object.object_id,
                'version_id': object.version_id,
                'action_id': object.action_id,
                'schema': object.schema,
                'data': object.data
            }
            for object in objects
        ]

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
