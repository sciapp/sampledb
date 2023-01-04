# coding: utf-8
"""

"""
import base64
import typing
from copy import deepcopy
import datetime
import flask
import pytest

from sampledb import logic, db
from sampledb.logic import errors, actions, instruments, object_permissions
from sampledb.logic.action_translations import get_action_translations_for_action, set_action_translation, get_action_translation_for_action_in_language
from sampledb.logic.action_type_translations import get_action_type_translations_for_action_type
from sampledb.logic.actions import get_action, get_action_type, create_action_type, create_action
from sampledb.logic.comments import get_comment, create_comment, get_comments_for_object
from sampledb.logic.components import get_component_by_uuid, add_component, get_component, Component
from sampledb.logic.fed_logs import get_fed_action_log_entries_for_action, get_fed_instrument_log_entries_for_instrument, get_fed_user_log_entries_for_user, get_fed_location_log_entries_for_location, get_fed_location_type_log_entries_for_location_type, get_fed_comment_log_entries_for_comment, get_fed_object_location_assignment_log_entries_for_assignment, get_fed_file_log_entries_for_file, get_fed_action_type_log_entries_for_action_type, get_fed_object_log_entries_for_object
from sampledb.logic.federation.action_types import parse_action_type, shared_action_type_preprocessor, parse_import_action_type
from sampledb.logic.federation.actions import parse_action, shared_action_preprocessor, parse_import_action
from sampledb.logic.federation.comments import parse_import_comment
from sampledb.logic.federation.files import parse_import_file
from sampledb.logic.federation.instruments import parse_instrument, shared_instrument_preprocessor,  parse_import_instrument
from sampledb.logic.federation.location_types import parse_import_location_type
from sampledb.logic.federation.locations import parse_location, shared_location_preprocessor, locations_check_for_cyclic_dependencies, parse_import_location
from sampledb.logic.federation.markdown_images import parse_import_markdown_image
from sampledb.logic.federation.object_location_assignments import parse_import_object_location_assignment
from sampledb.logic.federation.objects import shared_object_preprocessor, parse_import_object
from sampledb.logic.federation.users import parse_user, shared_user_preprocessor, parse_import_user
from sampledb.logic.federation.update import update_shares
from sampledb.logic.files import get_file, create_url_file, get_files_for_object
from sampledb.logic.groups import create_group
from sampledb.logic.instrument_translations import get_instrument_translations_for_instrument, set_instrument_translation
from sampledb.logic.instruments import get_instrument
from sampledb.logic.languages import get_language, get_language_by_lang_code
from sampledb.logic.locations import get_location, get_fed_object_location_assignment, create_location, get_object_location_assignments, get_location_type
from sampledb.logic.object_permissions import get_object_permissions_for_users, get_object_permissions_for_groups, get_object_permissions_for_projects
from sampledb.logic.objects import create_object, get_fed_object, get_objects, get_object, get_object_versions, insert_fed_object_version
from sampledb.logic.projects import create_project
from sampledb.logic.tags import get_tags
from sampledb.logic.users import get_user
from sampledb.models import User, UserType, Action, ActionType, Comment, ObjectLocationAssignment, File, UserFederationAlias, Instrument, Location, InstrumentTranslation, ActionTranslation, ActionTypeTranslation, Permissions, MarkdownImage
from sampledb.models.fed_logs import FedActionLogEntryType, FedInstrumentLogEntryType, FedInstrumentLogEntry, FedActionLogEntry, FedUserLogEntryType, FedUserLogEntry, FedLocationLogEntry, FedLocationLogEntryType, FedLocationTypeLogEntry, FedLocationTypeLogEntryType, FedCommentLogEntry, FedCommentLogEntryType, FedObjectLocationAssignmentLogEntry, FedObjectLocationAssignmentLogEntryType, FedFileLogEntry, FedFileLogEntryType, FedActionTypeLogEntryType, FedActionTypeLogEntry, FedObjectLogEntry, FedObjectLogEntryType
from tests.logic.schemas.test_validate_schema import wrap_into_basic_schema

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
UUID_2 = '1e59c517-bd11-4390-aeb4-971f20b06612'

POLICY: typing.Dict[typing.Any, typing.Any] = {'access': {'data': True, 'action': True, 'users': True, 'files': True, 'comments': True, 'object_location_assignments': True}, 'permissions': {'users': {'1': 'read', '2': 'grant'}, 'groups': {'4': 'read', '5': 'grant'}, 'projects': {'1': 'read', '3': 'grant'}}}
OBJECT_DATA: typing.Dict[typing.Any, typing.Any] = {'object_id': 1, 'versions': [{'version_id': 0, 'data': {'name': {'_type': 'text', 'text': 'Example'}}, 'schema': {'title': 'Example Action', 'type': 'object', 'properties': {'name': {'title': 'Example Attribute', 'type': 'text'}}, 'required': ['name']}, 'user': {'user_id': 3, 'component_uuid': UUID_1}, 'utc_datetime': '2021-05-03 05:04:54.514236'}], 'action': {'action_id': 2, 'component_uuid': UUID_1}, 'policy': POLICY}
ARRAY_SCHEMA: typing.Dict[typing.Any, typing.Any] = {"title": "", "type": "object", "properties": {"name": {"title": "Name", "type": "text"}, "array": {"title": "Array", "type": "array", "items": {"title": "Subarray", "type": "array", "items": {"type": "text", "title": "Text"}}}}, "required": ["name"]}
ARRAY_DATA: typing.Dict[typing.Any, typing.Any] = {"name": {"text": {"en": ""}, "_type": "text"}, "array": [[{"text": {"en": "Entry 1.1"}, "_type": "text"}, {"text": {"en": "Entry 1.2"}, "_type": "text"}, {"text": {"en": "Entry 1.3"}, "_type": "text"}], [{"text": {"en": "Entry 2.1"}, "_type": "text"}, {"text": {"en": "Entry 2.2"}, "_type": "text"}], [{"text": {"en": "Entry 3.1"}, "_type": "text"}]]}
ARRAY_OBJECT_SCHEMA: typing.Dict[typing.Any, typing.Any] = {"title": "", "type": "object", "properties": {"name": {"title": "Name", "type": "text"}, "object": {"title": "Object", "type": "object", "properties": {"object_name": {"title": "Name", "type": "text"}, "text_array": {"type": "array", "title": "Text Array", "items": {"type": "text", "title": "Text"}}, "array": {"type": "array", "title": "Object Array", "items": {"type": "object", "title": "Object", "properties": {"subobject_name": {"title": "Name", "type": "text"}}}}}}}, "required": ["name"]}
ARRAY_OBJECT_DATA: typing.Dict[typing.Any, typing.Any] = {"name": {"text": {"en": "Name"}, "_type": "text"}, "object": {"array": [{"subobject_name": {"text": {"en": "Subobject Name"}, "_type": "text"}}], "text_array": [{"text": {"en": "Text 1"}, "_type": "text"}, {"text": {"en": "Text 2"}, "_type": "text"}], "object_name": {"text": {"en": "Object Name"}, "_type": "text"}}}
ACTION_DATA: typing.Dict[typing.Any, typing.Any] = {'action_id': 2, 'component_uuid': UUID_1, 'action_type': {'action_type_id': -96, 'component_uuid': UUID_1}, 'description_is_markdown': False, 'short_description_is_markdown': False, 'instrument': {'instrument_id': 4, 'component_uuid': UUID_1}, 'schema': {'title': 'Example Action', 'type': 'object', 'properties': {'name': {'title': 'Example Attribute', 'type': 'text'}}, 'required': ['name']}, 'user': {'user_id': 3, 'component_uuid': UUID_1}, 'is_hidden': False, 'translations': {'en': {'name': 'Example Action', 'description': 'Test Action', 'short_description': ''}, 'de': {'name': 'Beispielaktion', 'description': 'Aktion für Tests', 'short_description': ''}}}
ACTION_TYPE_DATA: typing.Dict[typing.Any, typing.Any] = {'action_type_id': 1, 'component_uuid': UUID_1, 'admin_only': False, 'enable_labels': True, 'enable_files': True, 'enable_locations': True, 'enable_publications': False, 'enable_comments': True, 'enable_activity_log': True, 'enable_related_objects': True, 'enable_project_link': False, 'translations': {'en': {'name': 'Action Type', 'description': 'Description', 'object_name': 'Action Object', 'object_name_plural': 'Action Objects', 'view_text': 'Show Action Objects', 'perform_text': 'Perform Action Type Action'}, 'de': {'name': 'Aktionstyp', 'description': 'Beschreibung', 'object_name': 'Aktionsobjekt', 'object_name_plural': 'Aktionsobjekte', 'view_text': 'Zeige Aktionsobjekte', 'perform_text': 'Führe Aktionstyp-Aktion aus'}}}
INSTRUMENT_DATA: typing.Dict[typing.Any, typing.Any] = {'instrument_id': 4, 'component_uuid': UUID_1, 'description_is_markdown': False, 'short_description_is_markdown': False, 'notes_is_markdown': False, 'is_hidden': False, 'translations': {'en': {'name': 'Example Instrument', 'description': 'Test instrument description', 'short_description': 'Test instrument short description', 'notes': 'Notes'}, 'de': {'name': 'Beispielinstrument', 'description': 'Beschreibung des Testinstrumentes', 'short_description': 'Kurzbeschreibung eines Beispielinstrumentes', 'notes': 'Notizen'}}}
USER_DATA: typing.Dict[typing.Any, typing.Any] = {'user_id': 3, 'component_uuid': UUID_1, 'name': 'Example User', 'email': 'example@example.com', 'orcid': '0000-0002-1825-0097', 'affiliation': 'FZJ', 'role': 'Role', 'extra_fields': {'website': 'example.com'}}
LOCATION_DATA: typing.Dict[typing.Any, typing.Any] = {'location_id': 2, 'component_uuid': UUID_1, 'name': {'en': 'Location', 'de': 'Ort'}, 'description': {'en': 'Example description', 'de': 'Beispielbeschreibung'}, 'parent_location': {'location_id': 1, 'component_uuid': UUID_1}, 'location_type': {'location_type_id': -99, 'component_uuid': UUID_1}, 'responsible_users': [{'user_id': 3, 'component_uuid': UUID_1}]}
LOCATION_TYPE_DATA: typing.Dict[typing.Any, typing.Any] = {'location_type_id': 5,  'component_uuid': UUID_1, 'name': {'en': 'Location Type'}, 'location_name_singular': {'en': 'Location'}, 'location_name_plural': {'en': 'Locations'}, 'admin_only': False, 'enable_parent_location': True, 'enable_sub_locations': True, 'enable_object_assignments': True, 'enable_responsible_users': True, 'show_location_log': True}
COMMENT_DATA: typing.Dict[typing.Any, typing.Any] = {'comment_id': 1, 'component_uuid': UUID_1, 'user': {'user_id': 1, 'component_uuid': UUID_1}, 'content': 'Comment Text', 'utc_datetime': '2021-05-03 05:04:54.729462'}
FILE_DATA: typing.Dict[typing.Any, typing.Any] = {'file_id': 1, 'component_uuid': UUID_1, 'user': {'user_id': 3, 'component_uuid': UUID_1}, 'data': {"storage": "url", "url": "https://example.com/file"}, 'utc_datetime': '2021-05-03 05:04:54.516344'}
OBJECT_LOCATION_ASSIGNMENT_DATA: typing.Dict[typing.Any, typing.Any] = {'id': 1, 'component_uuid': UUID_1, 'user': {'user_id': 1, 'component_uuid': UUID_1}, 'responsible_user': {'user_id': 1, 'component_uuid': UUID_1}, 'location': {'location_id': 1, 'component_uuid': UUID_1}, 'description': {'en': 'Object location assignment description'}, 'confirmed': False, 'utc_datetime': '2021-05-03 05:04:54.123450'}
COMPLEX_ACTION_SCHEMA: typing.Dict[typing.Any, typing.Any] = {"title": "Action", "type": "object", "properties": {"name": {"title": "Name", "type": "text"}, "multiline_text": {"title": "Multiline Text", "type": "text", "multiline": True, "placeholder": "Multiline Text"}, "markdown_text": {"title": "Markdown Text", "type": "text", "markdown": True, "default": "**Text**"}, "choice": {"title": "Choice", "type": "text", "choices": ["Option 1", "Option 2", "Option 3", "Option 4"]}, "quantity": {"title": "Quantity", "note": "Quantity", "type": "quantity", "units": "1"}, "bool": {"title": "Boolean", "type": "bool", "default": True}, "datetime": {"title": "Datetime", "type": "datetime"}, "sample": {"title": "Sample", "type": "sample"}, "measurement": {"title": "Measurement", "type": "measurement"}, "user": {"title": "User", "type": "user"}, "object": {"title": "Object", "type": "object_reference"}, "graphic": {"title": "Graphic", "type": "plotly_chart"}, "tags": {"type": "tags", "title": "Tags"}, "hazards": {"type": "hazards", "title": "GHS Hazards"}}, "required": ["name", "markdown_text", "tags", "hazards"], "propertyOrder": ["name", "multiline_text", "markdown_text", "choice", "quantity", "bool", "datetime", "sample", "measurement", "user", "object", "graphic", "tags", "hazards"]}
COMPLEX_OBJECT_DATA: typing.Dict[typing.Any, typing.Any] = {"bool": {"_type": "bool", "value": True}, "name": {"text": {"en": "Object"}, "_type": "text"}, "tags": {"tags": ["object", "result"], "_type": "tags"}, "user": {"_type": "user", "user_id": 3, "component_uuid": UUID_1}, "choice": {"text": "Option 3", "_type": "text"}, "object": {"_type": "object_reference", "object_id": 12, "component_uuid": UUID_1}, "sample": {"_type": "sample", "object_id": 8, "component_uuid": UUID_1}, "graphic": {"_type": "plotly_chart", "plotly": {"data": [{"x": ["0.000", "1.000"], "y": ["0.000", "1.000"], "type": "scatter"}], "layout": {"width": 800, "xaxis": {"type": "linear", "range": [0, 1]}, "yaxis": {"type": "linear", "range": [0.0, 1.0]}}}}, "hazards": {"_type": "hazards", "hazards": [3, 7, 9]}, "datetime": {"_type": "datetime", "utc_datetime": "2021-07-08 13:03:52"}, "quantity": {"_type": "quantity", "units": "1", "magnitude": 12, "dimensionality": "dimensionless", "magnitude_in_base_units": 12}, "measurement": {"_type": "measurement", "object_id": 6, "component_uuid": UUID_1}, "markdown_text": {"text": {"en": "**Text**"}, "_type": "text", "is_markdown": True}, "multiline_text": {"text": {"en": "Object\r\nTest"}, "_type": "text"}}
REFERENCES_TABLE_LIST_SCHEMA: typing.Dict[typing.Any, typing.Any] = {'title': 'Table and List', 'type': 'object', 'properties': {'name': {'title': 'Object Name', 'type': 'text'}, 'user1': {'title': 'User 1', 'type': 'user'}, 'object1': {'title': 'Object 1', 'type': 'object_reference'}, 'user2': {'title': 'User 2', 'type': 'user'}, 'object2': {'title': 'Object 2', 'type': 'object_reference'}, 'user3': {'title': 'User 3', 'type': 'user'}, 'object3': {'title': 'Object 3', 'type': 'object_reference'}, 'user4': {'title': 'User 4', 'type': 'user'}, 'object4': {'title': 'Object 4', 'type': 'object_reference'}, 'userlist': {'title': 'User List', 'type': 'array', 'style': 'list', 'items': {'title': 'User', 'type': 'user'}}, 'objectlist': {'title': 'Object List', 'type': 'array', 'style': 'list', 'items': {'title': 'Object', 'type': 'object_reference'}}, 'usertable': {'title': 'User Table', 'type': 'array', 'style': 'table', 'items': {'type': 'array', 'title': 'User Row', 'items': {'title': 'User', 'type': 'user'}}}, 'objecttable': {'title': 'Object Table', 'type': 'array', 'style': 'table', 'items': {'type': 'array', 'title': 'Object Row', 'items': {'title': 'Object', 'type': 'object_reference'}}}}, 'propertyOrder': ['name', 'user1', 'object1', 'user2', 'object2', 'user3', 'object3', 'user4', 'object4', 'userlist', 'objectlist', 'usertable', 'objecttable'], 'required': ['name']}
REFERENCES_TABLE_LIST_DATA_FRAME: typing.Dict[typing.Any, typing.Any] = {'name': {'text': {'en': 'Test Object'}, '_type': 'text'}, 'user1': {'_type': 'user'}, 'user2': {'_type': 'user'}, 'user3': {'_type': 'user'}, 'user4': {'_type': 'user'}, 'object1': {'_type': 'object_reference'}, 'object2': {'_type': 'object_reference'}, 'object3': {'_type': 'object_reference'}, 'object4': {'_type': 'object_reference'}, 'userlist': [{'_type': 'user'}, {'_type': 'user'}, {'_type': 'user'}, {'_type': 'user'}], 'objectlist': [{'_type': 'object_reference'}, {'_type': 'object_reference'}, {'_type': 'object_reference'}, {'_type': 'object_reference'}], 'usertable': [[{'_type': 'user', 'user_id': 6}, {'_type': 'user', 'user_id': 3, 'component_uuid': '7c3db1e8-15ba-4d86-885f-792e054d9c73'}], [{'_type': 'user', 'user_id': 5}, {'_type': 'user', 'user_id': 3, 'component_uuid': '208363a4-941b-4071-b6f1-f7803bcbe923'}]], 'objecttable': [[{'_type': 'object_reference'}, {'_type': 'object_reference'}], [{'_type': 'object_reference'}, {'_type': 'object_reference'}]]}


@pytest.fixture
def user():
    user = User(name='User', email='example@example.com', affiliation='FZJ', type=UserType.PERSON)
    db.session.add(user)
    db.session.commit()
    # force attribute refresh
    assert user.id is not None
    return user


@pytest.fixture
def fed_user(foreign_component):
    user = User(name='Fed User', email='example@example.com', affiliation='FZJ', type=UserType.FEDERATION_USER, fed_id=1, component_id=foreign_component.id)
    db.session.add(user)
    db.session.commit()
    # force attribute refresh
    assert user.id is not None
    return user


