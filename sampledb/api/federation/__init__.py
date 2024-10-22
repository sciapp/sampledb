# coding: utf-8
"""
API for data exchange in SampleDB federations
"""

from flask import Blueprint
from .federation import UpdateHook, ImportStatus, Objects, Users, File, Components, FederatedLoginMetadata

federation_api = Blueprint('federation_api', __name__)
federation_api.add_url_rule('/federation/v1/hooks/update/', endpoint='hooks_update', view_func=UpdateHook.as_view('update_hook'))
federation_api.add_url_rule('/federation/v1/shares/objects/<int:object_id>/import_status', endpoint='import_status', view_func=ImportStatus.as_view('import_status'))
federation_api.add_url_rule('/federation/v1/shares/objects/', endpoint='object_updates', view_func=Objects.as_view('objects'))
federation_api.add_url_rule('/federation/v1/shares/users/', endpoint='users', view_func=Users.as_view('users'))
federation_api.add_url_rule('/federation/v1/shares/objects/<int:object_id>/files/<int:file_id>', endpoint='file', view_func=File.as_view('file'))
federation_api.add_url_rule('/federation/v1/shares/components/', endpoint='components', view_func=Components.as_view('components'))
federation_api.add_url_rule('/federation/v1/shares/metadata/', endpoint='federated_login_metadata', view_func=FederatedLoginMetadata.as_view('federated_login_metadata'))
