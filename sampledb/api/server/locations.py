# coding: utf-8
"""
RESTful API for SampleDB
"""

from flask_restful import Resource

from .authentication import multi_auth
from ...logic import errors, locations

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def location_to_json(location: locations.Location):
    return {
        'location_id': location.id,
        'name': location.name['en'],
        'description': location.description['en'],
        'parent_location_id': location.parent_location_id
    }


def object_location_assignment_to_json(object_location_assignment: locations.ObjectLocationAssignment):
    return {
        'object_id': object_location_assignment.object_id,
        'location_id': object_location_assignment.location_id,
        'responsible_user_id': object_location_assignment.responsible_user_id,
        'user_id': object_location_assignment.user_id,
        'description': object_location_assignment.description['en'],
        'utc_datetime': object_location_assignment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
    }


class Location(Resource):
    @multi_auth.login_required
    def get(self, location_id: int):
        try:
            location = locations.get_location(location_id=location_id)
        except errors.LocationDoesNotExistError:
            return {
                "message": "location {} does not exist".format(location_id)
            }, 404
        return location_to_json(location)


class Locations(Resource):
    @multi_auth.login_required
    def get(self):
        return [location_to_json(location) for location in locations.get_locations()]


class ObjectLocationAssignment(Resource):
    @multi_auth.login_required
    def get(self, object_id: id, object_location_assignment_index: int):
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
    def get(self, object_id: int):
        try:
            return [
                object_location_assignment_to_json(object_location_assignment)
                for object_location_assignment in locations.get_object_location_assignments(object_id)
            ]
        except errors.ObjectDoesNotExistError:
            return {
                "message": "object {} does not exist".format(object_id)
            }, 404
