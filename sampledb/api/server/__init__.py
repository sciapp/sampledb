# coding: utf-8
"""
RESTful API for iffSamples
"""

from flask_restful import Api
from .objects import Object, Objects, ObjectVersion, ObjectVersions
from .actions import Action, Actions
from .instruments import Instrument, Instruments
from .locations import Location, Locations, ObjectLocationAssignment, ObjectLocationAssignments

api = Api()
api.add_resource(Objects, '/api/v1/objects/', endpoint='api.objects')
api.add_resource(Object, '/api/v1/objects/<int:object_id>', endpoint='api.object')
api.add_resource(ObjectVersions, '/api/v1/objects/<int:object_id>/versions/', endpoint='api.object_versions')
api.add_resource(ObjectVersion, '/api/v1/objects/<int:object_id>/versions/<int:version_id>', endpoint='api.object_version')
api.add_resource(Actions, '/api/v1/actions/', endpoint='api.actions')
api.add_resource(Action, '/api/v1/actions/<int:action_id>', endpoint='api.action')
api.add_resource(Instruments, '/api/v1/instruments/', endpoint='api.instruments')
api.add_resource(Instrument, '/api/v1/instruments/<int:instrument_id>', endpoint='api.instrument')
api.add_resource(Locations, '/api/v1/locations/', endpoint='api.locations')
api.add_resource(Location, '/api/v1/locations/<int:location_id>', endpoint='api.location')
api.add_resource(ObjectLocationAssignments, '/api/v1/objects/<int:object_id>/locations/', endpoint='api.object_location_assignments')
api.add_resource(ObjectLocationAssignment, '/api/v1/objects/<int:object_id>/locations/<int:object_location_assignment_index>', endpoint='api.object_location_assignment')