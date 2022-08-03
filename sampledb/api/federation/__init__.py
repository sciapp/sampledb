# coding: utf-8
"""
API for data exchange in SampleDB federations
"""

from flask_restful import Api
from .federation import UpdateHook, Objects, Users

api = Api()
api.add_resource(UpdateHook, '/federation/v1/hooks/update/', endpoint='federation.hooks.update')
api.add_resource(Objects, '/federation/v1/shares/objects/', endpoint='federation.object_updates')
api.add_resource(Users, '/federation/v1/shares/users/', endpoint='federation.users')
