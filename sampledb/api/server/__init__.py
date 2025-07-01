# coding: utf-8
"""
RESTful API for SampleDB
"""

from flask import Blueprint
from flask_cors import CORS
from .objects import Object, Objects, ObjectVersion, ObjectVersions, RelatedObjects
from .actions import Action, Actions
from .action_types import ActionType, ActionTypes
from .authentication import AccessTokens
from .comments import ObjectComment, ObjectComments
from .files import ObjectFile, ObjectFiles
from .instruments import Instrument, Instruments
from .instrument_log import InstrumentLogEntry, InstrumentLogEntries, InstrumentLogEntryFileAttachment, InstrumentLogEntryFileAttachments, InstrumentLogEntryObjectAttachment, InstrumentLogEntryObjectAttachments, InstrumentLogCategory, InstrumentLogCategories
from .locations import Location, Locations, ObjectLocationAssignment, ObjectLocationAssignments, LocationType, LocationTypes
from .object_log import ObjectLogEntries
from .object_permissions import UsersObjectPermissions, UserObjectPermissions, GroupsObjectPermissions, GroupObjectPermissions, ProjectsObjectPermissions, ProjectObjectPermissions, PublicObjectPermissions, AuthenticatedUserObjectPermissions, AnonymousUserObjectPermissions
from .users import CurrentUser, User, Users
from .groups import Group, Groups
from .projects import Project, Projects

