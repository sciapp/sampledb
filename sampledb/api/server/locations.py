# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask

from .authentication import multi_auth, object_permissions_required
from ..utils import Resource, ResponseData
from ...logic import errors, locations, location_permissions, users, utils
from ...models import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def location_to_json(location: locations.Location) -> typing.Dict[str, typing.Any]:
    return {
        'location_id': location.id,
        'name': utils.get_translated_text(location.name, 'en') if location.name else None,
        'description': utils.get_translated_text(location.description, 'en'),
        'parent_location_id': location.parent_location_id,
        'type_id': location.type_id,
        'is_hidden': location.is_hidden,
        'enable_object_assignments': location.enable_object_assignments,
    }


def location_type_to_json(location_type: locations.LocationType) -> typing.Dict[str, typing.Any]:
    return {
        'location_type_id': location_type.id,
        'name': location_type.name.get('en', None) if location_type.name else None,
    }


def object_location_assignment_to_json(object_location_assignment: locations.ObjectLocationAssignment) -> typing.Dict[str, typing.Any]:
    return {
        'object_id': object_location_assignment.object_id,
        'location_id': object_location_assignment.location_id,
        'responsible_user_id': object_location_assignment.responsible_user_id,
        'user_id': object_location_assignment.user_id,
        'description': utils.get_translated_text(object_location_assignment.description, 'en'),
        'utc_datetime': object_location_assignment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S') if object_location_assignment.utc_datetime is not None else None
    }


class Location(Resource):
    @multi_auth.login_required
    def get(self, location_id: int) -> ResponseData:
        try:
            location = locations.get_location(location_id=location_id)
        except errors.LocationDoesNotExistError:
            return {
                "message": f"location {location_id} does not exist"
            }, 404
        permissions = location_permissions.location_permissions.get_permissions_for_user(
            resource_id=location_id,
            user_id=flask.g.user.id,
            include_all_users=True,
            include_groups=True,
            include_projects=True,
            include_admin_permissions=True,
            limit_readonly_users=True
        )
        if Permissions.READ not in permissions:
            return flask.abort(403)
        return location_to_json(location)

    @multi_auth.login_required
    def put(self, location_id: int) -> ResponseData:
        if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask.g.user.is_admin:
            return {
                "message": "only administrators may manage locations"
            }, 403
        try:
            location = locations.get_location(location_id)
        except errors.LocationDoesNotExistError:
            return {
                "message": "location does not exist"
            }, 404
        if Permissions.WRITE not in location_permissions.get_user_location_permissions(location_id, flask.g.user.id):
            return {
                "message": "insufficient permissions for location"
            }, 403
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, dict):
            return {
                "message": "JSON object body required"
            }, 400
        if request_json.get('location_id', location_id) != location_id:
            return {
                "message": f"location_id must be {location_id}"
            }, 400
        for key in ['name', 'description', 'parent_location_id', 'type_id', 'is_hidden', 'enable_object_assignments']:
            if key not in request_json:
                return {
                    "message": f"missing property '{key}'"
                }, 400
        name = request_json['name']
        if type(name) is not str:
            return {
                "message": "name must be str"
            }, 400
        description = request_json['description']
        if type(description) is not str:
            return {
                "message": "description must be str"
            }, 400
        parent_location_id = request_json['parent_location_id']
        if parent_location_id is not None and type(parent_location_id) is not int:
            return {
                "message": "parent_location_id must be int or null"
            }, 400
        if parent_location_id is not None:
            try:
                parent_location = locations.get_location(parent_location_id)
            except errors.LocationDoesNotExistError:
                return {
                    "message": "parent location does not exist"
                }, 400
            if Permissions.WRITE not in location_permissions.get_user_location_permissions(parent_location_id, flask.g.user.id):
                return {
                    "message": "insufficient permissions for parent location"
                }, 403
            if not parent_location.type.enable_sub_locations:
                return {
                    "message": "parent location type does not allow having sub locations"
                }, 400
        type_id = request_json['type_id']
        if type(type_id) is not int:
            return {
                "message": "type_id must be int"
            }, 400
        try:
            location_type = locations.get_location_type(type_id)
        except errors.LocationTypeDoesNotExistError:
            return {
                "message": "location type does not exist"
            }, 400
        if not location_type.enable_parent_location and parent_location_id is not None:
            return {
                "message": "location type does not allow having a parent location"
            }, 400
        is_hidden = request_json['is_hidden']
        if type(is_hidden) is not bool:
            return {
                "message": "is_hidden must be boolean"
            }, 400
        enable_object_assignments = request_json['enable_object_assignments']
        if type(enable_object_assignments) is not bool:
            return {
                "message": "enable_object_assignments must be boolean"
            }, 400
        locations.update_location(
            location_id=location_id,
            name={'en': name},
            description={'en': description},
            parent_location_id=parent_location_id,
            user_id=flask.g.user.id,
            type_id=type_id,
            is_hidden=is_hidden,
            enable_object_assignments=enable_object_assignments
        )
        location = locations.get_location(location.id)
        return location_to_json(location), 200