@pytest.fixture
def simple_action():
    action = Action(
        action_type_id=ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        },
        instrument_id=None
    )
    db.session.add(action)
    db.session.commit()
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def measurement_action():
    action = Action(
        action_type_id=ActionType.MEASUREMENT,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        },
        instrument_id=None
    )
    db.session.add(action)
    db.session.commit()
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def instrument():
    instrument = Instrument()
    db.session.add(instrument)
    db.session.commit()

    assert instrument.id is not None

    set_instrument_translation(
        language_id=get_language_by_lang_code('en').id,
        instrument_id=instrument.id,
        name='Action',
        description='Action description',
        short_description='Action short description',
        notes='Notes'
    )

    set_instrument_translation(
        language_id=get_language_by_lang_code('de').id,
        instrument_id=instrument.id,
        name='Instrument',
        description='Beschreibung des Instrumentes',
        short_description='Kurzbeschreibung des Instrumentes',
        notes='Notizen'
    )

    return instrument


@pytest.fixture
def action(instrument, user):
    action = Action(
        action_type_id=ActionType.SAMPLE_CREATION,
        user_id=user.id,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        },
        instrument_id=instrument.id
    )
    db.session.add(action)
    db.session.commit()

    assert action.id is not None

    set_action_translation(
        language_id=get_language_by_lang_code('en').id,
        action_id=action.id,
        name='Action',
        description='Action description',
        short_description='Action short description'
    )

    set_action_translation(
        language_id=get_language_by_lang_code('de').id,
        action_id=action.id,
        name='Aktion',
        description='Beschreibung der Aktion',
        short_description='Kurzbeschreibung der Aktion'
    )

    return action


@pytest.fixture
def simple_object(user, simple_action):
    object = create_object(user_id=user.id, action_id=simple_action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    return object


@pytest.fixture
def markdown_action():
    action = Action(
        action_type_id=ActionType.SAMPLE_CREATION,
        schema={
            "type": "object",
            "title": "Example Object",
            "required": [
                "name"
            ],
            "properties": {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'comment': {
                    'title': 'Comment',
                    'type': 'text',
                    'markdown': True
                },
                'markdown': {
                    'title': 'Markdown Text',
                    'type': 'text',
                    'markdown': True,
                    'languages': ['en', 'de']
                }
            }
        },
        instrument_id=None
    )
    db.session.add(action)
    db.session.commit()
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def markdown_images(user):
    markdown_image_1 = MarkdownImage(64 * 'a' + '.png', b'1', user.id, datetime.datetime.utcnow(), True)
    markdown_image_2 = MarkdownImage(64 * 'b' + '.png', b'2', user.id, datetime.datetime.utcnow(), True)
    markdown_image_3 = MarkdownImage(64 * 'c' + '.png', b'3', user.id, datetime.datetime.utcnow(), True)

    db.session.add(markdown_image_1)
    db.session.add(markdown_image_2)
    db.session.add(markdown_image_3)
    db.session.commit()

    return markdown_image_1, markdown_image_2, markdown_image_3


@pytest.fixture
def markdown_object(user, markdown_action, markdown_images):
    md0, md1, md2 = markdown_images
    object = create_object(user_id=user.id, action_id=markdown_action.id, data={
        'name': {
            'text': 'name',
            '_type': 'text'
        },
        'comment': {
            'text': 'Image 1: ![image](/markdown_images/' + md0.file_name + ')',
            '_type': 'text',
            'is_markdown': True
        },
        'markdown': {
            'text': {
                'en': 'Image 2: ![image](/markdown_images/' + md1.file_name + ')',
                'de': 'Bild 2: ![image](/markdown_images/' + md2.file_name + ')'
            },
            '_type': 'text',
            'is_markdown': True
        }
    })

    return object


@pytest.fixture
def complex_action(instrument, user):
    action_type = create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        enable_labels=True,
        enable_comments=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_related_objects=True,
        enable_activity_log=True,
        enable_project_link=True,
        disable_create_objects=False,
        is_template=False
    )
    action = create_action(
        action_type_id=action_type.id,
        schema=COMPLEX_ACTION_SCHEMA,
        instrument_id=instrument.id,
        user_id=user.id,
        description_is_markdown=True,
        short_description_is_markdown=False
    )

    return action


@pytest.fixture
def ref_objects(user, simple_action, measurement_action):
    ref_object = create_object(
        user_id=user.id,
        action_id=simple_action.id,
        data={
            'name': {
                '_type': 'text',
                'text': 'Name'
            }
        }
    )
    ref_sample = create_object(
        user_id=user.id,
        action_id=simple_action.id,
        data={
            'name': {
                '_type': 'text',
                'text': 'Name'
            }
        }
    )
    ref_measurement = create_object(
        user_id=user.id,
        action_id=measurement_action.id,
        data={
            'name': {
                '_type': 'text',
                'text': 'Name'
            }
        }
    )

    return ref_object, ref_sample, ref_measurement


@pytest.fixture
def complex_object(complex_action, users, ref_objects):
    ref_object, ref_sample, ref_measurement = ref_objects
    user1, user2, user3, user4, user5, user6, user7 = users
    object_data = deepcopy(COMPLEX_OBJECT_DATA)
    object_data['object']['object_id'] = ref_object.object_id
    object_data['sample']['object_id'] = ref_sample.object_id
    object_data['measurement']['object_id'] = ref_measurement.object_id
    object_data['user']['user_id'] = user1.id
    object = create_object(
        user_id=user2.id,
        action_id=complex_action.id,
        data=object_data,
    )
    create_comment(object_id=object.id, user_id=user3.id, content='Comment')
    create_url_file(object_id=object.id, user_id=user4.id, url='http://example.com/file')
    location = create_location(name={'en': 'Location'}, description={'en': 'Description'}, parent_location_id=None, user_id=user5.id, type_id=logic.locations.LocationType.LOCATION)
    ola = ObjectLocationAssignment(object_id=object.object_id, location_id=location.id, responsible_user_id=user6.id, user_id=user7.id, description={'en': 'Assignment description'})
    db.session.add(ola)
    db.session.commit()

    return object


@pytest.fixture
def array_object(user):
    action = create_action(
        action_type_id=ActionType.SAMPLE_CREATION,
        schema=ARRAY_SCHEMA,
    )
    object = create_object(
        user_id=user.id,
        action_id=action.id,
        data=ARRAY_DATA,
        schema=ARRAY_SCHEMA
    )
    return object


@pytest.fixture
def array_object_object(user):
    action = create_action(
        action_type_id=ActionType.SAMPLE_CREATION,
        schema=ARRAY_OBJECT_SCHEMA,
    )
    object = create_object(
        user_id=user.id,
        action_id=action.id,
        data=ARRAY_OBJECT_DATA,
        schema=ARRAY_OBJECT_SCHEMA
    )
    return object


@pytest.fixture
def users():
    names = ['User ' + str(i) for i in range(1, 8)]
    users = [User(name=name, email="example@example.com", type=UserType.PERSON) for name in names]
    for user in users:
        db.session.add(user)
        db.session.commit()
        # force attribute refresh
        assert user.id is not None

    return users


@pytest.fixture
def groups(user):
    names = ['Group 1', 'Group 2', 'Group 3']
    groups = [create_group(name, '', user.id) for name in names]

    return groups


@pytest.fixture
def projects(user):
    names = ['Project 1', 'Project 2', 'Project 3']
    projects = [create_project(name, '', user.id) for name in names]

    return projects


@pytest.fixture
def component():
    component = add_component(address=None, uuid=UUID_1, name='Example component', description='')
    return component


@pytest.fixture
def foreign_component():
    component = add_component(address=None, uuid='bbadfbe8-7950-4da8-80f1-136be4fd3b8d', name='Example foreign component', description='')
    return component


@pytest.fixture
def user_alias_setup(user, component):
    user_alias = UserFederationAlias(user_id=user.id, component_id=component.id, name='Alias', email='alias@example.com', affiliation='FZJ GmbH')

    db.session.add(user_alias)
    db.session.commit()
    return user, component, user_alias


@pytest.fixture
def locations():
    data = [({'en': 'Location ' + str(i), 'de': 'Ort ' + str(i)}, {'en': 'Text describing location ' + str(i), 'de': 'Beschreibungstext für Ort ' + str(i)}) for i in range(1, 4)]
    locations = [Location(name=name, description=description, type_id=logic.locations.LocationType.LOCATION) for name, description in data]
    for location in locations:
        db.session.add(location)
    db.session.commit()
    locations[1].parent_location_id = locations[0].id
    db.session.add(locations[1])
    db.session.commit()
    return locations


@pytest.fixture
def object_history():
    object_data_1 = deepcopy(OBJECT_DATA)
    object_data_1['versions'][0]['version_id'] = 0
    object_data_1['versions'][0]['data']['name']['text'] = 'Example Version 0'
    object_data_1['versions'][0]['utc_datetime'] = '2021-05-03 05:04:54.614336'
    object_data_2 = deepcopy(OBJECT_DATA)
    object_data_2['versions'][0]['version_id'] = 1
    object_data_2['versions'][0]['data']['name']['text'] = 'Example Version 1'
    object_data_2['versions'][0]['utc_datetime'] = '2021-05-07 16:40:12.191564'
    object_data_3 = deepcopy(OBJECT_DATA)
    object_data_3['versions'][0]['version_id'] = 2
    object_data_3['versions'][0]['data']['name']['text'] = 'Example Version 2'
    object_data_3['versions'][0]['utc_datetime'] = '2021-06-12 12:30:14.735518'
    return object_data_1, object_data_2, object_data_3


def _check_object(object_data, comp):
    for version in object_data.get('versions'):
        object = get_fed_object(object_data.get('object_id'), comp.id, version.get('version_id'))
        assert object is not None
        assert object.fed_object_id == object_data.get('object_id')
        assert object.fed_version_id == version.get('version_id')
        assert object.data == version.get('data')
        assert object.schema == version.get('schema')
        if version.get('utc_datetime') is not None:
            assert object.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') == version.get('utc_datetime')
        assert object.component_id == comp.id

        if version.get('user') is not None:
            user_component = get_component_by_uuid(version['user'].get('component_uuid'))
            assert user_component is not None
            user = get_user(version['user'].get('user_id'), user_component.id)
            assert user is not None
            assert object.user_id == user.id

    if object_data.get('action') is not None:
        action_component = get_component_by_uuid(object_data['action'].get('component_uuid'))
        assert action_component is not None
        action = get_action(object_data['action'].get('action_id'), action_component.id)
        assert action is not None
        assert object.action_id == action.id


def _check_action(action_data):
    component = get_component_by_uuid(action_data.get('component_uuid'))
    assert component is not None

    action = get_action(action_data.get('action_id'), component.id)
    assert action is not None
    assert action.fed_id == action_data.get('action_id')
    assert action.component_id == component.id
    assert action.component == Component.from_database(component)

    assert action.description_is_markdown == action_data.get('description_is_markdown')
    assert action.short_description_is_markdown == action_data.get('short_description_is_markdown')
    assert action.schema == action_data.get('schema')
    assert action.is_hidden == action_data.get('is_hidden')

    if action_data.get('action_type') is not None:
        action_type_component = get_component_by_uuid(action_data['action_type'].get('component_uuid'))
        assert action_type_component is not None
        action_type = get_action_type(action_data['action_type'].get('action_type_id'), action_type_component.id)
        assert action_type is not None
        assert action.type_id == action_type.id

    if action_data.get('instrument') is not None:
        instrument_component = get_component_by_uuid(action_data['instrument'].get('component_uuid'))
        assert instrument_component is not None
        instrument = get_instrument(action_data['instrument'].get('instrument_id'), instrument_component.id)
        assert instrument is not None
        assert action.instrument_id == instrument.id

    if action_data.get('user') is not None:
        user_component = get_component_by_uuid(action_data['user'].get('component_uuid'))
        assert user_component is not None
        user = get_user(action_data['user'].get('user_id'), user_component.id)
        assert user is not None
        assert action.user_id == user.id

    translations = get_action_translations_for_action(action.id)
    if action_data.get('translations') is not None:
        assert len(translations) == len(action_data.get('translations'))
        for translation in translations:
            language = get_language(translation.language_id)
            assert translation.name == action_data['translations'][language.lang_code]['name']
            assert translation.description == action_data['translations'][language.lang_code]['description']
            assert translation.short_description == action_data['translations'][language.lang_code]['short_description']
    else:
        assert len(translations) == 0


def _check_action_type(action_type_data):
    component = get_component_by_uuid(action_type_data.get('component_uuid'))
    assert component is not None

    action_type = get_action_type(action_type_data.get('action_type_id'), component.id)
    assert action_type is not None
    assert action_type.fed_id == action_type_data.get('action_type_id')
    assert action_type.admin_only == action_type_data.get('admin_only')
    assert action_type.enable_labels == action_type_data.get('enable_labels')
    assert action_type.enable_files == action_type_data.get('enable_files')
    assert action_type.enable_locations == action_type_data.get('enable_locations')
    assert action_type.enable_publications == action_type_data.get('enable_publications')
    assert action_type.enable_comments == action_type_data.get('enable_comments')
    assert action_type.enable_activity_log == action_type_data.get('enable_activity_log')
    assert action_type.enable_related_objects == action_type_data.get('enable_related_objects')
    assert action_type.enable_project_link == action_type_data.get('enable_project_link')

    translations = get_action_type_translations_for_action_type(action_type.id)
    if action_type_data.get('translations') is not None:
        assert len(translations) == len(action_type_data.get('translations'))
        for translation in translations:
            language = get_language(translation.language_id)
            assert translation.name == action_type_data['translations'][language.lang_code]['name']
            assert translation.description == action_type_data['translations'][language.lang_code]['description']
            assert translation.object_name == action_type_data['translations'][language.lang_code]['object_name']
            assert translation.object_name_plural == action_type_data['translations'][language.lang_code]['object_name_plural']
            assert translation.view_text == action_type_data['translations'][language.lang_code]['view_text']
            assert translation.perform_text == action_type_data['translations'][language.lang_code]['perform_text']
    else:
        assert len(translations) == 0


def _check_instrument(instrument_data):
    component = get_component_by_uuid(instrument_data.get('component_uuid'))
    assert component is not None

    instrument = get_instrument(instrument_data.get('instrument_id'), component.id)
    assert instrument is not None
    assert instrument.fed_id == instrument_data.get('instrument_id')
    assert instrument.component_id == component.id
    assert instrument.component == Component.from_database(component)

    assert instrument.description_is_markdown == instrument_data.get('description_is_markdown')
    assert instrument.short_description_is_markdown == instrument_data.get('short_description_is_markdown')
    assert instrument.notes_is_markdown == instrument_data.get('notes_is_markdown')
    assert instrument.is_hidden == instrument_data.get('is_hidden')

    assert instrument.users_can_view_log_entries is False
    assert instrument.users_can_create_log_entries is False
    assert instrument.create_log_entry_default is False

    translations = get_instrument_translations_for_instrument(instrument.id)
    if instrument_data.get('translations') is not None:
        assert len(translations) == len(instrument_data.get('translations'))
        for translation in translations:
            language = get_language(translation.language_id)
            assert translation.name == instrument_data['translations'][language.lang_code]['name']
            assert translation.description == instrument_data['translations'][language.lang_code]['description']
            assert translation.short_description == instrument_data['translations'][language.lang_code]['short_description']
            assert translation.notes == instrument_data['translations'][language.lang_code]['notes']
    else:
        assert len(translations) == 0


def _check_user(user_data):
    component = get_component_by_uuid(user_data.get('component_uuid'))
    assert component is not None

    user = get_user(user_data.get('user_id'), component.id)
    assert user is not None
    assert user.fed_id == user_data.get('user_id')
    assert user.component_id == component.id
    assert user.component == get_component(component.id)

    assert user.name == user_data.get('name')
    assert user.email == user_data.get('email')
    assert user.orcid == user_data.get('orcid')
    assert user.affiliation == user_data.get('affiliation')
    assert user.role == user_data.get('role')
    if user_data.get('extra_fields') is not None:
        assert user.extra_fields == user_data.get('extra_fields')
    else:
        assert user.extra_fields == {}


def _check_location_type(location_type_data):
    component = get_component_by_uuid(location_type_data.get('component_uuid'))
    assert component is not None

    location_type = get_location_type(location_type_data.get('location_type_id'), component.id)
    assert location_type is not None
    assert location_type.fed_id == location_type_data.get('location_type_id')
    assert location_type.component.id == component.id

    assert location_type.name == location_type_data.get('name')
    assert location_type.location_name_singular == location_type_data.get('location_name_singular')
    assert location_type.location_name_plural == location_type_data.get('location_name_plural')
    assert location_type.admin_only == location_type_data.get('admin_only')
    assert location_type.enable_parent_location == location_type_data.get('enable_parent_location')
    assert location_type.enable_sub_locations == location_type_data.get('enable_sub_locations')
    assert location_type.enable_object_assignments == location_type_data.get('enable_object_assignments')
    assert location_type.enable_responsible_users == location_type_data.get('enable_responsible_users')


def _check_location(location_data):
    component = get_component_by_uuid(location_data.get('component_uuid'))
    assert component is not None

    location = get_location(location_data.get('location_id'), component.id)
    assert location is not None
    assert location.fed_id == location_data.get('location_id')
    assert location.component.id == component.id

    assert location.name == location_data.get('name')
    assert location.description == location_data.get('description')
    location_type_data = location_data.get('location_type')
    if location_type_data is None:
        assert location.type_id == logic.locations.LocationType.LOCATION
    else:
        assert location.type.fed_id == location_type_data.get('location_type_id')
        assert location.type.component.uuid == location_type_data.get('component_uuid')

    if location_data.get('parent_location') is not None:
        parent_location_component = get_component_by_uuid(location_data['parent_location'].get('component_uuid'))
        assert parent_location_component is not None
        parent_location = get_location(location_data['parent_location'].get('location_id'), parent_location_component.id)
        assert parent_location is not None
        assert location.parent_location_id == parent_location.id

    if location_data.get('responsible_users') is not None:
        for responsible_user_data in location_data['responsible_users']:
            responsible_user_component = get_component_by_uuid(responsible_user_data.get('component_uuid'))
            assert responsible_user_component is not None
            responsible_user = get_user(responsible_user_data.get('user_id'), responsible_user_component.id)
            assert responsible_user is not None


