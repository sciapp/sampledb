# coding: utf-8
"""

"""
import datetime
import pytest

from sampledb import db, models
from sampledb.logic import fed_logs, errors
from sampledb.logic.actions import create_action_type
from sampledb.logic.comments import create_comment, get_comment
from sampledb.logic.components import add_component
from sampledb.logic.files import create_url_file
from sampledb.logic.instrument_translations import set_instrument_translation
from sampledb.logic.languages import get_language_by_lang_code
from sampledb.logic.locations import Location, create_fed_assignment
from sampledb.logic.objects import create_object

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
UUID_2 = '1e59c517-bd11-4390-aeb4-971f20b06612'
UUID_3 = 'a0c0725f-850e-492d-8a3b-88c5bc037f02'


@pytest.fixture
def user():
    user = models.User(name='User', email='example@example.com', affiliation='FZJ', type=models.UserType.PERSON)
    db.session.add(user)
    db.session.commit()
    # force attribute refresh
    assert user.id is not None
    return user


@pytest.fixture
def users():
    user1 = models.User(name='User 1', email='example@example.com', affiliation='FZJ', type=models.UserType.PERSON)
    db.session.add(user1)
    db.session.commit()
    user2 = models.User(name='User 2', email='example@example.com', affiliation='FZJ', type=models.UserType.PERSON)
    db.session.add(user2)
    db.session.commit()
    # force attribute refresh
    assert user1.id is not None
    assert user2.id is not None
    return user1, user2


@pytest.fixture
def component():
    component = add_component(address=None, uuid=UUID_1, name='Example component', description='')
    return component


@pytest.fixture
def components():
    component1 = add_component(address=None, uuid=UUID_2, name='Example component 1', description='')
    component2 = add_component(address=None, uuid=UUID_3, name='Example component 2', description='')
    return component1, component2