api = Blueprint('api', __name__)
CORS(api)
api.add_url_rule('/api/v1/objects/', endpoint='objects', view_func=Objects.as_view('objects'))
api.add_url_rule('/api/v1/objects/<int:object_id>', endpoint='object', view_func=Object.as_view('object'))
api.add_url_rule('/api/v1/objects/<int:object_id>/versions/', endpoint='object_versions', view_func=ObjectVersions.as_view('object_versions'))
api.add_url_rule('/api/v1/objects/<int:object_id>/versions/<int:version_id>', endpoint='object_version', view_func=ObjectVersion.as_view('object_version'))
api.add_url_rule('/api/v1/objects/<int:object_id>/related_objects', endpoint='related_objects', view_func=RelatedObjects.as_view('related_objects'))
api.add_url_rule('/api/v1/actions/', endpoint='actions', view_func=Actions.as_view('actions'))
api.add_url_rule('/api/v1/actions/<int:action_id>', endpoint='action', view_func=Action.as_view('action'))
api.add_url_rule('/api/v1/action_types/', endpoint='action_types', view_func=ActionTypes.as_view('action_types'))
api.add_url_rule('/api/v1/action_types/<int(signed=True):type_id>', endpoint='action_type', view_func=ActionType.as_view('action_type'))
api.add_url_rule('/api/v1/access_tokens/', endpoint='access_tokens', view_func=AccessTokens.as_view('access_tokens'))
api.add_url_rule('/api/v1/objects/<int:object_id>/comments/', endpoint='object_comments', view_func=ObjectComments.as_view('object_comments'))
api.add_url_rule('/api/v1/objects/<int:object_id>/comments/<int:comment_id>', endpoint='object_comment', view_func=ObjectComment.as_view('object_comment'))
api.add_url_rule('/api/v1/instruments/', endpoint='instruments', view_func=Instruments.as_view('instruments'))
api.add_url_rule('/api/v1/instruments/<int:instrument_id>', endpoint='instrument', view_func=Instrument.as_view('instrument'))
api.add_url_rule('/api/v1/instruments/<int:instrument_id>/log_entries/', endpoint='instrument_log_entries', view_func=InstrumentLogEntries.as_view('instrument_log_entries'))
api.add_url_rule('/api/v1/instruments/<int:instrument_id>/log_entries/<int:log_entry_id>', endpoint='instrument_log_entry', view_func=InstrumentLogEntry.as_view('instrument_log_entry'))
api.add_url_rule('/api/v1/instruments/<int:instrument_id>/log_entries/<int:log_entry_id>/file_attachments/', endpoint='instrument_log_entry_file_attachments', view_func=InstrumentLogEntryFileAttachments.as_view('instrument_log_entry_file_attachments'))
api.add_url_rule('/api/v1/instruments/<int:instrument_id>/log_entries/<int:log_entry_id>/file_attachments/<int:file_attachment_id>', endpoint='instrument_log_entry_file_attachment', view_func=InstrumentLogEntryFileAttachment.as_view('instrument_log_entry_file_attachment'))
api.add_url_rule('/api/v1/instruments/<int:instrument_id>/log_entries/<int:log_entry_id>/object_attachments/', endpoint='instrument_log_entry_object_attachments', view_func=InstrumentLogEntryObjectAttachments.as_view('instrument_log_entry_object_attachments'))
api.add_url_rule('/api/v1/instruments/<int:instrument_id>/log_entries/<int:log_entry_id>/object_attachments/<int:object_attachment_id>', endpoint='instrument_log_entry_object_attachment', view_func=InstrumentLogEntryObjectAttachment.as_view('instrument_log_entry_object_attachment'))
api.add_url_rule('/api/v1/instruments/<int:instrument_id>/log_categories/', endpoint='instrument_log_categories', view_func=InstrumentLogCategories.as_view('instrument_log_categories'))
api.add_url_rule('/api/v1/instruments/<int:instrument_id>/log_categories/<int:category_id>', endpoint='instrument_log_category', view_func=InstrumentLogCategory.as_view('instrument_log_category'))
api.add_url_rule('/api/v1/locations/', endpoint='locations', view_func=Locations.as_view('locations'))
api.add_url_rule('/api/v1/locations/<int:location_id>', endpoint='location', view_func=Location.as_view('location'))
api.add_url_rule('/api/v1/location_types/', endpoint='location_types', view_func=LocationTypes.as_view('location_types'))
api.add_url_rule('/api/v1/location_types/<int(signed=True):location_type_id>', endpoint='location_type', view_func=LocationType.as_view('location_type'))
api.add_url_rule('/api/v1/objects/<int:object_id>/files/', endpoint='object_files', view_func=ObjectFiles.as_view('object_files'))
api.add_url_rule('/api/v1/objects/<int:object_id>/files/<int:file_id>', endpoint='object_file', view_func=ObjectFile.as_view('object_file'))
api.add_url_rule('/api/v1/objects/<int:object_id>/locations/', endpoint='object_location_assignments', view_func=ObjectLocationAssignments.as_view('object_location_assignments'))
api.add_url_rule('/api/v1/objects/<int:object_id>/locations/<int:object_location_assignment_index>', endpoint='object_location_assignment', view_func=ObjectLocationAssignment.as_view('object_location_assignment'))
api.add_url_rule('/api/v1/objects/<int:object_id>/permissions/users/', endpoint='users_object_permissions', view_func=UsersObjectPermissions.as_view('users_object_permissions'))
api.add_url_rule('/api/v1/objects/<int:object_id>/permissions/users/<int:user_id>', endpoint='user_object_permissions', view_func=UserObjectPermissions.as_view('user_object_permissions'))
api.add_url_rule('/api/v1/objects/<int:object_id>/permissions/groups/', endpoint='groups_object_permissions', view_func=GroupsObjectPermissions.as_view('groups_object_permissions'))
api.add_url_rule('/api/v1/objects/<int:object_id>/permissions/groups/<int:group_id>', endpoint='group_object_permissions', view_func=GroupObjectPermissions.as_view('group_object_permissions'))
api.add_url_rule('/api/v1/objects/<int:object_id>/permissions/projects/', endpoint='projects_object_permissions', view_func=ProjectsObjectPermissions.as_view('projects_object_permissions'))
api.add_url_rule('/api/v1/objects/<int:object_id>/permissions/projects/<int:project_id>', endpoint='project_object_permissions', view_func=ProjectObjectPermissions.as_view('project_object_permissions'))
api.add_url_rule('/api/v1/objects/<int:object_id>/permissions/public', endpoint='public_object_permissions', view_func=PublicObjectPermissions.as_view('public_object_permissions'))
api.add_url_rule('/api/v1/objects/<int:object_id>/permissions/authenticated_users', endpoint='all_user_object_permissions', view_func=AuthenticatedUserObjectPermissions.as_view('all_user_object_permissions'))
api.add_url_rule('/api/v1/objects/<int:object_id>/permissions/anonymous_users', endpoint='anonymous_user_object_permissions', view_func=AnonymousUserObjectPermissions.as_view('anonymous_user_object_permissions'))
api.add_url_rule('/api/v1/users/', endpoint='users', view_func=Users.as_view('users'))
api.add_url_rule('/api/v1/users/<int:user_id>', endpoint='user', view_func=User.as_view('user'))
api.add_url_rule('/api/v1/users/me', endpoint='current_user', view_func=CurrentUser.as_view('current_user'))
api.add_url_rule('/api/v1/groups/', endpoint='groups', view_func=Groups.as_view('groups'))
api.add_url_rule('/api/v1/groups/<int:group_id>', endpoint='group', view_func=Group.as_view('group'))
api.add_url_rule('/api/v1/projects/', endpoint='projects', view_func=Projects.as_view('projects'))
api.add_url_rule('/api/v1/projects/<int:project_id>', endpoint='project', view_func=Project.as_view('project'))
api.add_url_rule('/api/v1/object_log_entries/', endpoint='object_log_entries', view_func=ObjectLogEntries.as_view('object_log_entry'))