def _check_comment(comment_data):
    component = get_component_by_uuid(comment_data.get('component_uuid'))
    assert component is not None

    comment = get_comment(comment_data.get('comment_id'), component.id)
    assert comment is not None
    assert comment.fed_id == comment_data.get('comment_id')
    assert comment.component_id == component.id
    assert comment.component == component

    assert comment.content == comment_data.get('content')
    assert comment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') == comment_data.get('utc_datetime')

    if comment_data.get('user') is not None:
        user_component = get_component_by_uuid(comment_data['user'].get('component_uuid'))
        assert user_component is not None
        user = get_user(comment_data['user'].get('user_id'), user_component.id)
        assert user is not None
        assert comment.user_id == user.id


def _check_file(file_data, object_id):
    component = get_component_by_uuid(file_data.get('component_uuid'))
    assert component is not None

    file = get_file(file_data.get('file_id'), object_id, component.id)
    assert file is not None
    assert file.fed_id == file_data.get('file_id')
    assert file.component_id == component.id

    assert file.data == file_data.get('data')
    assert file.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') == file_data.get('utc_datetime')

    if file_data.get('user') is not None:
        user_component = get_component_by_uuid(file_data['user'].get('component_uuid'))
        assert user_component is not None
        user = get_user(file_data['user'].get('user_id'), user_component.id)
        assert user is not None
        assert file.user_id == user.id


def _check_object_location_assignment(assignment_data):
    component = get_component_by_uuid(assignment_data.get('component_uuid'))
    assert component is not None

    assignment = get_fed_object_location_assignment(assignment_data.get('id'), component.id)
    assignment = logic.locations.ObjectLocationAssignment.from_database(assignment)
    assert assignment is not None
    assert assignment.fed_id == assignment_data.get('id')
    assert assignment.component_id == component.id
    assert assignment.component == component
    assert assignment.description == assignment_data.get('description')
    assert assignment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') == assignment_data.get('utc_datetime')

    if assignment_data.get('user') is not None:
        user_component = get_component_by_uuid(assignment_data['user'].get('component_uuid'))
        assert user_component is not None
        user = get_user(assignment_data['user'].get('user_id'), user_component.id)
        assert user is not None
        assert assignment.user_id == user.id

    if assignment_data.get('responsible_user') is not None:
        responsible_user_component = get_component_by_uuid(assignment_data['responsible_user'].get('component_uuid'))
        assert responsible_user_component is not None
        responsible_user = get_user(assignment_data['responsible_user'].get('user_id'), responsible_user_component.id)
        assert responsible_user is not None
        assert assignment.responsible_user_id == responsible_user.id

    if assignment_data.get('location') is not None:
        location_component = get_component_by_uuid(assignment_data['location'].get('component_uuid'))
        assert location_component is not None
        location = get_location(assignment_data['location'].get('location_id'), location_component.id)
        assert location is not None
        assert assignment.location_id == location.id


def _invalid_component_uuid_test(data, parse_function):
    test_data = deepcopy(data)
    del test_data['component_uuid']
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data = deepcopy(data)
    test_data['component_uuid'] = '123456'
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data = deepcopy(data)
    test_data['component_uuid'] = 12
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data = deepcopy(data)
    test_data['component_uuid'] = True
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data = deepcopy(data)
    test_data['component_uuid'] = [UUID_1]
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data = deepcopy(data)
    test_data['component_uuid'] = {'uuid': UUID_1}
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)


def _invalid_id_test(data, key, parse_function):
    test_data = deepcopy(data)
    del test_data[key]
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = -1
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = 'seven'
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)


def _invalid_reference_test(data, key, id_key, parse_function, mandatory=False):
    test_data = deepcopy(data)
    test_data[key] = 'string'
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = 12
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = ['id', 12, 'component_uuid', 'uuid']
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = deepcopy(data[key])
    del test_data[key][id_key]
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key][id_key] = -1
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key][id_key] = 'seven'
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key][id_key] = False
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key][id_key] = data[key][id_key]
    del test_data[key]['component_uuid']
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key]['component_uuid'] = '123456'
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key]['component_uuid'] = 12
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key]['component_uuid'] = True
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data['component_uuid'] = [UUID_1]
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key]['component_uuid'] = {'uuid': UUID_1}
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    if mandatory:
        del test_data[key]
        with pytest.raises(errors.InvalidDataExportError):
            parse_function(test_data)


def _invalid_dict_test(data, key, parse_function, mandatory=False):
    test_data = deepcopy(data)
    test_data[key] = ['val1', 2]
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = 123
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = 'dict'
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = True
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    if mandatory:
        del test_data[key]
        with pytest.raises(errors.InvalidDataExportError):
            parse_function(test_data)


def _invalid_schema_test(data, key, parse_function):
    # see tests/logic/schemas/test_validate_schema
    test_data = deepcopy(data)
    test_data[key] = {}
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = wrap_into_basic_schema({
        'title': 'Example'
    })
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = {
        'title': "Basic Schema",
        'type': 'object',
        'properties': {
            'example': {
                'title': "Name",
                'type': 'text'
            }
        },
        'required': ['example']
    }
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = wrap_into_basic_schema({
        'title': "Basic Schema",
        'type': 'object',
        'properties': {
            'name': {
                'title': "Name",
                'type': 'text'
            }
        },
    })
    test_data[key]['required'].clear()
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)
    del test_data[key]['required']
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = wrap_into_basic_schema({
        'type': 'bool'
    })
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = wrap_into_basic_schema({
        'title': 'Example',
        'type': 'invalid'
    })
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = wrap_into_basic_schema({
        'title': 'Example',
        'type': b'bool'
    })
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)


def _invalid_bool_test(data, key, parse_function):
    test_data = deepcopy(data)
    test_data[key] = ['val1', 2]
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = 123
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = 'dict'
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = {'bool': True}
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)


def _invalid_str_test(data, key, parse_function, mandatory=False, allow_empty=True):
    test_data = deepcopy(data)
    test_data[key] = 12
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = {'name': 'name'}
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = ['name', 'description']
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = False
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    if mandatory:
        del test_data[key]
        with pytest.raises(errors.InvalidDataExportError):
            parse_function(test_data)

    if not allow_empty:
        test_data[key] = ''
        with pytest.raises(errors.InvalidDataExportError):
            parse_function(test_data)


def _invalid_translation_str_test(data, lang, key, parse_function):
    test_data = deepcopy(data)
    test_data['translations'][lang][key] = 12
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data['translations'][lang][key] = {'name': 'name'}
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data['translations'][lang][key] = ['name', 'description']
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data['translations'][lang][key] = False
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)


def _invalid_translation_test(data, key, parse_function):
    test_data = deepcopy(data)
    test_data[key] = 12
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = True
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = ['Description', 'Beschreibung']
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = {0: 'Description', 1: 'Beschreibung'}
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = {'en': 1, 'de': 'Beschreibung'}
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = {'en': 'Description', '': 'Beschreibung'}
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)


def _invalid_datetime_test(data, key, parse_function, mandatory=False):
    test_data = deepcopy(data)
    test_data[key] = '2021-05-03 05:04'
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = 700
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = {'hour': 7, 'min': 0}
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    test_data[key] = [7, 0]
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    dt = datetime.datetime.utcnow() + datetime.timedelta(days=2)
    test_data[key] = dt.strftime('%Y-%m-%d %H:%M:%S.%f')
    with pytest.raises(errors.InvalidDataExportError):
        parse_function(test_data)

    if mandatory:
        del test_data[key]
        with pytest.raises(errors.InvalidDataExportError):
            parse_function(test_data)


def test_import_simple_object(component):
    object_data = deepcopy(OBJECT_DATA)
    start_datetime = datetime.datetime.utcnow()
    object = parse_import_object(object_data, component)
    _check_object(object_data, component)

    assert len(get_objects()) == 1

    log_entries = get_fed_object_log_entries_for_object(object.id)
    assert len(FedObjectLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLogEntryType.IMPORT_OBJECT
    assert log_entries[0].component_id == component.id
    assert log_entries[0].object_id == object.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_update_object_version(component):
    old_object_data = deepcopy(OBJECT_DATA)
    start_datetime = datetime.datetime.utcnow()
    old_object = parse_import_object(old_object_data, component)

    object_data = deepcopy(OBJECT_DATA)
    object_data['versions'][0]['data'] = {
        'name': {
            '_type': 'text',
            'text': 'Updated Example'
        }
    }
    object_data['versions'][0]['schema'] = {
        'title': 'Updated Example Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Updated Example Attribute',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    object_data['action'] = {
        'action_id': 7,
        'component_uuid': UUID_1
    }
    object_data['versions'][0]['user'] = {
        'user_id': 5,
        'component_uuid': UUID_1
    }
    object_data['versions'][0]['utc_datetime'] = '2021-06-03 01:04:54.539351'
    object = parse_import_object(object_data, component)
    _check_object(object_data, component)

    assert old_object.id == object.id
    assert len(get_objects()) == 1

    log_entries = get_fed_object_log_entries_for_object(object.id)
    assert len(FedObjectLogEntry.query.all()) == 2
    assert len(log_entries) == 2
    assert log_entries[1].type == FedObjectLogEntryType.IMPORT_OBJECT
    assert log_entries[1].component_id == object.component_id
    assert log_entries[1].object_id == object.id
    assert log_entries[1].utc_datetime >= start_datetime
    assert log_entries[1].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].type == FedObjectLogEntryType.UPDATE_OBJECT
    assert log_entries[0].component_id == object.component_id
    assert log_entries[0].object_id == object.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].utc_datetime >= log_entries[1].utc_datetime


def test_parse_simple_object_invalid(component):
    object_data = deepcopy(OBJECT_DATA)
    del object_data['object_id']
    with pytest.raises(errors.InvalidDataExportError):
        parse_import_object(object_data, component)

    object_data = deepcopy(OBJECT_DATA)
    del object_data['versions'][0]['version_id']
    with pytest.raises(errors.InvalidDataExportError):
        parse_import_object(object_data, component)