@pytest.fixture
def action():
    action = models.Action(
        action_type_id=models.ActionType.SAMPLE_CREATION,
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
def actions():
    action1 = models.Action(
        action_type_id=models.ActionType.SAMPLE_CREATION,
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
    action2 = models.Action(
        action_type_id=models.ActionType.SAMPLE_CREATION,
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
    db.session.add(action1)
    db.session.add(action2)
    db.session.commit()
    # force attribute refresh
    assert action1.id is not None
    assert action2.id is not None
    return action1, action2


@pytest.fixture
def object(user, action):
    object = create_object(user_id=user.id, action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    return object


@pytest.fixture
def objects(user, action):
    object1 = create_object(user_id=user.id, action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    object2 = create_object(user_id=user.id, action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    return object1, object2


@pytest.fixture
def location():
    location = models.Location(
        name={
            'en': 'Location'
        },
        description={
            'en': ''
        })
    db.session.add(location)
    db.session.commit()
    return Location.from_database(location)


@pytest.fixture
def locations():
    location1 = models.Location(
        name={
            'en': 'Location 1'
        },
        description={
            'en': ''
        })
    location2 = models.Location(
        name={
            'en': 'Location 2'
        },
        description={
            'en': ''
        })
    db.session.add(location1)
    db.session.add(location2)
    db.session.commit()
    return Location.from_database(location1), Location.from_database(location2)


@pytest.fixture
def action_type():
    action_type = create_action_type(False, True, True, True, True, True, True, True, True, True, True, False, False)
    return action_type


@pytest.fixture
def action_types():
    action_type1 = create_action_type(False, True, True, True, True, True, True, True, True, True, True, False, False)
    action_type2 = create_action_type(False, True, True, True, True, True, True, True, True, True, True, False, False)
    return action_type1, action_type2


@pytest.fixture
def instrument():
    instrument = models.Instrument()
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
def instruments():
    instrument1 = models.Instrument()
    instrument2 = models.Instrument()
    db.session.add(instrument1)
    db.session.add(instrument2)
    db.session.commit()

    assert instrument1.id is not None
    assert instrument2.id is not None

    return instrument1, instrument2


@pytest.fixture
def comment_id(object, user):
    comment_id = create_comment(object.id, user.id, 'Comment')
    return comment_id


@pytest.fixture
def comments(objects, users):
    object1, object2 = objects
    user1, user2 = users
    comment1 = create_comment(object1.id, user1.id, 'Comment 1')
    comment2 = create_comment(object2.id, user2.id, 'Comment')
    comment3 = create_comment(object1.id, user2.id, 'Comment 2')
    return get_comment(comment1), get_comment(comment2), get_comment(comment3)


@pytest.fixture
def file(object, user):
    file = create_url_file(object.id, user.id, 'http://example.com/file')
    return file


@pytest.fixture
def files(objects, users):
    object1, object2 = objects
    user1, user2 = users
    file1 = create_url_file(object1.id, user1.id, 'http://example.com/file1')
    file2 = create_url_file(object2.id, user2.id, 'http://example.com/file2')
    file3 = create_url_file(object1.id, user2.id, 'http://example.com/file3')
    return file1, file2, file3


@pytest.fixture
def object_location_assignment(component, object, location, user):
    object_location_assignment = create_fed_assignment(1, component.id, object.id, location.id, user.id, user.id, {'en': 'Assigned Location'}, None, None)
    return object_location_assignment


@pytest.fixture
def object_location_assignments(components, objects, locations, users):
    object1, object2 = objects
    user1, user2 = users
    location1, location2 = locations
    component1, component2 = components
    object_location_assignment1 = create_fed_assignment(1, component1.id, object1.id, location1.id, user1.id, user1.id, {'en': 'Assigned Location 1'}, None, None)
    object_location_assignment2 = create_fed_assignment(2, component1.id, object2.id, location1.id, user2.id, user2.id, {'en': 'Assigned Location 2'}, None, None)
    object_location_assignment3 = create_fed_assignment(3, component1.id, object1.id, location2.id, user1.id, user2.id, {'en': 'Assigned Location 3'}, None, None)
    return object_location_assignment1, object_location_assignment2, object_location_assignment3


def test_import_user(user, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedUserLogEntry.query.all()) == 0
    fed_logs.import_user(user.id, component.id)
    log_entries = models.FedUserLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedUserLogEntryType.IMPORT_USER
    assert log_entries[0].user_id == user.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_import_user_missing_data(user, component):
    assert len(models.FedUserLogEntry.query.all()) == 0
    with pytest.raises(errors.UserDoesNotExistError):
        fed_logs.import_user(user.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.import_user(user.id, component.id + 1)
    assert len(models.FedUserLogEntry.query.all()) == 0


def test_update_user(user, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedUserLogEntry.query.all()) == 0
    fed_logs.update_user(user.id, component.id)
    log_entries = models.FedUserLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedUserLogEntryType.UPDATE_USER
    assert log_entries[0].user_id == user.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_update_user_missing_data(user, component):
    assert len(models.FedUserLogEntry.query.all()) == 0
    with pytest.raises(errors.UserDoesNotExistError):
        fed_logs.update_user(user.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.update_user(user.id, component.id + 1)
    assert len(models.FedUserLogEntry.query.all()) == 0


def test_create_ref_user(user, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedUserLogEntry.query.all()) == 0
    fed_logs.create_ref_user(user.id, component.id)
    log_entries = models.FedUserLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedUserLogEntryType.CREATE_REF_USER
    assert log_entries[0].user_id == user.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_create_ref_user_missing_data(user, component):
    assert len(models.FedUserLogEntry.query.all()) == 0
    with pytest.raises(errors.UserDoesNotExistError):
        fed_logs.create_ref_user(user.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.create_ref_user(user.id, component.id + 1)
    assert len(models.FedUserLogEntry.query.all()) == 0


def test_import_object(object, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedObjectLogEntry.query.all()) == 0
    fed_logs.import_object(object.id, component.id)
    log_entries = models.FedObjectLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedObjectLogEntryType.IMPORT_OBJECT
    assert log_entries[0].object_id == object.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_import_object_missing_data(object, component):
    assert len(models.FedObjectLogEntry.query.all()) == 0
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.import_object(object.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.import_object(object.id, component.id + 1)
    assert len(models.FedObjectLogEntry.query.all()) == 0


def test_update_object(object, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedObjectLogEntry.query.all()) == 0
    fed_logs.update_object(object.id, component.id)
    log_entries = models.FedObjectLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedObjectLogEntryType.UPDATE_OBJECT
    assert log_entries[0].object_id == object.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_update_object_missing_data(object, component):
    assert len(models.FedObjectLogEntry.query.all()) == 0
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.update_object(object.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.update_object(object.id, component.id + 1)
    assert len(models.FedObjectLogEntry.query.all()) == 0


def test_share_object(object, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedObjectLogEntry.query.all()) == 0
    fed_logs.share_object(object.id, component.id)
    log_entries = models.FedObjectLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedObjectLogEntryType.ADD_POLICY
    assert log_entries[0].object_id == object.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_share_object_missing_data(object, component):
    assert len(models.FedObjectLogEntry.query.all()) == 0
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.share_object(object.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.share_object(object.id, component.id + 1)
    assert len(models.FedObjectLogEntry.query.all()) == 0


def test_update_object_policy(object, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedObjectLogEntry.query.all()) == 0
    fed_logs.update_object_policy(object.id, component.id)
    log_entries = models.FedObjectLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedObjectLogEntryType.UPDATE_OBJECT_POLICY
    assert log_entries[0].object_id == object.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_update_object_policy_missing_data(object, component):
    assert len(models.FedObjectLogEntry.query.all()) == 0
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.update_object_policy(object.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.update_object_policy(object.id, component.id + 1)
    assert len(models.FedObjectLogEntry.query.all()) == 0


def test_import_location(location, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedLocationLogEntry.query.all()) == 0
    fed_logs.import_location(location.id, component.id)
    log_entries = models.FedLocationLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedLocationLogEntryType.IMPORT_LOCATION
    assert log_entries[0].location_id == location.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_import_location_missing_data(location, component):
    assert len(models.FedLocationLogEntry.query.all()) == 0
    with pytest.raises(errors.LocationDoesNotExistError):
        fed_logs.import_location(location.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.import_location(location.id, component.id + 1)
    assert len(models.FedLocationLogEntry.query.all()) == 0


def test_update_location(location, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedLocationLogEntry.query.all()) == 0
    fed_logs.update_location(location.id, component.id)
    log_entries = models.FedLocationLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedLocationLogEntryType.UPDATE_LOCATION
    assert log_entries[0].location_id == location.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_update_location_missing_data(location, component):
    assert len(models.FedLocationLogEntry.query.all()) == 0
    with pytest.raises(errors.LocationDoesNotExistError):
        fed_logs.update_location(location.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.update_location(location.id, component.id + 1)
    assert len(models.FedLocationLogEntry.query.all()) == 0


def test_create_ref_location(location, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedLocationLogEntry.query.all()) == 0
    fed_logs.create_ref_location(location.id, component.id)
    log_entries = models.FedLocationLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedLocationLogEntryType.CREATE_REF_LOCATION
    assert log_entries[0].location_id == location.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_create_ref_location_missing_data(location, component):
    assert len(models.FedLocationLogEntry.query.all()) == 0
    with pytest.raises(errors.LocationDoesNotExistError):
        fed_logs.create_ref_location(location.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.create_ref_location(location.id, component.id + 1)
    assert len(models.FedLocationLogEntry.query.all()) == 0


def test_import_action(action, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedActionLogEntry.query.all()) == 0
    fed_logs.import_action(action.id, component.id)
    log_entries = models.FedActionLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedActionLogEntryType.IMPORT_ACTION
    assert log_entries[0].action_id == action.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_import_action_missing_data(action, component):
    assert len(models.FedActionLogEntry.query.all()) == 0
    with pytest.raises(errors.ActionDoesNotExistError):
        fed_logs.import_action(action.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.import_action(action.id, component.id + 1)
    assert len(models.FedActionLogEntry.query.all()) == 0


def test_update_action(action, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedActionLogEntry.query.all()) == 0
    fed_logs.update_action(action.id, component.id)
    log_entries = models.FedActionLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedActionLogEntryType.UPDATE_ACTION
    assert log_entries[0].action_id == action.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_update_action_missing_data(action, component):
    assert len(models.FedActionLogEntry.query.all()) == 0
    with pytest.raises(errors.ActionDoesNotExistError):
        fed_logs.update_action(action.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.update_action(action.id, component.id + 1)
    assert len(models.FedActionLogEntry.query.all()) == 0


def test_create_ref_action(action, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedActionLogEntry.query.all()) == 0
    fed_logs.create_ref_action(action.id, component.id)
    log_entries = models.FedActionLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedActionLogEntryType.CREATE_REF_ACTION
    assert log_entries[0].action_id == action.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_create_ref_action_missing_data(action, component):
    assert len(models.FedActionLogEntry.query.all()) == 0
    with pytest.raises(errors.ActionDoesNotExistError):
        fed_logs.create_ref_action(action.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.create_ref_action(action.id, component.id + 1)
    assert len(models.FedActionLogEntry.query.all()) == 0


def test_import_action_type(action_type, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedActionTypeLogEntry.query.all()) == 0
    fed_logs.import_action_type(action_type.id, component.id)
    log_entries = models.FedActionTypeLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedActionTypeLogEntryType.IMPORT_ACTION_TYPE
    assert log_entries[0].action_type_id == action_type.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_import_action_type_missing_data(action_type, component):
    assert len(models.FedActionTypeLogEntry.query.all()) == 0
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        fed_logs.import_action_type(action_type.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.import_action_type(action_type.id, component.id + 1)
    assert len(models.FedActionTypeLogEntry.query.all()) == 0


def test_update_action_type(action_type, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedActionTypeLogEntry.query.all()) == 0
    fed_logs.update_action_type(action_type.id, component.id)
    log_entries = models.FedActionTypeLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedActionTypeLogEntryType.UPDATE_ACTION_TYPE
    assert log_entries[0].action_type_id == action_type.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_update_action_type_missing_data(action_type, component):
    assert len(models.FedActionTypeLogEntry.query.all()) == 0
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        fed_logs.update_action_type(action_type.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.update_action_type(action_type.id, component.id + 1)
    assert len(models.FedActionTypeLogEntry.query.all()) == 0


def test_create_ref_action_type(action_type, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedActionTypeLogEntry.query.all()) == 0
    fed_logs.create_ref_action_type(action_type.id, component.id)
    log_entries = models.FedActionTypeLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedActionTypeLogEntryType.CREATE_REF_ACTION_TYPE
    assert log_entries[0].action_type_id == action_type.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_create_ref_action_type_missing_data(action_type, component):
    assert len(models.FedActionTypeLogEntry.query.all()) == 0
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        fed_logs.create_ref_action_type(action_type.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.create_ref_action_type(action_type.id, component.id + 1)
    assert len(models.FedActionTypeLogEntry.query.all()) == 0


def test_import_instrument(instrument, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedInstrumentLogEntry.query.all()) == 0
    fed_logs.import_instrument(instrument.id, component.id)
    log_entries = models.FedInstrumentLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedInstrumentLogEntryType.IMPORT_INSTRUMENT
    assert log_entries[0].instrument_id == instrument.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_import_instrument_missing_data(instrument, component):
    assert len(models.FedInstrumentLogEntry.query.all()) == 0
    with pytest.raises(errors.InstrumentDoesNotExistError):
        fed_logs.import_instrument(instrument.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.import_instrument(instrument.id, component.id + 1)
    assert len(models.FedInstrumentLogEntry.query.all()) == 0


def test_update_instrument(instrument, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedInstrumentLogEntry.query.all()) == 0
    fed_logs.update_instrument(instrument.id, component.id)
    log_entries = models.FedInstrumentLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedInstrumentLogEntryType.UPDATE_INSTRUMENT
    assert log_entries[0].instrument_id == instrument.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_update_instrument_missing_data(instrument, component):
    assert len(models.FedInstrumentLogEntry.query.all()) == 0
    with pytest.raises(errors.InstrumentDoesNotExistError):
        fed_logs.update_instrument(instrument.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.update_instrument(instrument.id, component.id + 1)
    assert len(models.FedInstrumentLogEntry.query.all()) == 0


def test_create_ref_instrument(instrument, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedInstrumentLogEntry.query.all()) == 0
    fed_logs.create_ref_instrument(instrument.id, component.id)
    log_entries = models.FedInstrumentLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedInstrumentLogEntryType.CREATE_REF_INSTRUMENT
    assert log_entries[0].instrument_id == instrument.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_create_ref_instrument_missing_data(instrument, component):
    assert len(models.FedInstrumentLogEntry.query.all()) == 0
    with pytest.raises(errors.InstrumentDoesNotExistError):
        fed_logs.create_ref_instrument(instrument.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.create_ref_instrument(instrument.id, component.id + 1)
    assert len(models.FedInstrumentLogEntry.query.all()) == 0


def test_import_comment(comment_id, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedCommentLogEntry.query.all()) == 0
    fed_logs.import_comment(comment_id, component.id)
    log_entries = models.FedCommentLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedCommentLogEntryType.IMPORT_COMMENT
    assert log_entries[0].comment_id == comment_id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_import_comment_missing_data(comment_id, component):
    assert len(models.FedCommentLogEntry.query.all()) == 0
    with pytest.raises(errors.CommentDoesNotExistError):
        fed_logs.import_comment(comment_id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.import_comment(comment_id, component.id + 1)
    assert len(models.FedCommentLogEntry.query.all()) == 0


def test_update_comment(comment_id, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedCommentLogEntry.query.all()) == 0
    fed_logs.update_comment(comment_id, component.id)
    log_entries = models.FedCommentLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedCommentLogEntryType.UPDATE_COMMENT
    assert log_entries[0].comment_id == comment_id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_update_comment_missing_data(comment_id, component):
    assert len(models.FedCommentLogEntry.query.all()) == 0
    with pytest.raises(errors.CommentDoesNotExistError):
        fed_logs.update_comment(comment_id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.update_comment(comment_id, component.id + 1)
    assert len(models.FedCommentLogEntry.query.all()) == 0


def test_import_file(file, object, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedFileLogEntry.query.all()) == 0
    fed_logs.import_file(file.id, object.object_id, component.id)
    log_entries = models.FedFileLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedFileLogEntryType.IMPORT_FILE
    assert log_entries[0].file_id == file.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_import_file_missing_data(file, object, component):
    assert len(models.FedFileLogEntry.query.all()) == 0
    with pytest.raises(errors.FileDoesNotExistError):
        fed_logs.import_file(file.id + 1, object.object_id, component.id)
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.import_file(file.id, object.object_id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.import_file(file.id, object.object_id, component.id + 1)
    assert len(models.FedFileLogEntry.query.all()) == 0


def test_update_file(file, object, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedFileLogEntry.query.all()) == 0
    fed_logs.update_file(file.id, object.object_id, component.id)
    log_entries = models.FedFileLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedFileLogEntryType.UPDATE_FILE
    assert log_entries[0].file_id == file.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_update_file_missing_data(file, object, component):
    assert len(models.FedFileLogEntry.query.all()) == 0
    with pytest.raises(errors.FileDoesNotExistError):
        fed_logs.update_file(file.id + 1, object.object_id, component.id)
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.update_file(file.id, object.object_id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.update_file(file.id, object.object_id, component.id + 1)
    assert len(models.FedFileLogEntry.query.all()) == 0


def test_import_object_location_assignment(object_location_assignment, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedObjectLocationAssignmentLogEntry.query.all()) == 0
    fed_logs.import_object_location_assignment(object_location_assignment.id, component.id)
    log_entries = models.FedObjectLocationAssignmentLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT
    assert log_entries[0].object_location_assignment_id == object_location_assignment.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_import_object_location_assignment_missing_data(object_location_assignment, component):
    assert len(models.FedObjectLocationAssignmentLogEntry.query.all()) == 0
    with pytest.raises(errors.ObjectLocationAssignmentDoesNotExistError):
        fed_logs.import_object_location_assignment(object_location_assignment.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.import_object_location_assignment(object_location_assignment.id, component.id + 1)
    assert len(models.FedObjectLocationAssignmentLogEntry.query.all()) == 0


def test_update_object_location_assignment(object_location_assignment, component):
    start_time = datetime.datetime.utcnow()
    assert len(models.FedObjectLocationAssignmentLogEntry.query.all()) == 0
    fed_logs.update_object_location_assignment(object_location_assignment.id, component.id)
    log_entries = models.FedObjectLocationAssignmentLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].type == models.FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT
    assert log_entries[0].object_location_assignment_id == object_location_assignment.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].data == {}
    assert log_entries[0].utc_datetime >= start_time
    assert log_entries[0].utc_datetime < datetime.datetime.utcnow()


def test_update_object_location_assignment_missing_data(object_location_assignment, component):
    assert len(models.FedObjectLocationAssignmentLogEntry.query.all()) == 0
    with pytest.raises(errors.ObjectLocationAssignmentDoesNotExistError):
        fed_logs.update_object_location_assignment(object_location_assignment.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.update_object_location_assignment(object_location_assignment.id, component.id + 1)
    assert len(models.FedObjectLocationAssignmentLogEntry.query.all()) == 0


def test_get_fed_user_log_entries_for_user(users, components):
    user1, user2 = users
    component1, component2 = components
    entry1 = models.FedUserLogEntry(
        type=models.FedUserLogEntryType.UPDATE_USER,
        user_id=user1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedUserLogEntry(
        type=models.FedUserLogEntryType.UPDATE_USER,
        user_id=user1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedUserLogEntry(
        type=models.FedUserLogEntryType.IMPORT_USER,
        user_id=user1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedUserLogEntry(
        type=models.FedUserLogEntryType.IMPORT_USER,
        user_id=user2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_user_log_entries_for_user(user1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_user_log_entries_for_user(user1.id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_user_log_entries_for_user_missing_data(user, component):
    entry = models.FedUserLogEntry(type=models.FedUserLogEntryType.UPDATE_USER, user_id=user.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.UserDoesNotExistError):
        fed_logs.get_fed_user_log_entries_for_user(user.id + 1)
    with pytest.raises(errors.UserDoesNotExistError):
        fed_logs.get_fed_user_log_entries_for_user(user.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_user_log_entries_for_user(user.id, component.id + 1)


def test_get_fed_user_log_entries_for_component(users, components):
    user1, user2 = users
    component1, component2 = components
    entry1 = models.FedUserLogEntry(
        type=models.FedUserLogEntryType.UPDATE_USER,
        user_id=user1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedUserLogEntry(
        type=models.FedUserLogEntryType.UPDATE_USER,
        user_id=user1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedUserLogEntry(
        type=models.FedUserLogEntryType.IMPORT_USER,
        user_id=user1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedUserLogEntry(
        type=models.FedUserLogEntryType.IMPORT_USER,
        user_id=user2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=3)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_user_log_entries_for_component(component1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry4

    fed_log_entries = fed_logs.get_fed_user_log_entries_for_component(component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_user_log_entries_for_component_missing_data(user, component):
    entry = models.FedUserLogEntry(type=models.FedUserLogEntryType.UPDATE_USER, user_id=user.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_user_log_entries_for_component(component.id + 1)


def test_get_fed_object_log_entries_for_object(objects, components):
    object1, object2 = objects
    component1, component2 = components
    entry1 = models.FedObjectLogEntry(
        type=models.FedObjectLogEntryType.UPDATE_OBJECT,
        object_id=object1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedObjectLogEntry(
        type=models.FedObjectLogEntryType.UPDATE_OBJECT,
        object_id=object1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedObjectLogEntry(
        type=models.FedObjectLogEntryType.IMPORT_OBJECT,
        object_id=object1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedObjectLogEntry(
        type=models.FedObjectLogEntryType.IMPORT_OBJECT,
        object_id=object2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_object_log_entries_for_object(object1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_object_log_entries_for_object(object1.id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_object_log_entries_for_object_missing_data(object, component):
    entry = models.FedObjectLogEntry(type=models.FedObjectLogEntryType.UPDATE_OBJECT, object_id=object.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.get_fed_object_log_entries_for_object(object.id + 1)
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.get_fed_object_log_entries_for_object(object.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_object_log_entries_for_object(object.id, component.id + 1)


def test_get_fed_object_log_entries_for_component(objects, components):
    object1, object2 = objects
    component1, component2 = components
    entry1 = models.FedObjectLogEntry(
        type=models.FedObjectLogEntryType.UPDATE_OBJECT,
        object_id=object1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedObjectLogEntry(
        type=models.FedObjectLogEntryType.UPDATE_OBJECT,
        object_id=object1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedObjectLogEntry(
        type=models.FedObjectLogEntryType.IMPORT_OBJECT,
        object_id=object1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedObjectLogEntry(
        type=models.FedObjectLogEntryType.IMPORT_OBJECT,
        object_id=object2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=3)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_object_log_entries_for_component(component1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry4

    fed_log_entries = fed_logs.get_fed_object_log_entries_for_component(component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_object_log_entries_for_component_missing_data(object, component):
    entry = models.FedObjectLogEntry(type=models.FedObjectLogEntryType.UPDATE_OBJECT, object_id=object.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_object_log_entries_for_component(component.id + 1)


def test_get_fed_location_log_entries_for_location(locations, components):
    location1, location2 = locations
    component1, component2 = components
    entry1 = models.FedLocationLogEntry(
        type=models.FedLocationLogEntryType.UPDATE_LOCATION,
        location_id=location1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedLocationLogEntry(
        type=models.FedLocationLogEntryType.UPDATE_LOCATION,
        location_id=location1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedLocationLogEntry(
        type=models.FedLocationLogEntryType.IMPORT_LOCATION,
        location_id=location1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedLocationLogEntry(
        type=models.FedLocationLogEntryType.IMPORT_LOCATION,
        location_id=location2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_location_log_entries_for_location(location1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_location_log_entries_for_location(location1.id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_location_log_entries_for_location_missing_data(location, component):
    entry = models.FedLocationLogEntry(type=models.FedLocationLogEntryType.UPDATE_LOCATION, location_id=location.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.LocationDoesNotExistError):
        fed_logs.get_fed_location_log_entries_for_location(location.id + 1)
    with pytest.raises(errors.LocationDoesNotExistError):
        fed_logs.get_fed_location_log_entries_for_location(location.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_location_log_entries_for_location(location.id, component.id + 1)


def test_get_fed_location_log_entries_for_component(locations, components):
    location1, location2 = locations
    component1, component2 = components
    entry1 = models.FedLocationLogEntry(
        type=models.FedLocationLogEntryType.UPDATE_LOCATION,
        location_id=location1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedLocationLogEntry(
        type=models.FedLocationLogEntryType.UPDATE_LOCATION,
        location_id=location1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedLocationLogEntry(
        type=models.FedLocationLogEntryType.IMPORT_LOCATION,
        location_id=location1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedLocationLogEntry(
        type=models.FedLocationLogEntryType.IMPORT_LOCATION,
        location_id=location2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=3)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_location_log_entries_for_component(component1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry4

    fed_log_entries = fed_logs.get_fed_location_log_entries_for_component(component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_location_log_entries_for_component_missing_data(location, component):
    entry = models.FedLocationLogEntry(type=models.FedLocationLogEntryType.UPDATE_LOCATION, location_id=location.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_location_log_entries_for_component(component.id + 1)


def test_get_fed_action_log_entries_for_action(actions, components):
    action1, action2 = actions
    component1, component2 = components
    entry1 = models.FedActionLogEntry(
        type=models.FedActionLogEntryType.UPDATE_ACTION,
        action_id=action1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedActionLogEntry(
        type=models.FedActionLogEntryType.UPDATE_ACTION,
        action_id=action1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedActionLogEntry(
        type=models.FedActionLogEntryType.IMPORT_ACTION,
        action_id=action1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedActionLogEntry(
        type=models.FedActionLogEntryType.IMPORT_ACTION,
        action_id=action2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_action_log_entries_for_action(action1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_action_log_entries_for_action(action1.id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_action_log_entries_for_action_missing_data(action, component):
    entry = models.FedActionLogEntry(type=models.FedActionLogEntryType.UPDATE_ACTION, action_id=action.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ActionDoesNotExistError):
        fed_logs.get_fed_action_log_entries_for_action(action.id + 1)
    with pytest.raises(errors.ActionDoesNotExistError):
        fed_logs.get_fed_action_log_entries_for_action(action.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_action_log_entries_for_action(action.id, component.id + 1)


def test_get_fed_action_log_entries_for_component(actions, components):
    action1, action2 = actions
    component1, component2 = components
    entry1 = models.FedActionLogEntry(
        type=models.FedActionLogEntryType.UPDATE_ACTION,
        action_id=action1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedActionLogEntry(
        type=models.FedActionLogEntryType.UPDATE_ACTION,
        action_id=action1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedActionLogEntry(
        type=models.FedActionLogEntryType.IMPORT_ACTION,
        action_id=action1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedActionLogEntry(
        type=models.FedActionLogEntryType.IMPORT_ACTION,
        action_id=action2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=3)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_action_log_entries_for_component(component1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry4

    fed_log_entries = fed_logs.get_fed_action_log_entries_for_component(component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_action_log_entries_for_component_missing_data(action, component):
    entry = models.FedActionLogEntry(type=models.FedActionLogEntryType.UPDATE_ACTION, action_id=action.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_action_log_entries_for_component(component.id + 1)


def test_get_fed_action_type_log_entries_for_action_type(action_types, components):
    action_type1, action_type2 = action_types
    component1, component2 = components
    entry1 = models.FedActionTypeLogEntry(
        type=models.FedActionTypeLogEntryType.UPDATE_ACTION_TYPE,
        action_type_id=action_type1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedActionTypeLogEntry(
        type=models.FedActionTypeLogEntryType.UPDATE_ACTION_TYPE,
        action_type_id=action_type1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedActionTypeLogEntry(
        type=models.FedActionTypeLogEntryType.IMPORT_ACTION_TYPE,
        action_type_id=action_type1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedActionTypeLogEntry(
        type=models.FedActionTypeLogEntryType.IMPORT_ACTION_TYPE,
        action_type_id=action_type2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_action_type_log_entries_for_action_type(action_type1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_action_type_log_entries_for_action_type(action_type1.id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_action_type_log_entries_for_action_type_missing_data(action_type, component):
    entry = models.FedActionTypeLogEntry(type=models.FedActionTypeLogEntryType.UPDATE_ACTION_TYPE, action_type_id=action_type.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        fed_logs.get_fed_action_type_log_entries_for_action_type(action_type.id + 1)
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        fed_logs.get_fed_action_type_log_entries_for_action_type(action_type.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_action_type_log_entries_for_action_type(action_type.id, component.id + 1)


def test_get_fed_action_type_log_entries_for_component(action_types, components):
    action_type1, action_type2 = action_types
    component1, component2 = components
    entry1 = models.FedActionTypeLogEntry(
        type=models.FedActionTypeLogEntryType.UPDATE_ACTION_TYPE,
        action_type_id=action_type1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedActionTypeLogEntry(
        type=models.FedActionTypeLogEntryType.UPDATE_ACTION_TYPE,
        action_type_id=action_type1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedActionTypeLogEntry(
        type=models.FedActionTypeLogEntryType.IMPORT_ACTION_TYPE,
        action_type_id=action_type1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedActionTypeLogEntry(
        type=models.FedActionTypeLogEntryType.IMPORT_ACTION_TYPE,
        action_type_id=action_type2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=3)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_action_type_log_entries_for_component(component1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry4

    fed_log_entries = fed_logs.get_fed_action_type_log_entries_for_component(component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_action_type_log_entries_for_component_missing_data(action_type, component):
    entry = models.FedActionTypeLogEntry(type=models.FedActionTypeLogEntryType.UPDATE_ACTION_TYPE, action_type_id=action_type.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_action_type_log_entries_for_component(component.id + 1)


def test_get_fed_instrument_log_entries_for_instrument(instruments, components):
    instrument1, instrument2 = instruments
    component1, component2 = components
    entry1 = models.FedInstrumentLogEntry(
        type=models.FedInstrumentLogEntryType.UPDATE_INSTRUMENT,
        instrument_id=instrument1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedInstrumentLogEntry(
        type=models.FedInstrumentLogEntryType.UPDATE_INSTRUMENT,
        instrument_id=instrument1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedInstrumentLogEntry(
        type=models.FedInstrumentLogEntryType.IMPORT_INSTRUMENT,
        instrument_id=instrument1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedInstrumentLogEntry(
        type=models.FedInstrumentLogEntryType.IMPORT_INSTRUMENT,
        instrument_id=instrument2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_instrument_log_entries_for_instrument(instrument1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_instrument_log_entries_for_instrument(instrument1.id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_instrument_log_entries_for_instrument_missing_data(instrument, component):
    entry = models.FedInstrumentLogEntry(type=models.FedInstrumentLogEntryType.UPDATE_INSTRUMENT, instrument_id=instrument.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.InstrumentDoesNotExistError):
        fed_logs.get_fed_instrument_log_entries_for_instrument(instrument.id + 1)
    with pytest.raises(errors.InstrumentDoesNotExistError):
        fed_logs.get_fed_instrument_log_entries_for_instrument(instrument.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_instrument_log_entries_for_instrument(instrument.id, component.id + 1)


def test_get_fed_instrument_log_entries_for_component(instruments, components):
    instrument1, instrument2 = instruments
    component1, component2 = components
    entry1 = models.FedInstrumentLogEntry(
        type=models.FedInstrumentLogEntryType.UPDATE_INSTRUMENT,
        instrument_id=instrument1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedInstrumentLogEntry(
        type=models.FedInstrumentLogEntryType.UPDATE_INSTRUMENT,
        instrument_id=instrument1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedInstrumentLogEntry(
        type=models.FedInstrumentLogEntryType.IMPORT_INSTRUMENT,
        instrument_id=instrument1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedInstrumentLogEntry(
        type=models.FedInstrumentLogEntryType.IMPORT_INSTRUMENT,
        instrument_id=instrument2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=3)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_instrument_log_entries_for_component(component1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry4

    fed_log_entries = fed_logs.get_fed_instrument_log_entries_for_component(component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_instrument_log_entries_for_component_missing_data(instrument, component):
    entry = models.FedInstrumentLogEntry(type=models.FedInstrumentLogEntryType.UPDATE_INSTRUMENT, instrument_id=instrument.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_instrument_log_entries_for_component(component.id + 1)


def test_get_fed_comment_log_entries_for_comment(comments, components):
    comment1, comment2, _ = comments
    component1, component2 = components
    entry1 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.UPDATE_COMMENT,
        comment_id=comment1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.UPDATE_COMMENT,
        comment_id=comment1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.IMPORT_COMMENT,
        comment_id=comment1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.IMPORT_COMMENT,
        comment_id=comment2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_comment_log_entries_for_comment(comment1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_comment_log_entries_for_comment(comment1.id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_comment_log_entries_for_comment_missing_data(comment_id, component):
    entry = models.FedCommentLogEntry(type=models.FedCommentLogEntryType.UPDATE_COMMENT, comment_id=comment_id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.CommentDoesNotExistError):
        fed_logs.get_fed_comment_log_entries_for_comment(comment_id + 1)
    with pytest.raises(errors.CommentDoesNotExistError):
        fed_logs.get_fed_comment_log_entries_for_comment(comment_id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_comment_log_entries_for_comment(comment_id, component.id + 1)


def test_get_fed_comment_log_entries_for_component(comments, components):
    comment1, comment2, _ = comments
    component1, component2 = components
    entry1 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.UPDATE_COMMENT,
        comment_id=comment1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.UPDATE_COMMENT,
        comment_id=comment1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.IMPORT_COMMENT,
        comment_id=comment1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.IMPORT_COMMENT,
        comment_id=comment2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=3)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_comment_log_entries_for_component(component1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry4

    fed_log_entries = fed_logs.get_fed_comment_log_entries_for_component(component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_comment_log_entries_for_component_missing_data(comment_id, component):
    entry = models.FedCommentLogEntry(type=models.FedCommentLogEntryType.UPDATE_COMMENT, comment_id=comment_id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_comment_log_entries_for_component(component.id + 1)


def test_get_fed_comment_log_entries_for_object(comments, components):
    comment1, comment2, comment3 = comments
    # comment1 and comment3 -> object1, comment2 -> object2
    component1, component2 = components
    object_id = comment1.object_id
    entry1 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.IMPORT_COMMENT,
        comment_id=comment3.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.UPDATE_COMMENT,
        comment_id=comment1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.IMPORT_COMMENT,
        comment_id=comment1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedCommentLogEntry(
        type=models.FedCommentLogEntryType.IMPORT_COMMENT,
        comment_id=comment2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_comment_log_entries_for_object(object_id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_comment_log_entries_for_object(object_id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_comment_log_entries_for_object_missing_data(comments, component):
    object_id = comments[0].object_id
    invalid_object_id = max((c.object_id for c in comments)) + 1
    comment_id = comments[0].id
    entry = models.FedCommentLogEntry(type=models.FedCommentLogEntryType.UPDATE_COMMENT, comment_id=comment_id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.get_fed_comment_log_entries_for_object(invalid_object_id)
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.get_fed_comment_log_entries_for_object(invalid_object_id, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_comment_log_entries_for_object(object_id, component.id + 1)


def test_get_fed_file_log_entries_for_file(files, components):
    file1, file2, _ = files
    component1, component2 = components
    entry1 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.UPDATE_FILE,
        file_id=file1.id, object_id=file1.object_id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.UPDATE_FILE,
        file_id=file1.id, object_id=file1.object_id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.IMPORT_FILE,
        file_id=file1.id, object_id=file1.object_id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.IMPORT_FILE,
        file_id=file2.id, object_id=file2.object_id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_file_log_entries_for_file(file1.id, file1.object_id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_file_log_entries_for_file(file1.id, file1.object_id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_file_log_entries_for_file_missing_data(file, component):
    entry = models.FedFileLogEntry(type=models.FedFileLogEntryType.UPDATE_FILE, file_id=file.id, object_id=file.object_id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.FileDoesNotExistError):
        fed_logs.get_fed_file_log_entries_for_file(file.id + 1, file.object_id)
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.get_fed_file_log_entries_for_file(file.id, file.object_id + 1)
    with pytest.raises(errors.FileDoesNotExistError):
        fed_logs.get_fed_file_log_entries_for_file(file.id + 1, file.object_id, component.id)
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.get_fed_file_log_entries_for_file(file.id, file.object_id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_file_log_entries_for_file(file.id, file.object_id, component.id + 1)


def test_get_fed_file_log_entries_for_component(files, components):
    file1, file2, _ = files
    component1, component2 = components
    entry1 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.UPDATE_FILE,
        file_id=file1.id, object_id=file1.object_id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.UPDATE_FILE,
        file_id=file1.id, object_id=file1.object_id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.IMPORT_FILE,
        file_id=file1.id, object_id=file1.object_id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.IMPORT_FILE,
        file_id=file2.id, object_id=file2.object_id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=3)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_file_log_entries_for_component(component1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry4

    fed_log_entries = fed_logs.get_fed_file_log_entries_for_component(component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_file_log_entries_for_component_missing_data(file, component):
    entry = models.FedFileLogEntry(type=models.FedFileLogEntryType.UPDATE_FILE, file_id=file.id, object_id=file.object_id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_file_log_entries_for_component(component.id + 1)


def test_get_fed_file_log_entries_for_object(files, components):
    file1, file2, file3 = files
    # file1 and file3 -> object1, file2 -> object2
    component1, component2 = components
    object_id = file1.object_id
    entry1 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.IMPORT_FILE,
        file_id=file3.id, object_id=file3.object_id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.UPDATE_FILE,
        file_id=file1.id, object_id=file1.object_id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.IMPORT_FILE,
        file_id=file1.id, object_id=file1.object_id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedFileLogEntry(
        type=models.FedFileLogEntryType.IMPORT_FILE,
        file_id=file2.id, object_id=file2.object_id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_file_log_entries_for_object(object_id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_file_log_entries_for_object(object_id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_file_log_entries_for_object_missing_data(files, component):
    object_id = files[0].object_id
    invalid_object_id = max((c.object_id for c in files)) + 1
    file_id = files[0].id
    entry = models.FedFileLogEntry(type=models.FedFileLogEntryType.UPDATE_FILE, file_id=file_id, object_id=object_id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.get_fed_file_log_entries_for_object(invalid_object_id)
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.get_fed_file_log_entries_for_object(invalid_object_id, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_file_log_entries_for_object(object_id, component.id + 1)


def test_get_fed_object_location_assignment_log_entries_for_assignment(object_location_assignments, components):
    object_location_assignment1, object_location_assignment2, _ = object_location_assignments
    component1, component2 = components
    entry1 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_object_location_assignment_log_entries_for_assignment(object_location_assignment1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_object_location_assignment_log_entries_for_assignment(object_location_assignment1.id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_object_location_assignment_log_entries_for_assignment_missing_data(object_location_assignment, component):
    entry = models.FedObjectLocationAssignmentLogEntry(type=models.FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT, object_location_assignment_id=object_location_assignment.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ObjectLocationAssignmentDoesNotExistError):
        fed_logs.get_fed_object_location_assignment_log_entries_for_assignment(object_location_assignment.id + 1)
    with pytest.raises(errors.ObjectLocationAssignmentDoesNotExistError):
        fed_logs.get_fed_object_location_assignment_log_entries_for_assignment(object_location_assignment.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_object_location_assignment_log_entries_for_assignment(object_location_assignment.id, component.id + 1)


def test_get_fed_object_location_assignment_log_entries_for_component(object_location_assignments, components):
    object_location_assignment1, object_location_assignment2, _ = object_location_assignments
    component1, component2 = components
    entry1 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=3)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_object_location_assignment_log_entries_for_component(component1.id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry4

    fed_log_entries = fed_logs.get_fed_object_location_assignment_log_entries_for_component(component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_object_location_assignment_log_entries_for_component_missing_data(object_location_assignment, component):
    entry = models.FedObjectLocationAssignmentLogEntry(type=models.FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT, object_location_assignment_id=object_location_assignment.id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_object_location_assignment_log_entries_for_component(component.id + 1)


def test_get_fed_object_location_assignment_log_entries_for_object(object_location_assignments, components):
    object_location_assignment1, object_location_assignment2, object_location_assignment3 = object_location_assignments
    # object_location_assignment1 and object_location_assignment3 -> object1, object_location_assignment2 -> object2
    component1, component2 = components
    object_id = object_location_assignment1.object_id
    entry1 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment3.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow()
    )
    entry2 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment1.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    entry3 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment1.id,
        component_id=component2.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=2)
    )
    entry4 = models.FedObjectLocationAssignmentLogEntry(
        type=models.FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment2.id,
        component_id=component1.id,
        data={},
        utc_datetime=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.session.add(entry1)
    db.session.add(entry2)
    db.session.add(entry3)
    db.session.add(entry4)
    db.session.commit()
    fed_log_entries = fed_logs.get_fed_object_location_assignment_log_entries_for_object(object_id)
    assert len(fed_log_entries) == 3
    assert fed_log_entries[0] == entry1
    assert fed_log_entries[1] == entry2
    assert fed_log_entries[2] == entry3

    fed_log_entries = fed_logs.get_fed_object_location_assignment_log_entries_for_object(object_id, component2.id)
    assert len(fed_log_entries) == 1
    assert fed_log_entries[0] == entry3


def test_get_fed_object_location_assignment_log_entries_for_object_missing_data(object_location_assignments, component):
    object_id = object_location_assignments[0].object_id
    invalid_object_id = max((c.object_id for c in object_location_assignments)) + 1
    object_location_assignment_id = object_location_assignments[0].id
    entry = models.FedObjectLocationAssignmentLogEntry(type=models.FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT, object_location_assignment_id=object_location_assignment_id, component_id=component.id, data={}, utc_datetime=datetime.datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.get_fed_object_location_assignment_log_entries_for_object(invalid_object_id)
    with pytest.raises(errors.ObjectDoesNotExistError):
        fed_logs.get_fed_object_location_assignment_log_entries_for_object(invalid_object_id, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        fed_logs.get_fed_object_location_assignment_log_entries_for_object(object_id, component.id + 1)