class Locations(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        return [
            location_to_json(location)
            for location in location_permissions.get_locations_with_user_permissions(
                user_id=flask.g.user.id,
                permissions=Permissions.READ
            )
        ]

    @multi_auth.login_required
    def post(self) -> ResponseData:
        if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask.g.user.is_admin:
            return {
                "message": "only administrators may manage locations"
            }, 403
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, dict):
            return {
                "message": "JSON object body required"
            }, 400
        name = ''
        if 'name' in request_json:
            if type(request_json['name']) is not str:
                return {
                    "message": "name must be str"
                }, 400
            name = request_json['name']
        description = ''
        if 'description' in request_json:
            if type(request_json['description']) is not str:
                return {
                    "message": "description must be str"
                }, 400
            description = request_json['description']
        parent_location_id = None
        if request_json.get('parent_location_id') is not None:
            if type(request_json['parent_location_id']) is not int:
                return {
                    "message": "parent_location_id must be int"
                }, 400
            parent_location_id = request_json['parent_location_id']
            try:
                parent_location = locations.get_location(parent_location_id)
            except errors.LocationDoesNotExistError:
                return {
                    "message": "parent location does not exist"
                }, 400
            if Permissions.WRITE not in location_permissions.get_user_location_permissions(parent_location_id, flask.g.user.id):
                return {
                    "message": "insufficient permissions for parent location"
                }, 403
            if not parent_location.type.enable_sub_locations:
                return {
                    "message": "parent location type does not allow having sub locations"
                }, 400
        type_id = locations.LocationType.LOCATION
        if 'type_id' in request_json:
            if type(request_json['type_id']) is not int:
                return {
                    "message": "type_id must be int"
                }, 400
            type_id = request_json['type_id']
            try:
                location_type = locations.get_location_type(type_id)
            except errors.LocationTypeDoesNotExistError:
                return {
                    "message": "location type does not exist"
                }, 400
            if location_type.admin_only and not flask.g.user.is_admin:
                return {
                    "message": "location type may only be used by administrators"
                }, 403
            if not location_type.enable_parent_location and parent_location_id is not None:
                return {
                    "message": "location type does not allow having a parent location"
                }, 400
        location = locations.create_location(
            name={'en': name},
            description={'en': description},
            parent_location_id=parent_location_id,
            user_id=flask.g.user.id,
            type_id=type_id
        )
        return flask.redirect(
            flask.url_for('.location', location_id=location.id),
            201
        )


class LocationType(Resource):
    @multi_auth.login_required
    def get(self, location_type_id: int) -> ResponseData:
        try:
            location_type = locations.get_location_type(location_type_id=location_type_id)
        except errors.LocationTypeDoesNotExistError:
            return {
                "message": f"location type {location_type_id} does not exist"
            }, 404
        return location_type_to_json(location_type)


class LocationTypes(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        return [
            location_type_to_json(location_type)
            for location_type in locations.get_location_types()
        ]


class ObjectLocationAssignment(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, object_location_assignment_index: int) -> ResponseData:
        try:
            object_location_assignments = locations.get_object_location_assignments(object_id=object_id)
        except errors.ObjectDoesNotExistError:
            return {
                "message": f"object {object_id} does not exist"
            }, 404
        if object_location_assignment_index < 0 or object_location_assignment_index >= len(object_location_assignments):
            return {
                "message": f"location assignment {object_location_assignment_index} for object {object_id} does not exist"
            }, 404
        return object_location_assignment_to_json(object_location_assignments[object_location_assignment_index])


class ObjectLocationAssignments(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        try:
            return [
                object_location_assignment_to_json(object_location_assignment)
                for object_location_assignment in locations.get_object_location_assignments(object_id)
            ]
        except errors.ObjectDoesNotExistError:
            return {
                "message": f"object {object_id} does not exist"
            }, 404

    @object_permissions_required(Permissions.WRITE)
    def post(self, object_id: int) -> ResponseData:
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, dict):
            return {
                "message": "JSON object body required"
            }, 400
        if 'object_id' in request_json:
            if request_json['object_id'] != object_id:
                return {
                    "message": f"object_id must be {object_id}"
                }, 400
        location_id = None
        if 'location_id' in request_json:
            if type(request_json['location_id']) is not int:
                return {
                    "message": "location_id must be int"
                }, 400
            location_id = request_json['location_id']
        responsible_user_id = None
        if 'responsible_user_id' in request_json:
            if type(request_json['responsible_user_id']) is not int:
                return {
                    "message": "responsible_user_id must be int"
                }, 400
            responsible_user_id = request_json['responsible_user_id']
        description = ''
        if 'description' in request_json:
            if type(request_json['description']) is not str:
                return {
                    "message": "description must be str"
                }, 400
            description = request_json['description']
        if location_id is None and responsible_user_id is None:
            return {
                "message": "at least one of location_id and responsible_user_id must be set"
            }, 400
        if location_id is not None:
            try:
                location = locations.get_location(location_id=location_id)
            except errors.LocationDoesNotExistError:
                return {
                    "message": "location does not exist"
                }, 400
            if Permissions.READ not in location_permissions.get_user_location_permissions(location_id, flask.g.user.id):
                return {
                    "message": "no permissions for location"
                }, 403
            if not location.enable_object_assignments or not location.type.enable_object_assignments:
                return {
                    "message": "location does not allow object assignments"
                }, 400

        if responsible_user_id is not None:
            try:
                users.check_user_exists(responsible_user_id)
            except errors.UserDoesNotExistError:
                return {
                    "message": "user does not exist"
                }, 400
        try:
            locations.assign_location_to_object(
                object_id=object_id,
                location_id=location_id,
                responsible_user_id=responsible_user_id,
                user_id=flask.g.user.id,
                description={'en': description}
            )
        except errors.ExceedingLocationCapacityError:
            return {
                "message": "capacity of location exceeded"
            }, 400
        object_location_assignment = locations.get_object_location_assignments(object_id)[-1]
        return flask.redirect(
            flask.url_for('.object_location_assignment', object_id=object_id, object_location_assignment_index=object_location_assignment.id),
            201
        )