def test_import_simple_object_no_schema(component):
    object_data = deepcopy(OBJECT_DATA)
    del object_data['versions'][0]['schema']
    start_datetime = datetime.datetime.utcnow()
    object = parse_import_object(object_data, component)
    del object_data['versions'][0]['data']
    _check_object(object_data, component)

    assert len(get_objects()) == 1

    log_entries = get_fed_object_log_entries_for_object(object.id)
    assert len(FedObjectLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLogEntryType.IMPORT_OBJECT
    assert log_entries[0].component_id == component.id
    assert log_entries[0].object_id == object.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_simple_object_no_data(component):
    object_data = deepcopy(OBJECT_DATA)
    del object_data['versions'][0]['data']
    start_datetime = datetime.datetime.utcnow()
    object = parse_import_object(object_data, component)
    _check_object(object_data, component)

    assert len(get_objects()) == 1

    log_entries = get_fed_object_log_entries_for_object(object.id)
    assert len(FedObjectLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLogEntryType.IMPORT_OBJECT
    assert log_entries[0].component_id == component.id
    assert log_entries[0].object_id == object.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_simple_object_no_user(component):
    object_data = deepcopy(OBJECT_DATA)
    del object_data['versions'][0]['user']
    start_datetime = datetime.datetime.utcnow()
    object = parse_import_object(object_data, component)
    _check_object(object_data, component)

    assert len(get_objects()) == 1

    log_entries = get_fed_object_log_entries_for_object(object.id)
    assert len(FedObjectLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLogEntryType.IMPORT_OBJECT
    assert log_entries[0].component_id == component.id
    assert log_entries[0].object_id == object.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_simple_object_no_action(component):
    object_data = deepcopy(OBJECT_DATA)
    del object_data['action']
    start_datetime = datetime.datetime.utcnow()
    object = parse_import_object(object_data, component)
    _check_object(object_data, component)

    assert len(get_objects()) == 1

    log_entries = get_fed_object_log_entries_for_object(object.id)
    assert len(FedObjectLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLogEntryType.IMPORT_OBJECT
    assert log_entries[0].component_id == component.id
    assert log_entries[0].object_id == object.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_simple_object_no_utc_datetime(component):
    object_data = deepcopy(OBJECT_DATA)
    del object_data['versions'][0]['utc_datetime']
    start_datetime = datetime.datetime.utcnow()
    object = parse_import_object(object_data, component)
    _check_object(object_data, component)

    assert len(get_objects()) == 1

    log_entries = get_fed_object_log_entries_for_object(object.id)
    assert len(FedObjectLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLogEntryType.IMPORT_OBJECT
    assert log_entries[0].component_id == component.id
    assert log_entries[0].object_id == object.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_markdown_image(component):
    parse_import_markdown_image((64 * 'a' + 'png', 'MQ=='), component)
    parse_import_markdown_image((64 * 'b' + 'png', 'Mg=='), component)
    parse_import_markdown_image((64 * 'c' + 'png', 'Mw=='), component)

    markdown_images = MarkdownImage.query.all()
    assert len(markdown_images) == 3
    assert markdown_images[0].file_name == 64 * 'a' + 'png'
    assert markdown_images[0].content == b'1'
    assert markdown_images[0].user_id is None
    assert markdown_images[0].permanent is True
    assert markdown_images[0].component_id == component.id
    assert markdown_images[1].file_name == 64 * 'b' + 'png'
    assert markdown_images[1].content == b'2'
    assert markdown_images[1].user_id is None
    assert markdown_images[1].permanent is True
    assert markdown_images[1].component_id == component.id
    assert markdown_images[2].file_name == 64 * 'c' + 'png'
    assert markdown_images[2].content == b'3'
    assert markdown_images[2].user_id is None
    assert markdown_images[2].permanent is True
    assert markdown_images[2].component_id == component.id


def test_import_object_history(component, object_history):
    object_data_1, object_data_2, object_data_3 = object_history
    object_2 = parse_import_object(object_data_2, component)
    object_id = object_2.object_id
    _check_object(object_data_2, component)
    assert object_2 == get_object(object_id)

    object_1 = parse_import_object(object_data_1, component)
    _check_object(object_data_1, component)
    assert object_2 == get_object(object_id)
    assert [object_1, object_2] == get_object_versions(object_id)

    object_3 = parse_import_object(object_data_3, component)
    _check_object(object_data_3, component)
    assert object_3 == get_object(object_id)
    assert [object_1, object_2, object_3] == get_object_versions(object_id)


def test_import_object_version_update(component, object_history):
    object_data_1, object_data_2, _ = object_history
    object_1 = parse_import_object(object_data_1, component)
    _check_object(object_data_1, component)
    object_id = object_1.object_id
    assert object_1 == get_object(object_id)
    assert [object_1] == get_object_versions(object_id)

    object_data_2['versions'][0]['version_id'] = 0
    object_2 = parse_import_object(object_data_2, component)
    _check_object(object_data_2, component)
    get_object(object_id)
    assert object_2 == get_object(object_id)
    assert [object_2] == get_object_versions(object_id)


def test_import_object_tags(component):
    object_data = deepcopy(OBJECT_DATA)
    object_data['versions'][0]['data'] = deepcopy(COMPLEX_OBJECT_DATA)
    object_data['versions'][0]['schema'] = deepcopy(COMPLEX_ACTION_SCHEMA)
    parse_import_object(object_data, component)
    tags = get_tags()
    assert len(tags) == len(object_data['versions'][0]['data']['tags']['tags'])
    for tag in tags:
        assert tag.name in object_data['versions'][0]['data']['tags']['tags']
        assert tag.uses == 1


def test_import_object_tags_new_subversion(component):
    object_data = deepcopy(OBJECT_DATA)
    object_data['versions'][0]['data'] = deepcopy(COMPLEX_OBJECT_DATA)
    object_data['versions'][0]['schema'] = deepcopy(COMPLEX_ACTION_SCHEMA)
    parse_import_object(object_data, component)

    object_data_2 = deepcopy(object_data)
    object_data_2['versions'][0]['data']['tags']['tags'].remove('object')
    parse_import_object(object_data_2, component)
    tags = get_tags()
    assert len(tags) == len(object_data_2['versions'][0]['data']['tags']['tags'])
    for tag in tags:
        assert tag.name in object_data_2['versions'][0]['data']['tags']['tags']
        assert tag.uses == 1

    object_data_3 = deepcopy(object_data)
    object_data_3['versions'][0]['data']['tags']['tags'].append('tag')
    parse_import_object(object_data_3, component)
    tags = get_tags()
    assert len(tags) == len(object_data_3['versions'][0]['data']['tags']['tags'])
    for tag in tags:
        assert tag.name in object_data_3['versions'][0]['data']['tags']['tags']
        assert tag.uses == 1


def test_import_object_tags_new_subversion_old_previous_version(component):
    object_data = deepcopy(OBJECT_DATA)
    object_data['versions'][0]['data'] = deepcopy(COMPLEX_OBJECT_DATA)
    object_data['versions'][0]['schema'] = deepcopy(COMPLEX_ACTION_SCHEMA)
    parse_import_object(object_data, component)

    object_data_2 = deepcopy(object_data)

    object_data_2['versions'][0]['version_id'] += 1
    parse_import_object(object_data_2, component)

    object_data_3 = deepcopy(object_data)
    object_data_3['versions'][0]['data']['tags']['tags'].remove('object')
    parse_import_object(object_data_3, component)
    tags = get_tags()
    assert len(tags) == len(object_data['versions'][0]['data']['tags']['tags'])
    for tag in tags:
        assert tag.name in object_data['versions'][0]['data']['tags']['tags']
        assert tag.uses == 1

    object_data_4 = deepcopy(object_data)
    object_data_4['versions'][0]['data']['tags']['tags'].append('tag')
    parse_import_object(object_data_4, component)
    tags = get_tags()
    assert len(tags) == len(object_data['versions'][0]['data']['tags']['tags'])
    for tag in tags:
        assert tag.name in object_data['versions'][0]['data']['tags']['tags']
        assert tag.uses == 1


def test_import_object_tags_new_old_version(component):
    object_data = deepcopy(OBJECT_DATA)
    object_data['versions'][0]['data'] = deepcopy(COMPLEX_OBJECT_DATA)
    object_data['versions'][0]['schema'] = deepcopy(COMPLEX_ACTION_SCHEMA)
    object_data['versions'][0]['version_id'] = 3
    parse_import_object(object_data, component)

    object_data_2 = deepcopy(object_data)
    object_data_2['versions'][0]['data']['tags']['tags'].remove('object')
    object_data_2['versions'][0]['version_id'] = 2
    parse_import_object(object_data_2, component)
    tags = get_tags()
    assert len(tags) == len(object_data['versions'][0]['data']['tags']['tags'])
    for tag in tags:
        assert tag.name in object_data['versions'][0]['data']['tags']['tags']
        assert tag.uses == 1

    object_data_3 = deepcopy(object_data)
    object_data_3['versions'][0]['data']['tags']['tags'].append('tag')
    object_data_3['versions'][0]['version_id'] = 1
    parse_import_object(object_data_3, component)
    tags = get_tags()
    assert len(tags) == len(object_data['versions'][0]['data']['tags']['tags'])
    for tag in tags:
        assert tag.name in object_data['versions'][0]['data']['tags']['tags']
        assert tag.uses == 1


def test_import_object_table_list_references(component, user, fed_user, simple_object):
    fed_data = deepcopy(simple_object.data)
    fed_data['name']['text'] = 'Imported'
    fed_object = insert_fed_object_version(
        fed_object_id=42,
        fed_version_id=0,
        component_id=component.id,
        action_id=None,
        user_id=fed_user.id,
        data=fed_data,
        schema=simple_object.schema,
        utc_datetime=datetime.datetime.utcnow()
    )
    object_permissions.set_user_object_permissions(object_id=fed_object.object_id, user_id=user.id, permissions=object_permissions.Permissions.READ)
    data = deepcopy(REFERENCES_TABLE_LIST_DATA_FRAME)
    data['user1']['user_id'] = fed_user.id  # imported user
    data['user1']['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['user2']['user_id'] = 12  # unknown user, unknown component
    data['user2']['component_uuid'] = UUID_2
    data['user3']['user_id'] = user.id  # local user
    data['user3']['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['user4']['user_id'] = fed_user.fed_id + 1  # unknown user, known component
    data['user4']['component_uuid'] = component.uuid

    data['object1']['object_id'] = fed_object.object_id  # imported object
    data['object1']['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['object2']['object_id'] = 6  # unknown object, unknown component
    data['object2']['component_uuid'] = UUID_2
    data['object3']['object_id'] = simple_object.object_id  # local object
    data['object3']['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['object4']['object_id'] = fed_object.fed_object_id + 1  # unknown object, known component
    data['object4']['component_uuid'] = component.uuid

    data['userlist'][0]['user_id'] = fed_user.id  # imported user
    data['userlist'][0]['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['userlist'][1]['user_id'] = 12  # unknown user, unknown component
    data['userlist'][1]['component_uuid'] = UUID_2
    data['userlist'][2]['user_id'] = user.id  # local user
    data['userlist'][2]['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['userlist'][3]['user_id'] = fed_user.fed_id + 1  # unknown user, known component
    data['userlist'][3]['component_uuid'] = component.uuid

    data['objectlist'][0]['object_id'] = fed_object.object_id  # imported object
    data['objectlist'][0]['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['objectlist'][1]['object_id'] = 6  # unknown object, unknown component
    data['objectlist'][1]['component_uuid'] = UUID_2
    data['objectlist'][2]['object_id'] = simple_object.object_id  # local object
    data['objectlist'][2]['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['objectlist'][3]['object_id'] = fed_object.fed_object_id + 1  # unknown object, known component
    data['objectlist'][3]['component_uuid'] = component.uuid

    data['usertable'][0][0]['user_id'] = fed_user.id  # imported user
    data['usertable'][0][0]['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['usertable'][0][1]['user_id'] = 12  # unknown user, unknown component
    data['usertable'][0][1]['component_uuid'] = UUID_2
    data['usertable'][1][0]['user_id'] = user.id  # local user
    data['usertable'][1][0]['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['usertable'][1][1]['user_id'] = fed_user.fed_id + 1  # unknown user, known component
    data['usertable'][1][1]['component_uuid'] = component.uuid

    data['objecttable'][0][0]['object_id'] = fed_object.object_id  # imported object
    data['objecttable'][0][0]['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['objecttable'][0][1]['object_id'] = 6  # unknown object, unknown component
    data['objecttable'][0][1]['component_uuid'] = UUID_2
    data['objecttable'][1][0]['object_id'] = simple_object.object_id  # local object
    data['objecttable'][1][0]['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
    data['objecttable'][1][1]['object_id'] = fed_object.fed_object_id + 1  # unknown object, known component
    data['objecttable'][1][1]['component_uuid'] = component.uuid

    parse_import_object({
        'object_id': 3,
        'versions': [{
            'version_id': 0,
            'data': data,
            'schema': REFERENCES_TABLE_LIST_SCHEMA,
            'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
        }],
        'policy': {}
    }, component)


def test_import_action(component):
    action_data = deepcopy(ACTION_DATA)
    start_datetime = datetime.datetime.utcnow()
    action = parse_import_action(action_data, component)
    _check_action(action_data)

    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_template_action_without_template(component):
    action_data = deepcopy(ACTION_DATA)
    action_data['schema']['properties']['template'] = {
        'type': 'object',
        'title': 'Template',
        'template': {'action_id': 123, 'component_uuid': UUID_1},
        'properties': {'text': {'title': 'Template Text', 'type': 'text'}}
    }
    start_datetime = datetime.datetime.utcnow()
    action = parse_import_action(action_data, component)
    _check_action(action_data)

    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_template_action_with_template(component):
    template_data = deepcopy(ACTION_DATA)
    template_data['action_id'] = 123
    template_data['schema'] = {
        'type': 'object',
        'title': 'Template',
        'properties': {'name': {'type': 'text', 'title': 'Name'}, 'text': {'title': 'Template Text', 'type': 'text'}},
        'required': ['name']
    }
    action_data = deepcopy(ACTION_DATA)
    action_data['schema']['properties']['template'] = {
        'type': 'object',
        'title': 'Template',
        'template': {'action_id': 123, 'component_uuid': UUID_1},
        'properties': {'text': {'title': 'Template Text', 'type': 'text'}}
    }
    start_datetime = datetime.datetime.utcnow()
    template_action = parse_import_action(template_data, component)
    action = parse_import_action(action_data, component)
    # resolve template reference for _check_action
    action_data['schema']['properties']['template'] = {
        'type': 'object',
        'title': 'Template',
        'template': template_action.id,
        'properties': {'text': {'title': 'Template Text', 'type': 'text'}},
        'required': []
    }
    _check_action(action_data)
    _check_action(template_data)

    assert action.schema['properties']['template']['template'] == template_action.id

    assert len(actions.get_actions()) == 2
    assert len(FedActionLogEntry.query.all()) == 2

    log_entries = get_fed_action_log_entries_for_action(template_action.id)
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == template_action.component.id
    assert log_entries[0].action_id == template_action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_update_action(component):
    old_action_data = deepcopy(ACTION_DATA)
    start_datetime = datetime.datetime.utcnow()
    old_action = parse_import_action(old_action_data, component)

    action_data = deepcopy(ACTION_DATA)
    action_data['description_is_markdown'] = True
    action_data['short_description_is_markdown'] = True
    action_data['is_hidden'] = True
    action_data['schema'] = {
        'title': 'Updated Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'description': {
                'title': 'Description',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    action_data['instrument'] = {
        'instrument_id': 7,
        'component_uuid': UUID_1
    }
    action_data['user'] = {
        'user_id': 5,
        'component_uuid': UUID_1
    }
    action_data['translations'] = {
        'en': {
            'name': 'Updated Example Action',
            'description': 'Updated description',
            'short_description': 'Updated short description'
        },
        'de': {
            'name': 'Aktualisierte Beispielaktion',
            'description': 'Aktualisierte Beschreibung',
            'short_description': 'Aktualiserte Kurzbeschreibung'
        }
    }
    action = parse_import_action(action_data, component)
    _check_action(action_data)

    assert old_action.id == action.id
    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 2
    assert len(log_entries) == 2
    assert log_entries[1].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[1].component_id == action.component.id
    assert log_entries[1].action_id == action.id
    assert log_entries[1].utc_datetime >= start_datetime
    assert log_entries[1].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].type == FedActionLogEntryType.UPDATE_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].utc_datetime >= log_entries[1].utc_datetime


def test_parse_action_invalid_data():
    _invalid_component_uuid_test(ACTION_DATA, parse_action)
    _invalid_id_test(ACTION_DATA, 'action_id', parse_action)
    _invalid_reference_test(ACTION_DATA, 'action_type', 'action_type_id', parse_action, mandatory=True)
    _invalid_reference_test(ACTION_DATA, 'instrument', 'instrument_id', parse_action)
    _invalid_reference_test(ACTION_DATA, 'user', 'user_id', parse_action)
    _invalid_dict_test(ACTION_DATA, 'schema', parse_action)

    def check_schema_not_none(action_data):
        parsed_action_data = parse_action(action_data)
        if parsed_action_data['schema'] is None:
            raise errors.InvalidDataExportError()
    _invalid_schema_test(ACTION_DATA, 'schema', check_schema_not_none)
    _invalid_bool_test(ACTION_DATA, 'description_is_markdown', parse_action)
    _invalid_bool_test(ACTION_DATA, 'is_hidden', parse_action)
    _invalid_bool_test(ACTION_DATA, 'short_description_is_markdown', parse_action)

    _invalid_dict_test(ACTION_DATA, 'translations', parse_action)
    # creates action_type but does not insert translations -> no rollback!
    for lang in ACTION_DATA['translations'].keys():
        _invalid_translation_str_test(ACTION_DATA, lang, 'name', parse_action)
        _invalid_translation_str_test(ACTION_DATA, lang, 'description', parse_action)
        _invalid_translation_str_test(ACTION_DATA, lang, 'short_description', parse_action)

    assert len(actions.get_actions()) == 0
    assert len(FedActionLogEntry.query.all()) == 0
    assert len(ActionTranslation.query.all()) == 0


def test_import_action_no_description_is_markdown(component):
    action_data = deepcopy(ACTION_DATA)
    del action_data['description_is_markdown']
    start_datetime = datetime.datetime.utcnow()
    action = parse_import_action(action_data, component)
    action_data['description_is_markdown'] = False
    _check_action(action_data)

    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_action_no_short_description_is_markdown(component):
    action_data = deepcopy(ACTION_DATA)
    del action_data['short_description_is_markdown']
    start_datetime = datetime.datetime.utcnow()
    action = parse_import_action(action_data, component)
    action_data['short_description_is_markdown'] = False
    _check_action(action_data)

    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_action_no_instrument(component):
    action_data = deepcopy(ACTION_DATA)
    del action_data['instrument']
    start_datetime = datetime.datetime.utcnow()
    action = parse_import_action(action_data, component)
    _check_action(action_data)

    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_action_no_schema(component):
    action_data = deepcopy(ACTION_DATA)
    del action_data['schema']
    start_datetime = datetime.datetime.utcnow()
    action = parse_import_action(action_data, component)
    _check_action(action_data)

    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_action_no_user(component):
    action_data = deepcopy(ACTION_DATA)
    del action_data['user']
    start_datetime = datetime.datetime.utcnow()
    action = parse_import_action(action_data, component)
    _check_action(action_data)

    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_action_no_is_hidden(component):
    action_data = deepcopy(ACTION_DATA)
    del action_data['is_hidden']
    start_datetime = datetime.datetime.utcnow()
    action = parse_import_action(action_data, component)
    action_data['is_hidden'] = False
    _check_action(action_data)

    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_action_no_translations(component):
    action_data = deepcopy(ACTION_DATA)
    del action_data['translations']
    start_datetime = datetime.datetime.utcnow()
    action = parse_import_action(action_data, component)
    _check_action(action_data)

    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_action_type(component):
    # default action_types
    num_types = len(actions.get_action_types())
    action_type_data = deepcopy(ACTION_TYPE_DATA)
    start_datetime = datetime.datetime.utcnow()
    action_type = parse_import_action_type(action_type_data, component)
    _check_action_type(action_type_data)

    assert len(actions.get_action_types()) == num_types + 1

    log_entries = get_fed_action_type_log_entries_for_action_type(action_type.id)
    assert len(FedActionTypeLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionTypeLogEntryType.IMPORT_ACTION_TYPE
    assert log_entries[0].component_id == action_type.component_id
    assert log_entries[0].action_type_id == action_type.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_default_action_type(component):
    for i, action_type_id in enumerate([ActionType.SAMPLE_CREATION, ActionType.MEASUREMENT, ActionType.SIMULATION]):
        num_types = len(actions.get_action_types())
        action_type_data = deepcopy(ACTION_TYPE_DATA)
        action_type_data['action_type_id'] = action_type_id
        start_datetime = datetime.datetime.utcnow()
        action_type = parse_import_action_type(action_type_data, component)
        _check_action_type(action_type_data)

        assert len(actions.get_action_types()) == num_types + 1

        log_entries = get_fed_action_type_log_entries_for_action_type(action_type.id)
        assert len(FedActionTypeLogEntry.query.all()) == 1 + i
        assert len(log_entries) == 1
        assert log_entries[0].type == FedActionTypeLogEntryType.IMPORT_ACTION_TYPE
        assert log_entries[0].component_id == action_type.component_id
        assert log_entries[0].action_type_id == action_type.id
        assert log_entries[0].utc_datetime >= start_datetime
        assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_update_action_type(component):
    # default action_types
    num_types = len(actions.get_action_types())

    old_action_type_data = deepcopy(ACTION_TYPE_DATA)
    start_datetime = datetime.datetime.utcnow()
    old_action_type = parse_import_action_type(old_action_type_data, component)

    action_type_data = deepcopy(ACTION_TYPE_DATA)
    for key in action_type_data:
        if key not in {'component_uuid', 'action_type_id'}:
            action_type_data[key] = not action_type_data[key]
    action_type_data['translations'] = {
        'en': {
            'name': 'Updated Action Type',
            'description': 'Updated Description',
            'object_name': 'Updated Action Object',
            'object_name_plural': 'Updated Action Objects',
            'view_text': 'Show Updated Action Objects',
            'perform_text': 'Perform UpdatedAction Type Action'
        },
        'de': {
            'name': 'Aktualisierter Aktionstyp',
            'description': 'Aktualisierte Beschreibung',
            'object_name': 'Aktualisiertes Aktionsobjekt',
            'object_name_plural': 'Aktualisierte Aktionsobjekte',
            'view_text': 'Zeige aktualisierte Aktionsobjekte',
            'perform_text': 'Führe aktualisierte Aktionstyp-Aktion aus'
        }
    }

    action_type = parse_import_action_type(action_type_data, component)
    _check_action_type(action_type_data)

    assert len(actions.get_action_types()) == num_types + 1
    assert old_action_type.id == action_type.id

    log_entries = get_fed_action_type_log_entries_for_action_type(action_type.id)
    assert len(FedActionTypeLogEntry.query.all()) == 2
    assert len(log_entries) == 2
    assert log_entries[1].type == FedActionTypeLogEntryType.IMPORT_ACTION_TYPE
    assert log_entries[1].component_id == action_type.component_id
    assert log_entries[1].action_type_id == action_type.id
    assert log_entries[1].utc_datetime >= start_datetime
    assert log_entries[1].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].type == FedActionTypeLogEntryType.UPDATE_ACTION_TYPE
    assert log_entries[0].component_id == action_type.component_id
    assert log_entries[0].action_type_id == action_type.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].utc_datetime >= log_entries[1].utc_datetime


def test_parse_action_type_invalid_data(component):
    # default action_types
    num_types = len(actions.get_action_types())
    num_translations = len(ActionTypeTranslation.query.all())

    _invalid_id_test(ACTION_TYPE_DATA, 'action_type_id', parse_action_type)
    _invalid_component_uuid_test(ACTION_TYPE_DATA, parse_action_type)
    _invalid_bool_test(ACTION_TYPE_DATA, 'admin_only', parse_action_type)
    _invalid_bool_test(ACTION_TYPE_DATA, 'enable_labels', parse_action_type)
    _invalid_bool_test(ACTION_TYPE_DATA, 'enable_files', parse_action_type)
    _invalid_bool_test(ACTION_TYPE_DATA, 'enable_locations', parse_action_type)
    _invalid_bool_test(ACTION_TYPE_DATA, 'enable_publications', parse_action_type)
    _invalid_bool_test(ACTION_TYPE_DATA, 'enable_comments', parse_action_type)
    _invalid_bool_test(ACTION_TYPE_DATA, 'enable_activity_log', parse_action_type)
    _invalid_bool_test(ACTION_TYPE_DATA, 'enable_related_objects', parse_action_type)
    _invalid_bool_test(ACTION_TYPE_DATA, 'enable_project_link', parse_action_type)

    # creates action_type but does not insert translations -> no rollback!
    _invalid_dict_test(ACTION_TYPE_DATA, 'translations', parse_action_type)
    for lang in ACTION_TYPE_DATA['translations'].keys():
        _invalid_translation_str_test(ACTION_TYPE_DATA, lang, 'name', parse_action_type)
        _invalid_translation_str_test(ACTION_TYPE_DATA, lang, 'description', parse_action_type)
        _invalid_translation_str_test(ACTION_TYPE_DATA, lang, 'object_name', parse_action_type)
        _invalid_translation_str_test(ACTION_TYPE_DATA, lang, 'object_name_plural', parse_action_type)
        _invalid_translation_str_test(ACTION_TYPE_DATA, lang, 'view_text', parse_action_type)
        _invalid_translation_str_test(ACTION_TYPE_DATA, lang, 'perform_text', parse_action_type)

    assert len(actions.get_action_types()) == num_types
    assert len(FedActionTypeLogEntry.query.all()) == 0
    assert len(ActionTypeTranslation.query.all()) == num_translations


def test_import_instrument(component):
    instrument_data = deepcopy(INSTRUMENT_DATA)
    start_datetime = datetime.datetime.utcnow()
    instrument = parse_import_instrument(instrument_data, component)
    _check_instrument(instrument_data)

    assert len(instruments.get_instruments()) == 1

    log_entries = get_fed_instrument_log_entries_for_instrument(instrument.id)
    assert len(FedInstrumentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedInstrumentLogEntryType.IMPORT_INSTRUMENT
    assert log_entries[0].component_id == instrument.component.id
    assert log_entries[0].instrument_id == instrument.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_update_instrument(component):
    old_instrument_data = deepcopy(INSTRUMENT_DATA)
    start_datetime = datetime.datetime.utcnow()
    old_instrument = parse_import_instrument(old_instrument_data, component)

    instrument_data = deepcopy(INSTRUMENT_DATA)
    instrument_data['is_hidden'] = True
    instrument_data['translations'] = {
        'en': {
            'name': 'Updated Example Instrument',
            'description': 'Updated description',
            'short_description': 'Updated short description',
            'notes': 'Updated Notes'
        },
        'de': {
            'name': 'Aktualisiertes Beispielinstrument',
            'description': 'Aktualisierte Beschreibung',
            'short_description': 'Aktualiserte Kurzbeschreibung',
            'notes': 'Aktualisierte Notizen'
        }
    }

    instrument = parse_import_instrument(instrument_data, component)
    _check_instrument(instrument_data)

    assert old_instrument.id == instrument.id
    assert len(instruments.get_instruments()) == 1

    log_entries = get_fed_instrument_log_entries_for_instrument(instrument.id)
    assert len(FedInstrumentLogEntry.query.all()) == 2
    assert len(log_entries) == 2
    assert log_entries[1].type == FedInstrumentLogEntryType.IMPORT_INSTRUMENT
    assert log_entries[1].component_id == instrument.component.id
    assert log_entries[1].instrument_id == instrument.id
    assert log_entries[1].utc_datetime >= start_datetime
    assert log_entries[1].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].type == FedInstrumentLogEntryType.UPDATE_INSTRUMENT
    assert log_entries[0].component_id == instrument.component.id
    assert log_entries[0].instrument_id == instrument.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].utc_datetime >= log_entries[1].utc_datetime


def test_parse_instrument_invalid_data():
    _invalid_component_uuid_test(INSTRUMENT_DATA, parse_instrument)
    _invalid_id_test(INSTRUMENT_DATA, 'instrument_id', parse_instrument)
    _invalid_bool_test(INSTRUMENT_DATA, 'description_is_markdown', parse_instrument)
    _invalid_bool_test(INSTRUMENT_DATA, 'is_hidden', parse_instrument)
    _invalid_bool_test(INSTRUMENT_DATA, 'short_description_is_markdown', parse_instrument)
    _invalid_bool_test(INSTRUMENT_DATA, 'notes_is_markdown', parse_instrument)

    _invalid_dict_test(INSTRUMENT_DATA, 'translations', parse_instrument)
    # creates action_type but does not insert translations -> no rollback!
    for lang in INSTRUMENT_DATA['translations'].keys():
        _invalid_translation_str_test(INSTRUMENT_DATA, lang, 'name', parse_instrument)
        _invalid_translation_str_test(INSTRUMENT_DATA, lang, 'description', parse_instrument)
        _invalid_translation_str_test(INSTRUMENT_DATA, lang, 'short_description', parse_instrument)
        _invalid_translation_str_test(INSTRUMENT_DATA, lang, 'notes', parse_instrument)

    assert len(instruments.get_instruments()) == 0
    assert len(FedInstrumentLogEntry.query.all()) == 0
    assert len(InstrumentTranslation.query.all()) == 0


def test_import_instrument_no_description_is_markdown(component):
    instrument_data = deepcopy(INSTRUMENT_DATA)
    del instrument_data['description_is_markdown']
    start_datetime = datetime.datetime.utcnow()
    instrument = parse_import_instrument(instrument_data, component)
    instrument_data['description_is_markdown'] = False
    _check_instrument(instrument_data)

    assert len(instruments.get_instruments()) == 1

    log_entries = get_fed_instrument_log_entries_for_instrument(instrument.id)
    assert len(FedInstrumentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedInstrumentLogEntryType.IMPORT_INSTRUMENT
    assert log_entries[0].component_id == instrument.component.id
    assert log_entries[0].instrument_id == instrument.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_instrument_no_short_description_is_markdown(component):
    instrument_data = deepcopy(INSTRUMENT_DATA)
    del instrument_data['short_description_is_markdown']
    start_datetime = datetime.datetime.utcnow()
    instrument = parse_import_instrument(instrument_data, component)
    instrument_data['short_description_is_markdown'] = False
    _check_instrument(instrument_data)

    assert len(instruments.get_instruments()) == 1

    log_entries = get_fed_instrument_log_entries_for_instrument(instrument.id)
    assert len(FedInstrumentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedInstrumentLogEntryType.IMPORT_INSTRUMENT
    assert log_entries[0].component_id == instrument.component.id
    assert log_entries[0].instrument_id == instrument.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_instrument_no_is_hidden(component):
    instrument_data = deepcopy(INSTRUMENT_DATA)
    del instrument_data['is_hidden']
    start_datetime = datetime.datetime.utcnow()
    instrument = parse_import_instrument(instrument_data, component)
    instrument_data['is_hidden'] = False
    _check_instrument(instrument_data)

    assert len(instruments.get_instruments()) == 1

    log_entries = get_fed_instrument_log_entries_for_instrument(instrument.id)
    assert len(FedInstrumentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedInstrumentLogEntryType.IMPORT_INSTRUMENT
    assert log_entries[0].component_id == instrument.component.id
    assert log_entries[0].instrument_id == instrument.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_instrument_no_translations(component):
    instrument_data = deepcopy(INSTRUMENT_DATA)
    del instrument_data['translations']
    start_datetime = datetime.datetime.utcnow()
    instrument = parse_import_instrument(instrument_data, component)
    _check_instrument(instrument_data)

    assert len(instruments.get_instruments()) == 1

    log_entries = get_fed_instrument_log_entries_for_instrument(instrument.id)
    assert len(FedInstrumentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedInstrumentLogEntryType.IMPORT_INSTRUMENT
    assert log_entries[0].component_id == instrument.component.id
    assert log_entries[0].instrument_id == instrument.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_user(component):
    user_data = deepcopy(USER_DATA)
    start_datetime = datetime.datetime.utcnow()
    user = parse_import_user(user_data, component)
    _check_user(user_data)

    assert len(logic.users.get_users()) == 1

    log_entries = get_fed_user_log_entries_for_user(user.id)
    assert len(FedUserLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedUserLogEntryType.IMPORT_USER
    assert log_entries[0].component_id == user.component.id
    assert log_entries[0].user_id == user.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_update_user(component):
    old_user_data = deepcopy(USER_DATA)
    start_datetime = datetime.datetime.utcnow()
    old_user = parse_import_user(old_user_data, component)

    user_data = deepcopy(USER_DATA)
    user_data['name'] = 'Updated User'
    user_data['email'] = 'example2@example.com'
    user_data['affiliation'] = 'PGI'

    user = parse_import_user(user_data, component)
    _check_user(user_data)

    assert old_user.id == user.id
    assert len(logic.users.get_users()) == 1

    log_entries = get_fed_user_log_entries_for_user(user.id)
    assert len(FedUserLogEntry.query.all()) == 2
    assert len(log_entries) == 2
    assert log_entries[1].type == FedUserLogEntryType.IMPORT_USER
    assert log_entries[1].component_id == user.component.id
    assert log_entries[1].user_id == user.id
    assert log_entries[1].utc_datetime >= start_datetime
    assert log_entries[1].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].type == FedUserLogEntryType.UPDATE_USER
    assert log_entries[0].component_id == user.component.id
    assert log_entries[0].user_id == user.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].utc_datetime >= log_entries[1].utc_datetime


def test_parse_user_invalid_data(component):
    def parse_function(user_data):
        return parse_user(user_data, component)
    _invalid_component_uuid_test(USER_DATA, parse_function)
    _invalid_id_test(USER_DATA, 'user_id', parse_function)
    _invalid_str_test(USER_DATA, 'name', parse_function)
    _invalid_str_test(USER_DATA, 'email', parse_function)
    _invalid_str_test(USER_DATA, 'orcid', parse_function)
    _invalid_str_test(USER_DATA, 'affiliation', parse_function)
    _invalid_str_test(USER_DATA, 'role', parse_function)
    _invalid_dict_test(USER_DATA, 'extra_fields', parse_function)

    assert len(logic.users.get_users()) == 0
    assert len(FedUserLogEntry.query.all()) == 0


def test_import_user_no_name(component):
    user_data = deepcopy(USER_DATA)
    del user_data['name']
    start_datetime = datetime.datetime.utcnow()
    user = parse_import_user(user_data, component)
    _check_user(user_data)

    assert len(logic.users.get_users()) == 1

    log_entries = get_fed_user_log_entries_for_user(user.id)
    assert len(FedUserLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedUserLogEntryType.IMPORT_USER
    assert log_entries[0].component_id == user.component.id
    assert log_entries[0].user_id == user.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_user_no_email(component):
    user_data = deepcopy(USER_DATA)
    del user_data['email']
    start_datetime = datetime.datetime.utcnow()
    user = parse_import_user(user_data, component)
    _check_user(user_data)

    assert len(logic.users.get_users()) == 1

    log_entries = get_fed_user_log_entries_for_user(user.id)
    assert len(FedUserLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedUserLogEntryType.IMPORT_USER
    assert log_entries[0].component_id == user.component.id
    assert log_entries[0].user_id == user.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_user_no_affiliation(component):
    user_data = deepcopy(USER_DATA)
    del user_data['affiliation']
    start_datetime = datetime.datetime.utcnow()
    user = parse_import_user(user_data, component)
    _check_user(user_data)

    assert len(logic.users.get_users()) == 1

    log_entries = get_fed_user_log_entries_for_user(user.id)
    assert len(FedUserLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedUserLogEntryType.IMPORT_USER
    assert log_entries[0].component_id == user.component.id
    assert log_entries[0].user_id == user.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_location_type(component):
    num_default_location_types = len(logic.locations.get_location_types())
    location_type_data = deepcopy(LOCATION_TYPE_DATA)
    start_datetime = datetime.datetime.utcnow()
    location_type = parse_import_location_type(location_type_data, component)
    _check_location_type(location_type_data)

    assert len(logic.locations.get_location_types()) == num_default_location_types + 1

    log_entries = get_fed_location_type_log_entries_for_location_type(location_type.id)
    assert len(log_entries) == 1
    assert log_entries[0].type == FedLocationTypeLogEntryType.IMPORT_LOCATION_TYPE
    assert log_entries[0].component_id == location_type.component.id
    assert log_entries[0].location_type_id == location_type.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_update_location_type(component):
    num_default_location_types = len(logic.locations.get_location_types())
    old_location_type_data = deepcopy(LOCATION_TYPE_DATA)
    start_datetime = datetime.datetime.utcnow()
    old_location_type = parse_import_location_type(old_location_type_data, component)

    location_type_data = deepcopy(LOCATION_TYPE_DATA)
    location_type_data['name'] = {'en': 'Updated Location Type', 'de': 'Aktualisierter Ortstyp'}
    location_type_data['admin_only'] = not old_location_type.admin_only

    location_type = parse_import_location_type(location_type_data, component)
    _check_location_type(location_type_data)

    assert old_location_type.id == location_type.id
    assert len(logic.locations.get_location_types()) == num_default_location_types + 1

    log_entries = get_fed_location_type_log_entries_for_location_type(location_type.id)
    assert len(log_entries) == 2
    assert log_entries[1].type == FedLocationTypeLogEntryType.IMPORT_LOCATION_TYPE
    assert log_entries[1].component_id == location_type.component.id
    assert log_entries[1].location_type_id == location_type.id
    assert log_entries[1].utc_datetime >= start_datetime
    assert log_entries[1].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].type == FedLocationTypeLogEntryType.UPDATE_LOCATION_TYPE
    assert log_entries[0].component_id == location_type.component.id
    assert log_entries[0].location_type_id == location_type.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].utc_datetime >= log_entries[1].utc_datetime


def test_parse_location_type_invalid_data():
    num_default_location_types = len(logic.locations.get_location_types())
    _invalid_component_uuid_test(LOCATION_TYPE_DATA, parse_location)
    _invalid_id_test(LOCATION_TYPE_DATA, 'location_type_id', parse_location)
    _invalid_translation_test(LOCATION_TYPE_DATA, 'name', parse_location)
    _invalid_translation_test(LOCATION_TYPE_DATA, 'location_name_singular', parse_location)
    _invalid_translation_test(LOCATION_TYPE_DATA, 'location_name_plural', parse_location)

    assert len(logic.locations.get_location_types()) == num_default_location_types
    assert len(FedLocationTypeLogEntry.query.all()) == 0


def test_import_location(component):
    location_data = deepcopy(LOCATION_DATA)
    start_datetime = datetime.datetime.utcnow()
    location = parse_import_location(location_data, component)
    _check_location(location_data)

    assert len(logic.locations.get_locations()) == 2    # including parent reference

    log_entries = get_fed_location_log_entries_for_location(location.id)
    assert len(log_entries) == 1
    assert log_entries[0].type == FedLocationLogEntryType.IMPORT_LOCATION
    assert log_entries[0].component_id == location.component.id
    assert log_entries[0].location_id == location.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_location_unknown_language(component):
    location_data = deepcopy(LOCATION_DATA)
    location_data['name']['se'] = 'Plats'
    location_data['description']['se'] = 'Beskrivning'
    start_datetime = datetime.datetime.utcnow()
    location = parse_import_location(location_data, component)
    _check_location(location_data)

    assert len(logic.locations.get_locations()) == 2    # including parent

    log_entries = get_fed_location_log_entries_for_location(location.id)
    assert len(log_entries) == 1
    assert log_entries[0].type == FedLocationLogEntryType.IMPORT_LOCATION
    assert log_entries[0].component_id == location.component.id
    assert log_entries[0].location_id == location.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_update_location(component):
    old_location_data = deepcopy(LOCATION_DATA)
    start_datetime = datetime.datetime.utcnow()
    old_location = parse_import_location(old_location_data, component)

    location_data = deepcopy(LOCATION_DATA)
    location_data['name'] = {'en': 'Updated Location', 'de': 'Aktualisierter Ort'}
    location_data['description'] = {'en': 'Updated description', 'de': 'Aktualisierte Beschreibung'}
    location_data['parent_location'] = {
        'location_id': 5,
        'component_uuid': UUID_1
    }

    location = parse_import_location(location_data, component)
    _check_location(location_data)

    assert old_location.id == location.id
    assert len(logic.locations.get_locations()) == 3    # including parent / updated parent

    log_entries = get_fed_location_log_entries_for_location(location.id)
    assert len(log_entries) == 2
    assert log_entries[1].type == FedLocationLogEntryType.IMPORT_LOCATION
    assert log_entries[1].component_id == location.component.id
    assert log_entries[1].location_id == location.id
    assert log_entries[1].utc_datetime >= start_datetime
    assert log_entries[1].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].type == FedLocationLogEntryType.UPDATE_LOCATION
    assert log_entries[0].component_id == location.component.id
    assert log_entries[0].location_id == location.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].utc_datetime >= log_entries[1].utc_datetime


def test_parse_location_invalid_data():
    _invalid_component_uuid_test(LOCATION_DATA, parse_location)
    _invalid_id_test(LOCATION_DATA, 'location_id', parse_location)
    _invalid_translation_test(LOCATION_DATA, 'name', parse_location)
    _invalid_translation_test(LOCATION_DATA, 'description', parse_location)
    _invalid_reference_test(LOCATION_DATA, 'parent_location', 'location_id', parse_location)

    assert len(logic.locations.get_locations()) == 0
    assert len(FedLocationLogEntry.query.all()) == 0


def test_import_location_no_name(component):
    location_data = deepcopy(LOCATION_DATA)
    del location_data['name']
    start_datetime = datetime.datetime.utcnow()
    location = parse_import_location(location_data, component)
    _check_location(location_data)

    assert len(logic.locations.get_locations()) == 2    # including parent

    log_entries = get_fed_location_log_entries_for_location(location.id)
    assert len(log_entries) == 1
    assert log_entries[0].type == FedLocationLogEntryType.IMPORT_LOCATION
    assert log_entries[0].component_id == location.component.id
    assert log_entries[0].location_id == location.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_location_no_description(component):
    location_data = deepcopy(LOCATION_DATA)
    del location_data['description']
    start_datetime = datetime.datetime.utcnow()
    location = parse_import_location(location_data, component)
    _check_location(location_data)

    assert len(logic.locations.get_locations()) == 2    # including parent

    log_entries = get_fed_location_log_entries_for_location(location.id)
    assert len(log_entries) == 1
    assert log_entries[0].type == FedLocationLogEntryType.IMPORT_LOCATION
    assert log_entries[0].component_id == location.component.id
    assert log_entries[0].location_id == location.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_location_no_parent_location(component):
    location_data = deepcopy(LOCATION_DATA)
    del location_data['parent_location']
    start_datetime = datetime.datetime.utcnow()
    location = parse_import_location(location_data, component)
    _check_location(location_data)

    assert len(logic.locations.get_locations()) == 1

    log_entries = get_fed_location_log_entries_for_location(location.id)
    assert len(FedLocationLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedLocationLogEntryType.IMPORT_LOCATION
    assert log_entries[0].component_id == location.component.id
    assert log_entries[0].location_id == location.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_location_no_location_type(component):
    location_data = deepcopy(LOCATION_DATA)
    del location_data['location_type']
    start_datetime = datetime.datetime.utcnow()
    location = parse_import_location(location_data, component)
    _check_location(location_data)

    assert len(logic.locations.get_locations()) == 2    # including parent

    log_entries = get_fed_location_log_entries_for_location(location.id)
    assert len(log_entries) == 1
    assert log_entries[0].type == FedLocationLogEntryType.IMPORT_LOCATION
    assert log_entries[0].component_id == location.component.id
    assert log_entries[0].location_id == location.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_locations_check_for_cyclic_dependencies():
    location_data_parent = deepcopy(LOCATION_DATA)
    parsed_parent = parse_location(location_data_parent)

    location_data_child = deepcopy(LOCATION_DATA)
    location_data_child['location_id'] += 1
    location_data_child['parent_location']['location_id'] = location_data_parent['location_id']
    parsed_child = parse_location(location_data_child)

    locations_check_for_cyclic_dependencies({
        (parsed_parent['fed_id'], parsed_parent['component_uuid']): parsed_parent,
        (parsed_child['fed_id'], parsed_child['component_uuid']): parsed_child
    })


def test_locations_check_for_cyclic_dependencies_self_parent():
    location_data = deepcopy(LOCATION_DATA)
    location_data['parent_location']['location_id'] = location_data['location_id']
    parsed_location = parse_location(location_data)

    with pytest.raises(errors.InvalidDataExportError):
        locations_check_for_cyclic_dependencies({
            (parsed_location['fed_id'], parsed_location['component_uuid']): parsed_location
        })


def test_locations_check_for_cyclic_dependencies_cyclic():
    parsed_locations = {}
    location_data_1 = deepcopy(LOCATION_DATA)
    location_data_1['location_id'] = 1
    location_data_1['parent_location']['location_id'] = 2
    parsed_locations[(location_data_1['location_id'], location_data_1['component_uuid'])] = parse_location(location_data_1)
    location_data_2 = deepcopy(LOCATION_DATA)
    location_data_2['location_id'] = 2
    location_data_2['parent_location']['location_id'] = 1
    parsed_locations[(location_data_2['location_id'], location_data_2['component_uuid'])] = parse_location(location_data_2)
    location_data_3 = deepcopy(LOCATION_DATA)
    location_data_3['location_id'] = 3
    location_data_3['parent_location']['location_id'] = 2
    parsed_locations[(location_data_3['location_id'], location_data_3['component_uuid'])] = parse_location(location_data_3)
    location_data_4 = deepcopy(LOCATION_DATA)
    location_data_4['location_id'] = 4
    location_data_4['parent_location']['location_id'] = 3
    parsed_locations[(location_data_4['location_id'], location_data_4['component_uuid'])] = parse_location(location_data_4)

    with pytest.raises(errors.InvalidDataExportError):
        locations_check_for_cyclic_dependencies(parsed_locations)


def test_locations_check_for_cyclic_dependencies_cyclic_including_local_locations(component, user):
    # setting:
    # x -> y: y is parent of x, x is child of y
    # lx: x is a local location, fx: x has been imported from federation
    # l2 -> l1 -> f1
    location_data_1 = deepcopy(LOCATION_DATA)
    location_data_1['location_id'] = 1
    location_data_1['parent_location'] = None
    fed_location_1 = parse_import_location(location_data_1, component)  # f1
    location_1 = create_location(
        name={'en': 'Location 1'},
        description={},
        user_id=user.id,
        parent_location_id=fed_location_1.id,
        type_id=logic.locations.LocationType.LOCATION
    )   # l1
    location_2 = create_location(
        name={'en': 'Location 1'},
        description={},
        user_id=user.id,
        parent_location_id=location_1.id,
        type_id=logic.locations.LocationType.LOCATION
    )   # l2

    # import new location f2, which is child of l2
    # update f1 to be child of f2
    # l2 -> l1 -> f1 -> f2 -> l2
    parsed_locations = {}
    location_data_2 = deepcopy(LOCATION_DATA)
    location_data_2['location_id'] = 2
    location_data_2['parent_location'] = {
        'location_id': location_2.id,
        'component_uuid': flask.current_app.config['FEDERATION_UUID']
    }
    parsed_locations[(location_data_2['location_id'], location_data_2['component_uuid'])] = parse_location(location_data_2)

    location_data_1['parent_location'] = {
        'location_id': location_data_2['location_id'],
        'component_uuid': location_data_2['component_uuid']
    }
    parsed_locations[(location_data_1['location_id'], location_data_1['component_uuid'])] = parse_location(location_data_1)

    with pytest.raises(errors.InvalidDataExportError):
        locations_check_for_cyclic_dependencies(parsed_locations)


def test_import_comment(simple_object, component):
    comment_data = deepcopy(COMMENT_DATA)
    start_datetime = datetime.datetime.utcnow()
    comment = parse_import_comment(comment_data, simple_object, component)
    _check_comment(comment_data)

    assert len(Comment.query.all()) == 1

    log_entries = get_fed_comment_log_entries_for_comment(comment.id)
    assert len(FedCommentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedCommentLogEntryType.IMPORT_COMMENT
    assert log_entries[0].component_id == comment.component.id
    assert log_entries[0].comment_id == comment.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_update_comment(simple_object, component):
    old_comment_data = deepcopy(COMMENT_DATA)
    start_datetime = datetime.datetime.utcnow()
    old_comment = parse_import_comment(old_comment_data, simple_object, component)

    comment_data = deepcopy(COMMENT_DATA)
    comment_data['content'] = 'Updated comment'
    comment_data['utc_datetime'] = '2021-06-03 01:04:54.164552'
    comment_data['user'] = {
        'user_id': 3,
        'component_uuid': UUID_1
    }

    comment = parse_import_comment(comment_data, simple_object, component)
    _check_comment(comment_data)

    assert old_comment.id == comment.id
    assert len(Comment.query.all()) == 1

    log_entries = get_fed_comment_log_entries_for_comment(comment.id)
    assert len(FedCommentLogEntry.query.all()) == 2
    assert len(log_entries) == 2
    assert log_entries[1].type == FedCommentLogEntryType.IMPORT_COMMENT
    assert log_entries[1].component_id == comment.component.id
    assert log_entries[1].comment_id == comment.id
    assert log_entries[1].utc_datetime >= start_datetime
    assert log_entries[1].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].type == FedCommentLogEntryType.UPDATE_COMMENT
    assert log_entries[0].component_id == comment.component.id
    assert log_entries[0].comment_id == comment.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].utc_datetime >= log_entries[1].utc_datetime


def test_parse_comment_invalid_data(simple_object, component):
    def parse_function(data):
        return parse_import_comment(data, simple_object, component)
    _invalid_id_test(COMMENT_DATA, 'comment_id', parse_function)
    _invalid_component_uuid_test(COMMENT_DATA, parse_function)
    _invalid_reference_test(COMMENT_DATA, 'user', 'user_id', parse_function)
    _invalid_str_test(COMMENT_DATA, 'content', parse_function, mandatory=True, allow_empty=False)
    _invalid_datetime_test(COMMENT_DATA, 'utc_datetime', parse_function, mandatory=True)

    assert len(Comment.query.all()) == 0
    assert len(FedCommentLogEntry.query.all()) == 0


def test_import_comment_no_user(simple_object, component):
    comment_data = deepcopy(COMMENT_DATA)
    del comment_data['user']
    start_datetime = datetime.datetime.utcnow()
    comment = parse_import_comment(comment_data, simple_object, component)
    _check_comment(comment_data)

    assert len(Comment.query.all()) == 1

    log_entries = get_fed_comment_log_entries_for_comment(comment.id)
    assert len(FedCommentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedCommentLogEntryType.IMPORT_COMMENT
    assert log_entries[0].component_id == comment.component.id
    assert log_entries[0].comment_id == comment.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_file_url(simple_object, component):
    file_data = deepcopy(FILE_DATA)
    start_datetime = datetime.datetime.utcnow()
    file = parse_import_file(file_data, simple_object, component)
    _check_file(file_data, simple_object.id)

    assert len(File.query.all()) == 1

    log_entries = get_fed_file_log_entries_for_file(file.id, simple_object.object_id)
    assert len(FedFileLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedFileLogEntryType.IMPORT_FILE
    assert log_entries[0].component_id == file.component_id
    assert log_entries[0].file_id == file.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_update_file_url(simple_object, component):
    old_file_data = deepcopy(FILE_DATA)
    start_datetime = datetime.datetime.utcnow()
    old_file = parse_import_file(old_file_data, simple_object, component)

    file_data = deepcopy(FILE_DATA)
    file_data['data'] = {"storage": "url", "url": "https://example.com/file2"}
    file_data['utc_datetime'] = '2021-06-03 01:04:54.164902'
    file_data['user'] = {
        'user_id': 1,
        'component_uuid': UUID_1
    }

    file = parse_import_file(file_data, simple_object, component)
    _check_file(file_data, simple_object.id)

    assert old_file.id == file.id
    assert len(File.query.all()) == 1

    log_entries = get_fed_file_log_entries_for_file(file.id, simple_object.object_id)
    assert len(FedFileLogEntry.query.all()) == 2
    assert len(log_entries) == 2
    assert log_entries[1].type == FedFileLogEntryType.IMPORT_FILE
    assert log_entries[1].component_id == file.component_id
    assert log_entries[1].file_id == file.id
    assert log_entries[1].utc_datetime >= start_datetime
    assert log_entries[1].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].type == FedFileLogEntryType.UPDATE_FILE
    assert log_entries[0].component_id == file.component_id
    assert log_entries[0].file_id == file.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].utc_datetime >= log_entries[1].utc_datetime


def test_parse_file_invalid_data(simple_object, component):
    def parse_function(data):
        return parse_import_file(data, simple_object, component)
    _invalid_id_test(FILE_DATA, 'file_id', parse_function)
    _invalid_component_uuid_test(FILE_DATA, parse_function)
    _invalid_reference_test(FILE_DATA, 'user', 'user_id', parse_function)
    _invalid_dict_test(FILE_DATA, 'data', parse_function)
    _invalid_dict_test(FILE_DATA, 'hidden', parse_function)
    file_data = deepcopy(FILE_DATA)
    del file_data['data']
    # del file_data['hidden']   # hidden equals None in example data
    with pytest.raises(errors.InvalidDataExportError):
        parse_import_file(file_data, simple_object, component)
    _invalid_datetime_test(FILE_DATA, 'utc_datetime', parse_function)

    file_data = deepcopy(FILE_DATA)
    del file_data['utc_datetime']

    with pytest.raises(errors.InvalidDataExportError):
        parse_import_file(file_data, simple_object, component)

    assert len(File.query.all()) == 0
    assert len(FedFileLogEntry.query.all()) == 0


def test_parse_file_no_user(simple_object, component):
    file_data = deepcopy(FILE_DATA)
    del file_data['user']
    start_datetime = datetime.datetime.utcnow()
    file = parse_import_file(file_data, simple_object, component)
    _check_file(file_data, simple_object.id)

    assert len(File.query.all()) == 1

    log_entries = get_fed_file_log_entries_for_file(file.id, simple_object.object_id)
    assert len(FedFileLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedFileLogEntryType.IMPORT_FILE
    assert log_entries[0].component_id == file.component_id
    assert log_entries[0].file_id == file.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_object_location_assignment(simple_object, component):
    assignment_data = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    start_datetime = datetime.datetime.utcnow()
    assignment = parse_import_object_location_assignment(assignment_data, simple_object, component)
    _check_object_location_assignment(assignment_data)

    assert len(ObjectLocationAssignment.query.all()) == 1

    log_entries = get_fed_object_location_assignment_log_entries_for_assignment(assignment.id)
    assert len(FedObjectLocationAssignmentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT
    assert log_entries[0].component_id == assignment.component.id
    assert log_entries[0].object_location_assignment_id == assignment.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_update_object_location_assignment(simple_object, component):
    old_assignment_data = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    start_datetime = datetime.datetime.utcnow()
    old_assignment = parse_import_object_location_assignment(old_assignment_data, simple_object, component)

    assignment_data = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    assignment_data['description'] = {'en': 'Updated description'}
    assignment_data['utc_datetime'] = '2021-06-03 01:04:54.117490'
    assignment_data['user'] = {
        'user_id': 3,
        'component_uuid': UUID_1
    }
    assignment_data['responsible_user'] = {
        'user_id': 4,
        'component_uuid': UUID_1
    }
    assignment_data['location'] = {
        'location_id': 2,
        'component_uuid': UUID_1
    }

    assignment = parse_import_object_location_assignment(assignment_data, simple_object, component)
    _check_object_location_assignment(assignment_data)

    assert old_assignment.id == assignment.id
    assert len(ObjectLocationAssignment.query.all()) == 1

    log_entries = get_fed_object_location_assignment_log_entries_for_assignment(assignment.id)
    assert len(FedObjectLocationAssignmentLogEntry.query.all()) == 2
    assert len(log_entries) == 2
    assert log_entries[1].type == FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT
    assert log_entries[1].component_id == assignment.component.id
    assert log_entries[1].object_location_assignment_id == assignment.id
    assert log_entries[1].utc_datetime >= start_datetime
    assert log_entries[1].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].type == FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT
    assert log_entries[0].component_id == assignment.component.id
    assert log_entries[0].object_location_assignment_id == assignment.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
    assert log_entries[0].utc_datetime >= log_entries[1].utc_datetime


def test_parse_object_location_assignment_invalid_data(simple_object):
    _invalid_component_uuid_test(OBJECT_LOCATION_ASSIGNMENT_DATA, lambda d: parse_import_object_location_assignment(d, simple_object, component))
    _invalid_id_test(OBJECT_LOCATION_ASSIGNMENT_DATA, 'id', lambda d: parse_import_object_location_assignment(d, simple_object, component))

    assignment_data = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    del assignment_data['responsible_user']
    del assignment_data['description']
    del assignment_data['location']
    with pytest.raises(errors.InvalidDataExportError):
        parse_import_object_location_assignment(assignment_data, simple_object, component)

    assignment_data = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    del assignment_data['utc_datetime']
    with pytest.raises(errors.InvalidDataExportError):
        parse_import_object_location_assignment(assignment_data, simple_object, component)

    assert len(logic.locations.get_object_location_assignments(simple_object.id)) == 0
    assert len(FedObjectLocationAssignmentLogEntry.query.all()) == 0


def test_import_object_location_assignment_no_user(simple_object, component):
    assignment_data = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    del assignment_data['user']
    start_datetime = datetime.datetime.utcnow()
    assignment = parse_import_object_location_assignment(assignment_data, simple_object, component)
    _check_object_location_assignment(assignment_data)

    assert len(ObjectLocationAssignment.query.all()) == 1

    log_entries = get_fed_object_location_assignment_log_entries_for_assignment(assignment.id)
    assert len(FedObjectLocationAssignmentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT
    assert log_entries[0].component_id == assignment.component.id
    assert log_entries[0].object_location_assignment_id == assignment.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_object_location_assignment_no_responsible_user(simple_object, component):
    assignment_data = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    del assignment_data['responsible_user']
    start_datetime = datetime.datetime.utcnow()
    assignment = parse_import_object_location_assignment(assignment_data, simple_object, component)
    _check_object_location_assignment(assignment_data)

    assert len(ObjectLocationAssignment.query.all()) == 1

    log_entries = get_fed_object_location_assignment_log_entries_for_assignment(assignment.id)
    assert len(FedObjectLocationAssignmentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT
    assert log_entries[0].component_id == assignment.component.id
    assert log_entries[0].object_location_assignment_id == assignment.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_object_location_assignment_no_location(simple_object, component):
    assignment_data = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    del assignment_data['location']
    start_datetime = datetime.datetime.utcnow()
    assignment = parse_import_object_location_assignment(assignment_data, simple_object, component)
    _check_object_location_assignment(assignment_data)

    assert len(ObjectLocationAssignment.query.all()) == 1

    log_entries = get_fed_object_location_assignment_log_entries_for_assignment(assignment.id)
    assert len(FedObjectLocationAssignmentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT
    assert log_entries[0].component_id == assignment.component.id
    assert log_entries[0].object_location_assignment_id == assignment.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_object_location_assignment_no_description(simple_object, component):
    assignment_data = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    del assignment_data['description']
    start_datetime = datetime.datetime.utcnow()
    assignment = parse_import_object_location_assignment(assignment_data, simple_object, component)
    _check_object_location_assignment(assignment_data)

    assert len(ObjectLocationAssignment.query.all()) == 1

    log_entries = get_fed_object_location_assignment_log_entries_for_assignment(assignment.id)
    assert len(FedObjectLocationAssignmentLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT
    assert log_entries[0].component_id == assignment.component.id
    assert log_entries[0].object_location_assignment_id == assignment.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_shared_object_preprocessor(complex_object, app):
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        policy = {
            'access': {
                'action': True,
                'data': True,
                'users': True,
                'comments': True,
                'files': True,
                'user_data': True,
                'object_location_assignments': True
            }
        }
        refs = []
        markdown_images = {}
        processed_object = shared_object_preprocessor(complex_object.object_id, policy, refs, markdown_images)

        assert processed_object['object_id'] == complex_object.object_id
        assert processed_object['versions'][0]['version_id'] == complex_object.version_id
        assert processed_object['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_object['versions'][0]['data'] == complex_object.data
        assert processed_object['versions'][0]['schema'] == complex_object.schema
        assert processed_object['versions'][0]['utc_datetime'] == complex_object.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
        assert processed_object['policy'] == policy

        assert 'action' in processed_object
        assert processed_object['action']['action_id'] == complex_object.action_id
        assert processed_object['action']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']

        assert 'user' in processed_object['versions'][0]
        assert processed_object['versions'][0]['user']['user_id'] == complex_object.user_id
        assert processed_object['versions'][0]['user']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']

        assert 'comments' in processed_object
        assert len(processed_object['comments']) == 1
        comments = get_comments_for_object(complex_object.object_id)
        assert len(comments) == 1
        comment = comments[0]
        processed_comment = processed_object['comments'][0]
        assert processed_comment['comment_id'] == comment.id
        assert processed_comment['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_comment['content'] == comment.content
        assert processed_comment['utc_datetime'] == comment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
        assert 'user' in processed_comment
        assert processed_comment['user']['user_id'] == comment.user_id
        assert processed_comment['user']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']

        assert 'object_location_assignments' in processed_object
        assert len(processed_object['object_location_assignments']) == 1
        olas = get_object_location_assignments(complex_object.id)
        assert len(olas) == 1
        ola = olas[0]
        processed_ola = processed_object['object_location_assignments'][0]
        assert processed_ola['id'] == ola.id
        assert processed_ola['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_ola['description'] == ola.description
        assert processed_ola['utc_datetime'] == ola.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
        assert processed_ola['confirmed'] == ola.confirmed
        assert 'user' in processed_ola
        assert processed_ola['user']['user_id'] == ola.user_id
        assert processed_ola['user']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert 'responsible_user' in processed_ola
        assert processed_ola['responsible_user']['user_id'] == ola.responsible_user_id
        assert processed_ola['responsible_user']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert 'location' in processed_ola
        assert processed_ola['location']['location_id'] == ola.location_id
        assert processed_ola['location']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']

        assert 'files' in processed_object
        assert len(processed_object['files']) == 1
        files = get_files_for_object(complex_object.id)
        assert len(files) == 1
        file = files[0]
        processed_file = processed_object['files'][0]
        assert processed_file['file_id'] == file.id
        assert processed_file['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_file['data'] == file.data
        assert processed_file['utc_datetime'] == file.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
        assert 'user' in processed_file
        assert processed_file['user']['user_id'] == file.user_id
        assert processed_file['user']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']

        assert len(refs) == 7       # 5 users, 1 location, 1 action

        assert markdown_images == {}


def test_shared_object_preprocessor_array(array_object):
    policy = {
        'access': {
            'action': True,
            'data': True,
            'users': True,
            'comments': True,
            'files': True,
            'user_data': True,
            'object_location_assignments': True
        }
    }
    refs = []
    markdown_images = {}
    processed_object = shared_object_preprocessor(array_object.object_id, policy, refs, markdown_images)

    assert processed_object['object_id'] == array_object.object_id
    assert processed_object['versions'][0]['version_id'] == array_object.version_id
    assert processed_object['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
    assert processed_object['versions'][0]['data'] == array_object.data
    assert processed_object['versions'][0]['schema'] == array_object.schema
    assert processed_object['versions'][0]['utc_datetime'] == array_object.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
    assert processed_object['policy'] == policy


def test_shared_object_preprocessor_array_object(array_object_object):
    policy = {
        'access': {
            'action': True,
            'data': True,
            'users': True,
            'comments': True,
            'files': True,
            'user_data': True,
            'object_location_assignments': True
        }
    }
    refs = []
    markdown_images = {}
    processed_object = shared_object_preprocessor(array_object_object.object_id, policy, refs, markdown_images)
    assert processed_object['object_id'] == array_object_object.object_id
    assert processed_object['versions'][0]['version_id'] == array_object_object.version_id
    assert processed_object['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
    assert processed_object['versions'][0]['data'] == array_object_object.data
    assert processed_object['versions'][0]['schema'] == array_object_object.schema
    assert processed_object['versions'][0]['utc_datetime'] == array_object_object.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
    assert processed_object['policy'] == policy


def test_shared_object_preprocessor_markdown_images(markdown_object, markdown_images, app):
    md0, md1, md2 = markdown_images
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        policy = {
            'access': {
                'action': True,
                'data': True,
                'users': True,
                'comments': True,
                'files': True,
                'user_data': True,
                'object_location_assignments': True
            }
        }
        refs = []
        markdown_images = {}
        processed_object = shared_object_preprocessor(markdown_object.object_id, policy, refs, markdown_images)

        assert processed_object['object_id'] == markdown_object.object_id
        assert processed_object['versions'][0]['version_id'] == markdown_object.version_id
        assert processed_object['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        ref_data = markdown_object.data
        ref_data['comment']['text'] = ref_data['comment']['text'].replace('markdown_images', 'markdown_images/' + flask.current_app.config['FEDERATION_UUID'])
        ref_data['markdown']['text']['en'] = ref_data['markdown']['text']['en'].replace('markdown_images', 'markdown_images/' + flask.current_app.config['FEDERATION_UUID'])
        ref_data['markdown']['text']['de'] = ref_data['markdown']['text']['de'].replace('markdown_images', 'markdown_images/' + flask.current_app.config['FEDERATION_UUID'])
        assert processed_object['versions'][0]['data'] == ref_data
        assert processed_object['versions'][0]['schema'] == markdown_object.schema
        assert processed_object['versions'][0]['utc_datetime'] == markdown_object.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
        assert processed_object['policy'] == policy

        assert markdown_images == {
            md0.file_name: base64.b64encode(md0.content).decode('utf-8'),
            md1.file_name: base64.b64encode(md1.content).decode('utf-8'),
            md2.file_name: base64.b64encode(md2.content).decode('utf-8')
        }


def test_shared_object_preprocessor_modification_insert(complex_object, app):
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        policy = {
            'access': {
                'action': True,
                'data': True,
                'users': True,
                'comments': True,
                'files': True,
                'user_data': True,
                'object_location_assignments': True
            },
            'modification': {
                'insert': {
                    'data': {
                        'license': {
                            '_type': 'text',
                            'text': 'License Text'
                        }
                    },
                    'schema': {
                        'license': {
                            'type': 'text',
                            'title': 'License'
                        }
                    }
                }
            }
        }

        refs = []
        markdown_images = {}
        processed_object = shared_object_preprocessor(complex_object.object_id, policy, refs, markdown_images)
        assert 'license' in processed_object['versions'][0]['data']
        assert processed_object['versions'][0]['data']['license'] == {'_type': 'text', 'text': 'License Text'}
        assert 'license' in processed_object['versions'][0]['schema']['properties']
        assert processed_object['versions'][0]['schema']['properties']['license'] == {'type': 'text', 'title': 'License'}
        del processed_object['versions'][0]['data']['license']
        assert processed_object['versions'][0]['data'] == complex_object.data
        del processed_object['versions'][0]['schema']['properties']['license']
        assert processed_object['versions'][0]['schema'] == complex_object.schema


def test_shared_object_preprocessor_modification_update(complex_object, app):
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        policy = {
            'access': {
                'action': True,
                'data': True,
                'users': True,
                'comments': True,
                'files': True,
                'user_data': True,
                'object_location_assignments': True
            },
            'modification': {
                'update': {
                    'data': {
                        'user': {
                            'user_id': None,
                            'export_edit_note': 'Removed referenced user'
                        }
                    },
                    # TODO schema
                }
            }
        }
        refs = []
        markdown_images = {}
        processed_object = shared_object_preprocessor(complex_object.object_id, policy, refs, markdown_images)

        assert processed_object['versions'][0]['data']['user']['user_id'] is None
        assert processed_object['versions'][0]['data']['user']['export_edit_note'] == 'Removed referenced user'
        del processed_object['versions'][0]['data']['user']
        data = deepcopy(complex_object.data)
        del data['user']
        assert processed_object['versions'][0]['data'] == data


def test_shared_action_preprocessor(action, component, app):
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        type = action.type
        user = action.user
        instrument = action.instrument
        refs = []
        markdown_images = {}
        processed_action = shared_action_preprocessor(action.id, component, refs, markdown_images)

        assert processed_action['action_id'] == action.id
        assert processed_action['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_action['action_type']['action_type_id'] == type.id
        assert processed_action['action_type']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_action['instrument']['instrument_id'] == instrument.id
        assert processed_action['instrument']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_action['user']['user_id'] == user.id
        assert processed_action['user']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_action['schema'] == action.schema
        assert processed_action['description_is_markdown'] == action.description_is_markdown
        assert processed_action['is_hidden'] == action.is_hidden
        assert processed_action['short_description_is_markdown'] == action.short_description_is_markdown

        assert len(processed_action['translations']) == 2
        for key, value in processed_action['translations'].items():
            language_id = get_language_by_lang_code(key).id
            translation = get_action_translation_for_action_in_language(action.id, language_id)
            assert value['name'] == translation.name
            assert value['description'] == translation.description
            assert value['short_description'] == translation.short_description

        assert ('action_types', type.id) in refs
        assert ('users', user.id) in refs
        assert ('instruments', instrument.id) in refs
        assert len(refs) == 3
        assert markdown_images == {}


def test_shared_action_preprocessor_does_not_exist(action, component):
    refs = []
    markdown_images = {}
    with pytest.raises(errors.ActionDoesNotExistError):
        shared_action_preprocessor(action.id + 1, component, refs, markdown_images)

    assert refs == []
    assert markdown_images == {}


def test_shared_action_preprocessor_markdown_images(simple_action, markdown_images, component, app):
    md0, md1, md2 = markdown_images
    simple_action.description_is_markdown = True
    simple_action.short_description_is_markdown = True
    db.session.add(simple_action)
    db.session.commit()
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        set_action_translation(
            get_language_by_lang_code('en').id,
            simple_action.id,
            name='Action',
            description='![image](/markdown_images/' + md0.file_name + ')',
            short_description='![image](/markdown_images/' + md1.file_name + ')'
        )
        set_action_translation(
            get_language_by_lang_code('de').id,
            simple_action.id,
            name='Aktion',
            description='![image](/markdown_images/' + md0.file_name + ')',
            short_description='![image](/markdown_images/' + md2.file_name + ')'
        )

        refs = []
        markdown_images = {}
        processed_action = shared_action_preprocessor(simple_action.id, component, refs, markdown_images)

        assert processed_action['action_id'] == simple_action.id
        assert processed_action['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_action['action_type']['action_type_id'] == simple_action.type_id
        assert processed_action['action_type']['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_action['instrument'] is None
        assert processed_action['user'] is None
        assert processed_action['schema'] == simple_action.schema
        assert processed_action['description_is_markdown'] == simple_action.description_is_markdown
        assert processed_action['is_hidden'] == simple_action.is_hidden
        assert processed_action['short_description_is_markdown'] == simple_action.short_description_is_markdown

        assert len(processed_action['translations']) == 2
        assert processed_action['translations']['en'] == {
            'name': 'Action',
            'description': '![image](/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + md0.file_name + ')',
            'short_description': '![image](/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + md1.file_name + ')'
        }
        assert processed_action['translations']['de'] == {
            'name': 'Aktion',
            'description': '![image](/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + md0.file_name + ')',
            'short_description': '![image](/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + md2.file_name + ')'
        }
        assert refs == [('action_types', simple_action.type_id)]

        assert markdown_images == {
            md0.file_name: base64.b64encode(md0.content).decode('utf-8'),
            md1.file_name: base64.b64encode(md1.content).decode('utf-8'),
            md2.file_name: base64.b64encode(md2.content).decode('utf-8')
        }


def test_shared_action_type_preprocessor(component):
    action_type = get_action_type(-99)
    refs = []
    markdown_images = {}
    processed_action = shared_action_type_preprocessor(action_type.id, component, refs, markdown_images)

    assert processed_action['action_type_id'] == action_type.id
    assert processed_action['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
    assert processed_action['admin_only'] == action_type.admin_only
    assert processed_action['enable_labels'] == action_type.enable_labels
    assert processed_action['enable_files'] == action_type.enable_files
    assert processed_action['enable_locations'] == action_type.enable_locations
    assert processed_action['enable_publications'] == action_type.enable_publications
    assert processed_action['enable_comments'] == action_type.enable_comments
    assert processed_action['enable_activity_log'] == action_type.enable_activity_log
    assert processed_action['enable_related_objects'] == action_type.enable_related_objects
    assert processed_action['enable_project_link'] == action_type.enable_project_link

    assert len(processed_action['translations'])
    for lang_code, value in processed_action['translations'].items():
        assert value['name'] == action_type.name.get(lang_code)
        assert value['description'] == action_type.description.get(lang_code)
        assert value['object_name'] == action_type.object_name.get(lang_code)
        assert value['object_name_plural'] == action_type.object_name_plural.get(lang_code)
        assert value['view_text'] == action_type.view_text.get(lang_code)
        assert value['perform_text'] == action_type.perform_text.get(lang_code)

    assert refs == []
    assert markdown_images == {}


def test_shared_action_type_preprocessor_does_not_exist(component):
    refs = []
    markdown_images = {}

    with pytest.raises(errors.ActionTypeDoesNotExistError):
        shared_action_type_preprocessor(1, component, refs, markdown_images)

    assert refs == []
    assert markdown_images == {}


def test_shared_instrument_preprocessor(instrument, component, app):
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        refs = []
        markdown_images = {}
        processed_instrument = shared_instrument_preprocessor(instrument.id, component, refs, markdown_images)

        assert processed_instrument['instrument_id'] == instrument.id
        assert processed_instrument['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_instrument['description_is_markdown'] == instrument.description_is_markdown
        assert processed_instrument['short_description_is_markdown'] == instrument.short_description_is_markdown
        assert processed_instrument['notes_is_markdown'] == instrument.notes_is_markdown
        assert processed_instrument['is_hidden'] == instrument.is_hidden

        assert len(processed_instrument['translations']) == 2
        for lang_code, value in processed_instrument['translations'].items():
            assert value['name'] == instrument.name.get(lang_code)
            assert value['description'] == instrument.description.get(lang_code)
            assert value['short_description'] == instrument.short_description.get(lang_code)
            assert value['notes'] == instrument.notes.get(lang_code)

        assert refs == []
        assert markdown_images == {}


def test_shared_instrument_preprocessor_markdown_images(component, markdown_images, app):
    md0, md1, md2 = markdown_images
    instrument = Instrument(description_is_markdown=True, short_description_is_markdown=True, notes_is_markdown=True)
    db.session.add(instrument)
    db.session.commit()

    assert instrument.id is not None

    set_instrument_translation(
        language_id=get_language_by_lang_code('en').id,
        instrument_id=instrument.id,
        name='Instrument',
        description='![image](/markdown_images/' + md0.file_name + ')',
        short_description='![image](/markdown_images/' + md1.file_name + ')',
        notes='![image](/markdown_images/' + md2.file_name + ')'
    )

    set_instrument_translation(
        language_id=get_language_by_lang_code('de').id,
        instrument_id=instrument.id,
        name='Instrument',
        description='![image](/markdown_images/' + md0.file_name + ')',
        short_description='![image](/markdown_images/' + md1.file_name + ')',
        notes='![image](/markdown_images/' + md2.file_name + ')'
    )

    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        refs = []
        markdown_images = {}
        processed_instrument = shared_instrument_preprocessor(instrument.id, component, refs, markdown_images)

        assert processed_instrument['instrument_id'] == instrument.id
        assert processed_instrument['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
        assert processed_instrument['description_is_markdown'] == instrument.description_is_markdown
        assert processed_instrument['short_description_is_markdown'] == instrument.short_description_is_markdown
        assert processed_instrument['notes_is_markdown'] == instrument.notes_is_markdown
        assert processed_instrument['is_hidden'] == instrument.is_hidden

        assert len(processed_instrument['translations']) == 2
        assert processed_instrument['translations']['en'] == {
            'name': 'Instrument',
            'description': '![image](/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + md0.file_name + ')',
            'short_description': '![image](/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + md1.file_name + ')',
            'notes': '![image](/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + md2.file_name + ')'
        }
        assert processed_instrument['translations']['de'] == {
            'name': 'Instrument',
            'description': '![image](/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + md0.file_name + ')',
            'short_description': '![image](/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + md1.file_name + ')',
            'notes': '![image](/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + md2.file_name + ')'
        }
        assert refs == []

        assert markdown_images == {
            md0.file_name: base64.b64encode(md0.content).decode('utf-8'),
            md1.file_name: base64.b64encode(md1.content).decode('utf-8'),
            md2.file_name: base64.b64encode(md2.content).decode('utf-8')
        }


def test_shared_instrument_preprocessor_does_not_exist(instrument, component):
    refs = []
    markdown_images = {}

    with pytest.raises(errors.InstrumentDoesNotExistError):
        shared_instrument_preprocessor(instrument.id + 1, component, refs, markdown_images)

    assert refs == []
    assert markdown_images == {}


def test_shared_location_preprocessor(locations, component):
    parent_location, sub_location, _ = locations
    refs = []
    markdown_images = {}
    processed_location = shared_location_preprocessor(sub_location.id, component, refs, markdown_images)

    assert processed_location['location_id'] == sub_location.id
    assert processed_location['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
    assert processed_location['name'] == sub_location.name
    assert processed_location['description'] == sub_location.description

    assert 'parent_location' in processed_location
    assert processed_location['parent_location'].get('location_id') == parent_location.id
    assert processed_location['parent_location'].get('component_uuid') == flask.current_app.config['FEDERATION_UUID']

    assert ('locations', parent_location.id) in refs
    assert ('location_types', logic.locations.LocationType.LOCATION) in refs
    assert len(refs) == 2
    assert markdown_images == {}


def test_shared_location_preprocessor_does_not_exist(component):
    refs = []
    markdown_images = {}

    with pytest.raises(errors.LocationDoesNotExistError):
        shared_location_preprocessor(1, component, refs, markdown_images)

    assert refs == []
    assert markdown_images == {}


def test_shared_user_preprocessor_alias(user_alias_setup):
    user, component, user_alias = user_alias_setup
    refs = []
    markdown_images = {}
    processed_user = shared_user_preprocessor(user.id, component, refs, markdown_images)

    assert processed_user['user_id'] == user.id
    assert processed_user['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
    assert processed_user['name'] == user_alias.name
    assert processed_user['email'] == user_alias.email
    assert processed_user['orcid'] == user_alias.orcid
    assert processed_user['affiliation'] == user_alias.affiliation
    assert refs == []
    assert markdown_images == {}


def test_shared_user_preprocessor_no_alias(user, component):
    refs = []
    markdown_images = {}
    processed_user = shared_user_preprocessor(user.id, component, refs, markdown_images)

    assert processed_user['user_id'] == user.id
    assert processed_user['component_uuid'] == flask.current_app.config['FEDERATION_UUID']
    assert processed_user['name'] is None
    assert processed_user['email'] is None
    assert processed_user['orcid'] is None
    assert processed_user['affiliation'] is None
    assert refs == []
    assert markdown_images == {}


def test_shared_user_preprocessor_different_component(fed_user, component):
    refs = []
    markdown_images = {}
    processed_user = shared_user_preprocessor(fed_user.id, component, refs, markdown_images)

    assert processed_user is None
    assert refs == []
    assert markdown_images == {}


def test_shared_user_preprocessor_does_not_exist(user, component):
    refs = []
    markdown_images = {}

    with pytest.raises(errors.UserDoesNotExistError):
        shared_user_preprocessor(user.id + 1, component, refs, markdown_images)

    assert refs == []
    assert markdown_images == {}


def test_update_shares(component, users, groups, projects):
    local_user1, local_user2, local_user3, _, _, _, _ = users
    local_group1, local_group2, local_group3 = groups
    local_project1, local_project2, local_project3 = projects
    default_action_types = len(ActionType.query.all())

    # objects
    object1_0 = deepcopy(OBJECT_DATA)
    object1_0['object_id'] = 1
    object1_0['versions'][0]['version_id'] = 0
    object1_0['versions'][0]['user']['user_id'] = 1
    object1_1 = deepcopy(OBJECT_DATA)
    object1_1['object_id'] = 1
    object1_1['versions'][0]['version_id'] = 1
    object1_1['versions'][0]['user']['user_id'] = 1
    object2 = deepcopy(OBJECT_DATA)
    object2['object_id'] = 2
    object2['versions'][0]['version_id'] = 0
    object2['versions'][0]['data'] = ARRAY_DATA
    object2['versions'][0]['schema'] = ARRAY_SCHEMA
    object2['versions'][0]['user']['user_id'] = 12
    object2['action']['action_id'] = 6

    # permissions
    object2['policy']['permissions']['users'] = {
        str(local_user1.id): 'read',
        str(local_user2.id): 'write',
        str(local_user3.id): 'grant'
    }
    object2['policy']['permissions']['groups'] = {
        str(local_group1.id): 'read',
        str(local_group2.id): 'write',
        str(local_group3.id): 'grant'
    }
    object2['policy']['permissions']['projects'] = {
        str(local_project1.id): 'read',
        str(local_project2.id): 'write',
        str(local_project3.id): 'grant'
    }

    # locations
    location1 = deepcopy(LOCATION_DATA)
    location1['location_id'] = 1
    location1['parent_location'] = None
    location2 = deepcopy(LOCATION_DATA)
    location2['location_id'] = 2
    location2['name'] = {'en': 'Test Location'}

    # users
    user1 = deepcopy(USER_DATA)
    user1['user_id'] = 1
    user2 = deepcopy(USER_DATA)
    user2['user_id'] = 2
    user2['name'] = 'User 2'
    user3 = deepcopy(USER_DATA)
    user3['user_id'] = 23
    user3['name'] = 'User 23'

    # instruments
    instrument1 = deepcopy(INSTRUMENT_DATA)
    instrument1['instrument_id'] = 1
    instrument2 = deepcopy(INSTRUMENT_DATA)
    instrument2['instrument_id'] = 2
    instrument3 = deepcopy(INSTRUMENT_DATA)
    instrument3['instrument_id'] = 3

    # actions
    action1 = deepcopy(ACTION_DATA)
    action1['action_id'] = 1
    action1['instrument']['instrument_id'] = 1
    action1['user']['user_id'] = 23
    action1['action_type']['action_type_id'] = 1
    action2 = deepcopy(ACTION_DATA)
    action2['action_id'] = 2
    action2['instrument']['instrument_id'] = 12
    action2['action_type']['action_type_id'] = 32
    action2['user']['user_id'] = 12

    # action types
    action_type1 = deepcopy(ACTION_TYPE_DATA)
    action_type1['action_type_id'] = 1
    action_type2 = deepcopy(ACTION_TYPE_DATA)
    action_type2['action_type_id'] = 2

    # comments
    comment1 = deepcopy(COMMENT_DATA)
    comment1['comment_id'] = 1
    comment2 = deepcopy(COMMENT_DATA)
    comment2['comment_id'] = 2
    comment2['user']['user_id'] = 2
    object1_0['comments'] = [comment1, comment2]
    comment3 = deepcopy(COMMENT_DATA)
    comment3['comment_id'] = 3
    comment2['user']['user_id'] = 23
    object2['comments'] = [comment3]

    # files
    file1 = deepcopy(FILE_DATA)
    file1['file_id'] = 1
    file1['user']['user_id'] = 3
    file2 = deepcopy(FILE_DATA)
    file2['file_id'] = 2
    file2['user']['user_id'] = 1
    object2['files'] = [file1, file2]

    # object location assignments
    ola1 = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    ola1['id'] = 1
    ola1['user']['user_id'] = 1
    ola1['responsible_user']['user_id'] = 23
    ola1['location']['location_id'] = 1
    ola2 = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    ola2['id'] = 2
    ola2['user']['user_id'] = 2
    ola2['responsible_user']['user_id'] = 1
    ola2['location']['location_id'] = 99
    object1_0['object_location_assignments'] = [ola1, ola2]
    ola3 = deepcopy(OBJECT_LOCATION_ASSIGNMENT_DATA)
    ola3['id'] = 3
    ola3['user']['user_id'] = 12
    ola3['responsible_user']['user_id'] = 6
    ola3['location']['location_id'] = 2
    object2['object_location_assignments'] = [ola3]

    updates = {
        'objects': [object1_0, object1_1, object2],
        'locations': [location1, location2],
        'users': [user1, user2, user3],
        'instruments': [instrument1, instrument2, instrument3],
        'actions': [action1, action2],
        'action_types': [action_type1, action_type2]
    }

    update_shares(component, updates)

    local_object2 = get_fed_object(2, component.id)
    _check_object(object1_0, component)
    _check_object(object1_1, component)
    _check_object(object2, component)
    _check_location(location1)
    _check_location(location2)
    _check_user(user1)
    _check_user(user2)
    _check_user(user3)
    _check_instrument(instrument1)
    _check_instrument(instrument2)
    _check_instrument(instrument3)
    _check_action(action1)
    _check_action(action2)
    _check_action_type(action_type1)
    _check_action_type(action_type2)
    _check_comment(comment1)
    _check_comment(comment2)
    _check_comment(comment3)
    _check_file(file1, local_object2.object_id)
    _check_file(file2, local_object2.object_id)
    _check_object_location_assignment(ola1)
    _check_object_location_assignment(ola2)
    _check_object_location_assignment(ola3)

    assert len(get_objects()) == 2      # imported: 2
    assert len(Location.query.all()) == 2 + 1       # imported: 2, references: 1
    assert len(User.query.all()) == 3 + 3 + 8       # imported: 3, references: 3, existing: 8
    assert len(Instrument.query.all()) == 3 + 1     # imported: 3, references: 1
    assert len(Action.query.all()) == 2 + 1     # imported: 2, references: 1
    assert len(ActionType.query.all()) == 2 + default_action_types + 1      # imported: 2, references: 1
    assert len(Comment.query.all()) == 3
    assert len(File.query.all()) == 2
    assert len(ObjectLocationAssignment.query.all()) == 3

    user_permissions = get_object_permissions_for_users(local_object2.object_id, False, False, False, False, False)
    assert len(user_permissions) == 3
    assert user_permissions[local_user1.id] == Permissions.READ
    assert user_permissions[local_user2.id] == Permissions.WRITE
    assert user_permissions[local_user3.id] == Permissions.GRANT
    group_permissions = get_object_permissions_for_groups(local_object2.object_id)
    assert len(group_permissions) == 3
    assert group_permissions[local_group1.id] == Permissions.READ
    assert group_permissions[local_group2.id] == Permissions.WRITE
    assert group_permissions[local_group3.id] == Permissions.GRANT
    project_permissions = get_object_permissions_for_projects(local_object2.object_id)
    assert len(project_permissions) == 3
    assert project_permissions[local_project1.id] == Permissions.READ
    assert project_permissions[local_project2.id] == Permissions.WRITE
    assert project_permissions[local_project3.id] == Permissions.GRANT


def test_update_users(component):
    user1 = deepcopy(USER_DATA)
    user1['user_id'] = 1
    user2 = deepcopy(USER_DATA)
    user2['user_id'] = 2
    user2['name'] = 'User 2'
    user3 = deepcopy(USER_DATA)
    user3['user_id'] = 23
    user3['name'] = 'User 23'
    updates = {'users': [user1, user2, user3]}

    update_shares(component, updates)
    _check_user(user1)
    _check_user(user2)
    _check_user(user3)
    assert len(User.query.all()) == 3


def test_import_object_invalid_permission(component, user):
    object_data = deepcopy(OBJECT_DATA)
    object_data['policy']['permissions'] = {'users': {str(user.id): 'bread'}}
    with pytest.raises(errors.InvalidDataExportError):
        parse_import_object(object_data, component)
    object_data['policy']['permissions'] = {'users': {str(user.id): True}}
    with pytest.raises(errors.InvalidDataExportError):
        parse_import_object(object_data, component)
    object_data['policy']['permissions'] = {'users': {str(user.id): 12}}
    with pytest.raises(errors.InvalidDataExportError):
        parse_import_object(object_data, component)


def test_import_object_timestamp(component, user):
    object_data = deepcopy(OBJECT_DATA)
    object_data['versions'][0]['utc_datetime'] = (datetime.datetime.utcnow() + datetime.timedelta(seconds=flask.current_app.config['VALID_TIME_DELTA'] + 300)).strftime('%Y-%m-%d %H:%M:%S.%f')
    with pytest.raises(errors.InvalidDataExportError):
        parse_import_object(object_data, component)
    object_data['versions'][0]['utc_datetime'] = (datetime.datetime.utcnow() + datetime.timedelta(seconds=flask.current_app.config['VALID_TIME_DELTA'] - 150)).strftime('%Y-%m-%d %H:%M:%S.%f')
    parse_import_object(object_data, component)
    _check_object(object_data, component)


def test_import_object_unknown_language(component):
    object_data = deepcopy(OBJECT_DATA)
    object_data['versions'][0]['schema'] = {
        'title': {'en': 'Example', 'se': 'Exempel'},
        'type': 'object',
        'properties': {
            'name': {
                'title': {'en': 'Name', 'se': 'Namn'},
                'type': 'text',
                'placeholder': {'en': 'Name', 'se': 'Namn'},
                'default': {'en': 'Name', 'se': 'Namn'},
                'note': {'en': 'Object name', 'se': 'Objektnamn'},
                'languages': ['en', 'se']
            },
            'choices': {
                'title': {'en': 'Choices', 'se': 'Urval'},
                'type': 'text',
                'default': {'en': 'Option 1', 'se': 'Alternativ 1'},
                'note': {'en': 'Select an entry', 'se': 'Välj en post'},
                'choices': [
                    {'en': 'Option 1', 'se': 'Alternativ 1'},
                    {'en': 'Option 2', 'se': 'Alternativ 2'},
                    {'en': 'Option 3', 'se': 'Alternativ 3'}
                ]
            },
            'textarray': {
                'title': {'en': 'Array', 'se': 'Array'},
                'type': 'array',
                'items': {
                    'title': {'en': 'Text', 'se': 'Text'},
                    'type': 'text',
                    'placeholder': {'en': 'Text', 'se': 'Text'},
                    'default': {'en': 'Text', 'se': 'Text'},
                    'note': {'en': 'Text', 'se': 'Text'},
                    'languages': ['en', 'se']
                }
            },
            'object': {
                'type': 'object',
                'title': {'en': 'Object', 'se': 'Objekt'},
                'properties': {
                    'name': {
                        'title': {'en': 'Name', 'se': 'Namn'},
                        'type': 'text',
                        'placeholder': {'en': 'Name', 'se': 'Namn'},
                        'default': {'en': 'Name', 'se': 'Namn'},
                        'note': {'en': 'Object name', 'se': 'Objektnamn'},
                        'languages': ['en', 'se']
                    }
                }
            }
        },
        'required': ['name']
    }
    object_data['versions'][0]['data'] = {
        'name': {
            'text': {'en': 'Name', 'se': 'Namn'},
            '_type': 'text'
        },
        'choices': {
            'text': {'en': 'Option 1', 'se': 'Alternativ 1'},
            '_type': 'text'
        },
        'textarray': [
            {
                'text': {'en': 'Text 1', 'se': 'Text 1'},
                '_type': 'text'
            },
            {
                'text': {'en': 'Text 2', 'se': 'Text 2'},
                '_type': 'text'
            },
            {
                'text': {'en': 'Text 3', 'se': 'Text 3'},
                '_type': 'text'
            }
        ],
        'object': {
            'name': {
                'text': {'en': 'Name', 'se': 'Namn'},
                '_type': 'text'
            },
        }
    }
    ref_object_data = deepcopy(OBJECT_DATA)
    ref_object_data['versions'][0]['schema'] = {
        'title': {'en': 'Example'},
        'type': 'object',
        'properties': {
            'name': {
                'title': {'en': 'Name'},
                'type': 'text',
                'placeholder': {'en': 'Name'},
                'default': {'en': 'Name'},
                'note': {'en': 'Object name'},
                'languages': ['en']
            },
            'choices': {
                'title': {'en': 'Choices'},
                'type': 'text',
                'default': {'en': 'Option 1'},
                'note': {'en': 'Select an entry'},
                'choices': [
                    {'en': 'Option 1'},
                    {'en': 'Option 2'},
                    {'en': 'Option 3'}
                ]
            },
            'textarray': {
                'title': {'en': 'Array'},
                'type': 'array',
                'items': {
                    'title': {'en': 'Text'},
                    'type': 'text',
                    'placeholder': {'en': 'Text'},
                    'default': {'en': 'Text'},
                    'note': {'en': 'Text'},
                    'languages': ['en']
                }
            },
            'object': {
                'type': 'object',
                'title': {'en': 'Object'},
                'properties': {
                    'name': {
                        'title': {'en': 'Name'},
                        'type': 'text',
                        'placeholder': {'en': 'Name'},
                        'default': {'en': 'Name'},
                        'note': {'en': 'Object name'},
                        'languages': ['en']
                    }
                }
            }
        },
        'required': ['name']
    }
    ref_object_data['versions'][0]['data'] = {
        'name': {
            'text': {'en': 'Name'},
            '_type': 'text'
        },
        'choices': {
            'text': {'en': 'Option 1'},
            '_type': 'text'
        },
        'textarray': [
            {
                'text': {'en': 'Text 1'},
                '_type': 'text'
            },
            {
                'text': {'en': 'Text 2'},
                '_type': 'text'
            },
            {
                'text': {'en': 'Text 3'},
                '_type': 'text'
            }
        ],
        'object': {
            'name': {
                'text': {'en': 'Name'},
                '_type': 'text'
            },
        }
    }
    start_datetime = datetime.datetime.utcnow()
    object = parse_import_object(object_data, component)
    _check_object(ref_object_data, component)

    assert len(get_objects()) == 1

    log_entries = get_fed_object_log_entries_for_object(object.id)
    assert len(FedObjectLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedObjectLogEntryType.IMPORT_OBJECT
    assert log_entries[0].component_id == component.id
    assert log_entries[0].object_id == object.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()


def test_import_action_unknown_language(component):
    action_data = deepcopy(ACTION_DATA)
    action_data['schema'] = {
        'title': {'en': 'Example', 'se': 'Exempel'},
        'type': 'object',
        'properties': {
            'name': {
                'title': {'en': 'Name', 'se': 'Namn'},
                'type': 'text',
                'placeholder': {'en': 'Name', 'se': 'Namn'},
                'default': {'en': 'Name', 'se': 'Namn'},
                'note': {'en': 'Object name', 'se': 'Objektnamn'},
                'languages': ['en', 'se']
            },
            'choices': {
                'title': {'en': 'Choices', 'se': 'Urval'},
                'type': 'text',
                'default': {'en': 'Option 1', 'se': 'Alternativ 1'},
                'note': {'en': 'Select an entry', 'se': 'Välj en post'},
                'choices': [
                    {'en': 'Option 1', 'se': 'Alternativ 1'},
                    {'en': 'Option 2', 'se': 'Alternativ 2'},
                    {'en': 'Option 3', 'se': 'Alternativ 3'}
                ]
            },
            'textarray': {
                'title': {'en': 'Array', 'se': 'Array'},
                'type': 'array',
                'items': {
                    'title': {'en': 'Text', 'se': 'Text'},
                    'type': 'text',
                    'placeholder': {'en': 'Text', 'se': 'Text'},
                    'default': {'en': 'Text', 'se': 'Text'},
                    'note': {'en': 'Text', 'se': 'Text'},
                    'languages': ['en', 'se']
                }
            },
            'object': {
                'type': 'object',
                'title': {'en': 'Object', 'se': 'Objekt'},
                'properties': {
                    'name': {
                        'title': {'en': 'Name', 'se': 'Namn'},
                        'type': 'text',
                        'placeholder': {'en': 'Name', 'se': 'Namn'},
                        'default': {'en': 'Name', 'se': 'Namn'},
                        'note': {'en': 'Object name', 'se': 'Objektnamn'},
                        'languages': ['en', 'se']
                    }
                }
            }
        },
        'required': ['name']
    }
    ref_action_data = deepcopy(ACTION_DATA)
    ref_action_data['schema'] = {
        'title': {'en': 'Example'},
        'type': 'object',
        'properties': {
            'name': {
                'title': {'en': 'Name'},
                'type': 'text',
                'placeholder': {'en': 'Name'},
                'default': {'en': 'Name'},
                'note': {'en': 'Object name'},
                'languages': ['en']
            },
            'choices': {
                'title': {'en': 'Choices'},
                'type': 'text',
                'default': {'en': 'Option 1'},
                'note': {'en': 'Select an entry'},
                'choices': [
                    {'en': 'Option 1'},
                    {'en': 'Option 2'},
                    {'en': 'Option 3'}
                ]
            },
            'textarray': {
                'title': {'en': 'Array'},
                'type': 'array',
                'items': {
                    'title': {'en': 'Text'},
                    'type': 'text',
                    'placeholder': {'en': 'Text'},
                    'default': {'en': 'Text'},
                    'note': {'en': 'Text'},
                    'languages': ['en']
                }
            },
            'object': {
                'type': 'object',
                'title': {'en': 'Object'},
                'properties': {
                    'name': {
                        'title': {'en': 'Name'},
                        'type': 'text',
                        'placeholder': {'en': 'Name'},
                        'default': {'en': 'Name'},
                        'note': {'en': 'Object name'},
                        'languages': ['en']
                    }
                }
            }
        },
        'required': ['name']
    }
    start_datetime = datetime.datetime.utcnow()
    action = parse_import_action(action_data, component)
    _check_action(ref_action_data)

    assert len(actions.get_actions()) == 1

    log_entries = get_fed_action_log_entries_for_action(action.id)
    assert len(FedActionLogEntry.query.all()) == 1
    assert len(log_entries) == 1
    assert log_entries[0].type == FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].component_id == action.component.id
    assert log_entries[0].action_id == action.id
    assert log_entries[0].utc_datetime >= start_datetime
    assert log_entries[0].utc_datetime <= datetime.datetime.utcnow()
