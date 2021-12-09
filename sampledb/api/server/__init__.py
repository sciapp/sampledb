# coding: utf-8
"""
RESTful API for SampleDB
"""

from flask_restful import Api
from .objects import Object, Objects, ObjectVersion, ObjectVersions
from .actions import Action, Actions
from .action_types import ActionType, ActionTypes
from .comments import ObjectComment, ObjectComments
from .files import ObjectFile, ObjectFiles
from .instruments import Instrument, Instruments
from .instrument_log import InstrumentLogEntry, InstrumentLogEntries, InstrumentLogEntryFileAttachment, InstrumentLogEntryFileAttachments, InstrumentLogEntryObjectAttachment, InstrumentLogEntryObjectAttachments, InstrumentLogCategory, InstrumentLogCategories
from .locations import Location, Locations, ObjectLocationAssignment, ObjectLocationAssignments
from .object_permissions import UsersObjectPermissions, UserObjectPermissions, GroupsObjectPermissions, GroupObjectPermissions, ProjectsObjectPermissions, ProjectObjectPermissions, PublicObjectPermissions
from .users import CurrentUser, User, Users

api = Api()
api.add_resource(Objects, '/api/v1/objects/', endpoint='api.objects')
api.add_resource(Object, '/api/v1/objects/<int:object_id>', endpoint='api.object')
api.add_resource(ObjectVersions, '/api/v1/objects/<int:object_id>/versions/', endpoint='api.object_versions')
api.add_resource(ObjectVersion, '/api/v1/objects/<int:object_id>/versions/<int:version_id>', endpoint='api.object_version')
api.add_resource(Actions, '/api/v1/actions/', endpoint='api.actions')
api.add_resource(Action, '/api/v1/actions/<int:action_id>', endpoint='api.action')
api.add_resource(ActionTypes, '/api/v1/action_types/', endpoint='api.action_types')
api.add_resource(ActionType, '/api/v1/action_types/<int(signed=True):type_id>', endpoint='api.action_type')
api.add_resource(ObjectComments, '/api/v1/objects/<int:object_id>/comments/', endpoint='api.object_comments')
api.add_resource(ObjectComment, '/api/v1/objects/<int:object_id>/comments/<int:comment_id>', endpoint='api.object_comment')
api.add_resource(Instruments, '/api/v1/instruments/', endpoint='api.instruments')
api.add_resource(Instrument, '/api/v1/instruments/<int:instrument_id>', endpoint='api.instrument')
api.add_resource(InstrumentLogEntries, '/api/v1/instruments/<int:instrument_id>/log_entries/', endpoint='api.instrument_log_entries')
api.add_resource(InstrumentLogEntry, '/api/v1/instruments/<int:instrument_id>/log_entries/<int:log_entry_id>', endpoint='api.instrument_log_entry')
api.add_resource(InstrumentLogEntryFileAttachments, '/api/v1/instruments/<int:instrument_id>/log_entries/<int:log_entry_id>/file_attachments/', endpoint='api.instrument_log_entry_file_attachments')
api.add_resource(InstrumentLogEntryFileAttachment, '/api/v1/instruments/<int:instrument_id>/log_entries/<int:log_entry_id>/file_attachments/<int:file_attachment_id>', endpoint='api.instrument_log_entry_file_attachment')
api.add_resource(InstrumentLogEntryObjectAttachments, '/api/v1/instruments/<int:instrument_id>/log_entries/<int:log_entry_id>/object_attachments/', endpoint='api.instrument_log_entry_object_attachments')
api.add_resource(InstrumentLogEntryObjectAttachment, '/api/v1/instruments/<int:instrument_id>/log_entries/<int:log_entry_id>/object_attachments/<int:object_attachment_id>', endpoint='api.instrument_log_entry_object_attachment')
api.add_resource(InstrumentLogCategories, '/api/v1/instruments/<int:instrument_id>/log_categories/', endpoint='api.instrument_log_categories')
api.add_resource(InstrumentLogCategory, '/api/v1/instruments/<int:instrument_id>/log_categories/<int:category_id>', endpoint='api.instrument_log_category')
api.add_resource(Locations, '/api/v1/locations/', endpoint='api.locations')
api.add_resource(Location, '/api/v1/locations/<int:location_id>', endpoint='api.location')
api.add_resource(ObjectFiles, '/api/v1/objects/<int:object_id>/files/', endpoint='api.object_files')
api.add_resource(ObjectFile, '/api/v1/objects/<int:object_id>/files/<int:file_id>', endpoint='api.object_file')
api.add_resource(ObjectLocationAssignments, '/api/v1/objects/<int:object_id>/locations/', endpoint='api.object_location_assignments')
api.add_resource(ObjectLocationAssignment, '/api/v1/objects/<int:object_id>/locations/<int:object_location_assignment_index>', endpoint='api.object_location_assignment')
api.add_resource(UsersObjectPermissions, '/api/v1/objects/<int:object_id>/permissions/users/', endpoint='api.users_object_permissions')
api.add_resource(UserObjectPermissions, '/api/v1/objects/<int:object_id>/permissions/users/<int:user_id>', endpoint='api.user_object_permissions')
api.add_resource(GroupsObjectPermissions, '/api/v1/objects/<int:object_id>/permissions/groups/', endpoint='api.groups_object_permissions')
api.add_resource(GroupObjectPermissions, '/api/v1/objects/<int:object_id>/permissions/groups/<int:group_id>', endpoint='api.group_object_permissions')
api.add_resource(ProjectsObjectPermissions, '/api/v1/objects/<int:object_id>/permissions/projects/', endpoint='api.projects_object_permissions')
api.add_resource(ProjectObjectPermissions, '/api/v1/objects/<int:object_id>/permissions/projects/<int:project_id>', endpoint='api.project_object_permissions')
api.add_resource(PublicObjectPermissions, '/api/v1/objects/<int:object_id>/permissions/public', endpoint='api.public_object_permissions')
api.add_resource(Users, '/api/v1/users/', endpoint='api.users')
api.add_resource(User, '/api/v1/users/<int:user_id>', endpoint='api.user')
api.add_resource(CurrentUser, '/api/v1/users/me', endpoint='api.current_user')
