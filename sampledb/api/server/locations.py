# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic import errors, locations, location_permissions, utils
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
        'utc_datetime': object_location_assignment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
    }


class Location(Resource):
    @multi_auth.login_required
    def get(self, location_id: int) -> ResponseData:
        try:
            location = locations.get_location(location_id=location_id)
        except errors.LocationDoesNotExistError:
            return {
                "message": "location {} does not exist".format(location_id)
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


class LocationType(Resource):
    @multi_auth.login_required
    def get(self, location_type_id: int) -> ResponseData:
        try:
            location_type = locations.get_location_type(location_type_id=location_type_id)
        except errors.LocationTypeDoesNotExistError:
            return {
                "message": "location type {} does not exist".format(location_type_id)
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
    @multi_auth.login_required
    def get(self, object_id: int, object_location_assignment_index: int) -> ResponseData:
        try:
            object_location_assignments = locations.get_object_location_assignments(object_id=object_id)
        except errors.ObjectDoesNotExistError:
            return {
                "message": "object {} does not exist".format(object_id)
            }, 404
        if object_location_assignment_index < 0 or object_location_assignment_index >= len(object_location_assignments):
            return {
                "message": "location assignment {} for object {} does not exist".format(object_location_assignment_index, object_id)
            }, 404
        return object_location_assignment_to_json(object_location_assignments[object_location_assignment_index])


class ObjectLocationAssignments(Resource):
    @multi_auth.login_required
    def get(self, object_id: int) -> ResponseData:
        try:
            return [
                object_location_assignment_to_json(object_location_assignment)
                for object_location_assignment in locations.get_object_location_assignments(object_id)
            ]
        except errors.ObjectDoesNotExistError:
            return {
                "message": "object {} does not exist".format(object_id)
            }, 404
