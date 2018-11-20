# coding: utf-8
"""
RESTful API for iffSamples
"""

from flask_restful import Api
from sampledb.api.server.objects import Object, Objects, ObjectVersion, ObjectVersions


api = Api()
api.add_resource(Objects, '/api/v1/objects/', endpoint='api.objects')
api.add_resource(Object, '/api/v1/objects/<int:object_id>', endpoint='api.object')
api.add_resource(ObjectVersions, '/api/v1/objects/<int:object_id>/versions/', endpoint='api.object_versions')
api.add_resource(ObjectVersion, '/api/v1/objects/<int:object_id>/versions/<int:version_id>', endpoint='api.object_version')
