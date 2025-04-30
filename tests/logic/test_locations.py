# coding: utf-8
"""

"""

import pytest

import sampledb
from sampledb.models import User, UserType, UserLogEntryType, Action, Object, ObjectLogEntryType
from sampledb.logic import locations, objects, actions, user_log, errors, object_log, components

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'


@pytest.fixture
def component():
    component = components.add_component(address=None, uuid=UUID_1, name='Example component', description='')
    return component


@pytest.fixture
def user(app):
    with app.app_context():
        user = User(name='User', email="example@example.com", type=UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        assert user.id is not None
    return sampledb.logic.users.User.from_database(user)


@pytest.fixture
def action():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Sample Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        },
        instrument_id=None
    )
    return action


@pytest.fixture
def object(user: User, action: Action):
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    return objects.create_object(user_id=user.id, action_id=action.id, data=data)


@pytest.fixture
def object2(user: User, action: Action):
    data = {'name': {'_type': 'text', 'text': 'Object 2'}}
    return objects.create_object(user_id=user.id, action_id=action.id, data=data)


@pytest.fixture
def location(user: User):
    return locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=locations.LocationType.LOCATION
    )


def test_create_location(user: User):
    assert len(locations.get_locations()) == 0
    locations.create_location({'en': "Example Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    assert len(locations.get_locations()) == 1
    location = locations.get_locations()[0]
    assert location.name == {
        'en': "Example Location"
    }
    assert location.description == {
        'en': "This is an example location"
    }
    assert location.parent_location_id is None
    user_log_entries = user_log.get_user_log_entries(user.id)
    assert user_log_entries[-1].type == UserLogEntryType.CREATE_LOCATION
    assert user_log_entries[-1].data['location_id'] == location.id


def test_create_location_with_parent_location(user: User):
    parent_location = locations.create_location({'en': "Parent Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    assert len(locations.get_locations()) == 1
    user_log_entries = user_log.get_user_log_entries(user.id)
    assert len(user_log_entries) == 1
    location = locations.create_location({'en': "Example Location"}, {'en': "This is an example location"}, parent_location.id, user.id, locations.LocationType.LOCATION)
    assert len(locations.get_locations()) == 2
    location = locations.get_location(location.id)
    assert location.name == {
        'en': "Example Location"
    }
    assert location.description == {
        'en': "This is an example location"
    }
    assert location.parent_location_id == parent_location.id
    user_log_entries = user_log.get_user_log_entries(user.id)
    assert len(user_log_entries) == 2
    user_log_entry = [e for e in user_log_entries if e.data.get('location_id', -1) == location.id][0]
    assert user_log_entry.type == UserLogEntryType.CREATE_LOCATION
    assert user_log_entry.data['location_id'] == location.id


def test_create_location_with_invalid_parent_location(user: User):
    parent_location = locations.create_location({'en': "Parent Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    assert len(locations.get_locations()) == 1
    with pytest.raises(errors.LocationDoesNotExistError):
        locations.create_location({'en': "Example Location"}, {'en': "This is an example location"}, parent_location.id + 1, user.id, locations.LocationType.LOCATION)
    assert len(locations.get_locations()) == 1


def test_create_location_fed(user, component):
    assert len(locations.get_locations()) == 0
    locations.create_location({'en': "Example Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION, fed_id=1, component_id=component.id)
    assert len(locations.get_locations()) == 1
    location = locations.get_locations()[0]
    assert location.name == {'en': "Example Location"}
    assert location.description == {'en': "This is an example location"}
    assert location.parent_location_id is None
    assert len(user_log.get_user_log_entries(user.id)) == 0
    assert location.component.id == component.id
    assert location.fed_id == 1


def test_create_location_invalid_parameters(user, component):
    with pytest.raises(AssertionError):
        locations.create_location(None, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    with pytest.raises(AssertionError):
        locations.create_location({'en': "Example Location"}, None, None, user.id, locations.LocationType.LOCATION)
    with pytest.raises(AssertionError):
        locations.create_location({'en': "Example Location"}, {'en': "This is an example location"}, None, None, locations.LocationType.LOCATION)
    with pytest.raises(AssertionError):
        locations.create_location({'en': "Example Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION, fed_id=1, component_id=None)
    with pytest.raises(AssertionError):
        locations.create_location({'en': "Example Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION, fed_id=None, component_id=component.id)


def test_create_location_fed_missing_component(user, component):
    with pytest.raises(errors.ComponentDoesNotExistError):
        locations.create_location({'en': "Example Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION, fed_id=1, component_id=component.id + 1)


def test_update_location(user: User):
    parent_location = locations.create_location({'en': "Parent Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    location = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    assert len(locations.get_locations()) == 2
    locations.update_location(location.id, {'en': "Updated Location"}, {'en': "This is a location description"}, None, user.id, location.type_id, False, True)
    assert len(locations.get_locations()) == 2
    location = locations.get_location(location.id)
    assert location.name == {'en': "Updated Location"}
    assert location.description == {'en': "This is a location description"}
    assert location.parent_location_id is None
    locations.update_location(location.id, {'en': "Updated Location"}, {'en': "This is a location description"}, parent_location.id, user.id, location.type_id, False, True)
    location = locations.get_location(location.id)
    assert location.parent_location_id == parent_location.id
    user_log_entries = user_log.get_user_log_entries(user.id)
    assert [e for e in user_log_entries if e.data.get('location_id', -1) == location.id and e.type == UserLogEntryType.UPDATE_LOCATION]


def test_update_location_self_parent(user: User):
    location = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    with pytest.raises(errors.CyclicLocationError):
        locations.update_location(location.id, {'en': "Updated Location"}, {'en': "This is a location description"}, location.id, user.id, location.type_id, False, True)


def test_update_location_cyclic(user: User):
    parent_location = locations.create_location({'en': "Parent Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    location = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, parent_location.id, user.id, locations.LocationType.LOCATION)
    with pytest.raises(errors.CyclicLocationError):
        locations.update_location(parent_location.id, {'en': "Parent Location"}, {'en': "This is an example location"}, location.id, user.id, location.type_id, False, True)


def test_update_location_parent_does_not_exist(user: User):
    location = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    with pytest.raises(errors.LocationDoesNotExistError):
        locations.update_location(location.id, {'en': "Location"}, {'en': "This is an example location"}, location.id + 1, user.id, location.type_id, False, True)


def test_update_location_which_does_not_exist(user: User):
    location = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    with pytest.raises(errors.LocationDoesNotExistError):
        locations.update_location(location.id + 1, {'en': "Location"}, {'en': "This is an example location"}, None, user.id, location.type_id, False, True)


def test_get_location_tree(user: User):
    child_location2 = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    parent_location = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    location = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, parent_location.id, user.id, locations.LocationType.LOCATION)
    child_location1 = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, location.id, user.id, locations.LocationType.LOCATION)
    locations.update_location(child_location2.id, {'en': "Location"}, {'en': "This is an example location"}, location.id, user.id, location.type_id, False, True)
    locations_map, locations_tree = locations.get_locations_tree()
    child_location2 = locations.get_location(child_location2.id)
    assert locations_map == {
        parent_location.id: parent_location,
        location.id: location,
        child_location1.id: child_location1,
        child_location2.id: child_location2
    }
    assert locations_tree == {
        parent_location.id: {
            location.id: {
                child_location1.id: {},
                child_location2.id: {}
            }
        }
    }


def test_assign_location(user: User, object: Object):
    object_location_assignment = locations.get_current_object_location_assignment(object.id)
    assert object_location_assignment is None
    location = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    locations.assign_location_to_object(object.id, location.id, None, user.id, {'en': "This object is stored at this location"})
    object_location_assignment = locations.get_current_object_location_assignment(object.id)
    assert object_location_assignment.object_id == object.id
    assert object_location_assignment.location_id == location.id
    assert object_location_assignment.user_id == user.id
    assert object_location_assignment.description == {'en': "This object is stored at this location"}
    user_log_entries = user_log.get_user_log_entries(user.id)
    assert [e for e in user_log_entries if e.data.get('object_location_assignment_id', -1) == object_location_assignment.id and e.type == UserLogEntryType.ASSIGN_LOCATION]
    object_log_entries = object_log.get_object_log_entries(object.id)
    assert [e for e in object_log_entries if e.data.get('object_location_assignment_id', -1) == object_location_assignment.id and e.type == ObjectLogEntryType.ASSIGN_LOCATION]


def test_assign_location_which_does_not_exist(user: User, object: Object):
    with pytest.raises(errors.LocationDoesNotExistError):
        locations.assign_location_to_object(object.id, 42, None, user.id, {'en': "This object is stored at this location"})
    object_location_assignment = locations.get_current_object_location_assignment(object.id)
    assert object_location_assignment is None


def test_assign_location_to_object_which_does_not_exist(user: User):
    location = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    with pytest.raises(errors.ObjectDoesNotExistError):
        locations.assign_location_to_object(42, location.id, None, user.id, {'en': "This object is stored at this location"})


def test_assign_location_multiple_times(user: User, object: Object):
    object_location_assignments = locations.get_object_location_assignments(object.id)
    assert object_location_assignments == []
    location1 = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    location2 = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    locations.assign_location_to_object(object.id, location1.id, None, user.id, {'en': "This object is stored at this location"})
    locations.assign_location_to_object(object.id, location2.id, None, user.id, {'en': "This object is stored at another location"})
    assert len(locations.get_object_location_assignments(object.id)) == 2
    object_location_assignment1, object_location_assignment2 = locations.get_object_location_assignments(object.id)
    assert object_location_assignment1.object_id == object.id
    assert object_location_assignment1.location_id == location1.id
    assert object_location_assignment1.user_id == user.id
    assert object_location_assignment1.description == {'en': "This object is stored at this location"}
    assert object_location_assignment2.object_id == object.id
    assert object_location_assignment2.location_id == location2.id
    assert object_location_assignment2.user_id == user.id
    assert object_location_assignment2.description == {'en': "This object is stored at another location"}


def test_object_ids_for_location(user: User, action: Action):
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    object1 = objects.create_object(user_id=user.id, action_id=action.id, data=data)
    object2 = objects.create_object(user_id=user.id, action_id=action.id, data=data)
    object3 = objects.create_object(user_id=user.id, action_id=action.id, data=data)
    location1 = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    location2 = locations.create_location({'en': "Location"}, {'en': "This is an example location"}, None, user.id, locations.LocationType.LOCATION)
    assert locations.get_object_ids_at_location(location1.id) == set()
    assert locations.get_object_ids_at_location(location2.id) == set()
    locations.assign_location_to_object(object1.id, location1.id, None, user.id, {'en': ""})
    assert locations.get_object_ids_at_location(location1.id) == {object1.id}
    assert locations.get_object_ids_at_location(location2.id) == set()
    locations.assign_location_to_object(object2.id, location1.id, None, user.id, {'en': ""})
    assert locations.get_object_ids_at_location(location1.id) == {object1.id, object2.id}
    assert locations.get_object_ids_at_location(location2.id) == set()
    locations.assign_location_to_object(object3.id, location2.id, user.id, user.id, {'en': ""})
    assert locations.get_object_ids_at_location(location1.id) == {object1.id, object2.id}
    assert locations.get_object_ids_at_location(location2.id) == {object3.id}


def test_object_responsibility_confirmation(user: User, object: Object, app):
    other_user = User(name='Other User', email="example@example.com", type=UserType.PERSON)
    sampledb.db.session.add(other_user)
    sampledb.db.session.commit()
    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        locations.assign_location_to_object(object.id, None, user.id, other_user.id, {'en': ""})
    app.config['SERVER_NAME'] = server_name
    object_location_assignment = locations.get_current_object_location_assignment(object.id)
    assert not object_location_assignment.confirmed
    locations.confirm_object_responsibility(object_location_assignment.id)
    object_location_assignment = locations.get_current_object_location_assignment(object.id)
    assert object_location_assignment.confirmed
    assert not object_location_assignment.declined
    with pytest.raises(errors.ObjectLocationAssignmentAlreadyConfirmedError):
        locations.decline_object_responsibility(object_location_assignment.id)
    object_location_assignment = locations.get_current_object_location_assignment(object.id)
    assert not object_location_assignment.declined
    assert object_location_assignment.confirmed


def test_object_responsibility_declination(user: User, object: Object, app):
    other_user = User(name='Other User', email="example@example.com", type=UserType.PERSON)
    sampledb.db.session.add(other_user)
    sampledb.db.session.commit()
    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        locations.assign_location_to_object(object.id, None, user.id, other_user.id, {'en': ""})
    app.config['SERVER_NAME'] = server_name
    object_location_assignment = locations.get_current_object_location_assignment(object.id)
    assert not object_location_assignment.declined
    locations.decline_object_responsibility(object_location_assignment.id)
    object_location_assignment = locations.get_current_object_location_assignment(object.id)
    assert object_location_assignment.declined
    assert not object_location_assignment.confirmed
    with pytest.raises(errors.ObjectLocationAssignmentAlreadyDeclinedError):
        locations.confirm_object_responsibility(object_location_assignment.id)
    object_location_assignment = locations.get_current_object_location_assignment(object.id)
    assert object_location_assignment.declined
    assert not object_location_assignment.confirmed


def test_location_translations(user: User):
    location = locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=locations.LocationType.LOCATION
    )
    assert location.name == {
        'en': 'Example Location'
    }
    assert location.description == {
        'en': 'This is an example location'
    }

    with pytest.raises(Exception):
        locations.update_location(
            location_id=location.id,
            name="Example Location 2",
            description="This is an example location 2",
            parent_location_id=None,
            user_id=user.id,
            type_id=location.type_id,
            is_hidden=location.is_hidden,
            enable_object_assignments=location.enable_object_assignments,
        )
    location = locations.get_location(location.id)
    assert location.name == {
        'en': 'Example Location'
    }
    assert location.description == {
        'en': 'This is an example location'
    }

    locations.update_location(
        location_id=location.id,
        name={'en': "Example Location 2"},
        description={'en': "This is an example location 2"},
        parent_location_id=None,
        user_id=user.id,
        type_id=location.type_id,
        is_hidden=location.is_hidden,
            enable_object_assignments=location.enable_object_assignments,
    )
    location = locations.get_location(location.id)
    assert location.name == {
        'en': 'Example Location 2'
    }
    assert location.description == {
        'en': 'This is an example location 2'
    }

    german = sampledb.logic.languages.get_language_by_lang_code('de')
    sampledb.logic.languages.update_language(
        language_id=german.id,
        names=german.names,
        lang_code=german.lang_code,
        datetime_format_datetime=german.datetime_format_datetime,
        datetime_format_moment=german.datetime_format_moment,
        datetime_format_moment_output=german.datetime_format_moment_output,
        date_format_moment_output=german.date_format_moment_output,
        enabled_for_input=True,
        enabled_for_user_interface=True
    )

    locations.update_location(
        location_id=location.id,
        name={
            'en': "Example Location",
            'de': "Beispielort"
        },
        description={
            'en': "This is an example location",
            'de': "Dies ist ein Beispielort"
        },
        parent_location_id=None,
        user_id=user.id,
        type_id=location.type_id,
        is_hidden=location.is_hidden,
        enable_object_assignments=location.enable_object_assignments,
    )
    location = locations.get_location(location.id)
    assert location.name == {
        'en': "Example Location",
        'de': "Beispielort"
    }
    assert location.description == {
        'en': "This is an example location",
        'de': "Dies ist ein Beispielort"
    }

    with pytest.raises(errors.LanguageDoesNotExistError):
        locations.update_location(
            location_id=location.id,
            name={
                'en': "Example Location",
                'xy': "Beispielort"
            },
            description={
                'en': "This is an example location",
                'xy': "Dies ist ein Beispielort"
            },
            parent_location_id=None,
            user_id=user.id,
            type_id=location.type_id,
            is_hidden=location.is_hidden,
            enable_object_assignments=location.enable_object_assignments,
        )

    location = locations.get_location(location.id)
    assert location.name == {
        'en': "Example Location",
        'de': "Beispielort"
    }
    assert location.description == {
        'en': "This is an example location",
        'de': "Dies ist ein Beispielort"
    }

    with pytest.raises(errors.MissingEnglishTranslationError):
        locations.update_location(
            location_id=location.id,
            name={
                'de': "Beispielort"
            },
            description={
                'de': "Dies ist ein Beispielort"
            },
            parent_location_id=None,
            user_id=user.id,
            type_id=location.type_id,
            is_hidden=location.is_hidden,
            enable_object_assignments=location.enable_object_assignments,
        )

    location = locations.get_location(location.id)
    assert location.name == {
        'en': "Example Location",
        'de': "Beispielort"
    }
    assert location.description == {
        'en': "This is an example location",
        'de': "Dies ist ein Beispielort"
    }

    with pytest.raises(errors.MissingEnglishTranslationError):
        locations.update_location(
            location_id=location.id,
            name={},
            description={},
            parent_location_id=None,
            user_id=user.id,
            type_id=location.type_id,
            is_hidden=location.is_hidden,
            enable_object_assignments=location.enable_object_assignments,
        )

    location = locations.get_location(location.id)
    assert location.name == {
        'en': "Example Location",
        'de': "Beispielort"
    }
    assert location.description == {
        'en': "This is an example location",
        'de': "Dies ist ein Beispielort"
    }

    with pytest.raises(errors.LanguageDoesNotExistError):
        locations.create_location(
            name={
                'en': "Example Location 2",
                'xy': "Beispielort 2"
            },
            description={
                'en': "This is an example location",
                'xy': "Dies ist ein Beispielort"
            },
            parent_location_id=None,
            user_id=user.id,
            type_id=locations.LocationType.LOCATION
        )

    with pytest.raises(errors.MissingEnglishTranslationError):
        locations.create_location(
            name={
                'de': "Beispielort 2"
            },
            description={
                'de': "Dies ist ein Beispielort"
            },
            parent_location_id=None,
            user_id=user.id,
            type_id=locations.LocationType.LOCATION
        )

    with pytest.raises(errors.MissingEnglishTranslationError):
        locations.create_location(
            name={},
            description={},
            parent_location_id=None,
            user_id=user.id,
            type_id=locations.LocationType.LOCATION
        )


def test_get_location(user, component):
    location_created = locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
            type_id=locations.LocationType.LOCATION
    )
    location = locations.get_location(location_created.id)
    assert location_created == location
    location_created = locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        fed_id=1,
        component_id=component.id,
        type_id=locations.LocationType.LOCATION
    )
    location = locations.get_location(1, component.id)
    assert location_created == location


def test_get_location_exceptions(component):
    with pytest.raises(errors.LocationDoesNotExistError):
        locations.get_location(42)
    with pytest.raises(errors.ComponentDoesNotExistError):
        locations.get_location(1, component.id + 1)


def test_any_objects_at_location(user, object):
    with pytest.raises(errors.LocationDoesNotExistError):
        locations.any_objects_at_location(0)
    location = locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=locations.LocationType.LOCATION
    )
    other_location = locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=locations.LocationType.LOCATION
    )
    assert not locations.any_objects_at_location(location.id)
    assert not locations.any_objects_at_location(other_location.id)
    locations.assign_location_to_object(
        object_id=object.id,
        location_id=location.id,
        user_id=user.id,
        responsible_user_id=None,
        description=None
    )
    assert locations.any_objects_at_location(location.id)
    assert not locations.any_objects_at_location(other_location.id)
    locations.assign_location_to_object(
        object_id=object.id,
        location_id=other_location.id,
        user_id=user.id,
        responsible_user_id=None,
        description=None
    )
    assert not locations.any_objects_at_location(location.id)
    assert locations.any_objects_at_location(other_location.id)
    locations.assign_location_to_object(
        object_id=object.id,
        location_id=None,
        user_id=user.id,
        responsible_user_id=user.id,
        description=None
    )
    assert not locations.any_objects_at_location(location.id)
    assert not locations.any_objects_at_location(other_location.id)


def test_create_location_type():
    location_type_id = locations.create_location_type(
        name={'en': 'Example Location Type'},
        location_name_singular={'en': 'Example Location'},
        location_name_plural={'en': 'Example Locations'},
        admin_only=False,
        enable_parent_location=True,
        enable_sub_locations=True,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=False,
        enable_capacities=False,
        show_location_log=True,
    ).id
    location_type = sampledb.models.locations.LocationType.query.filter_by(id=location_type_id).first()
    assert location_type.id == location_type_id
    assert location_type.name == {'en': 'Example Location Type'}
    assert location_type.location_name_singular == {'en': 'Example Location'}
    assert location_type.location_name_plural == {'en': 'Example Locations'}
    assert not location_type.admin_only
    assert location_type.enable_parent_location
    assert location_type.enable_sub_locations
    assert location_type.enable_object_assignments
    assert location_type.enable_responsible_users
    assert not location_type.enable_instruments
    assert not location_type.enable_capacities
    assert location_type.show_location_log


def test_update_location_type():
    locations.update_location_type(
        location_type_id=locations.LocationType.LOCATION,
        name={'en': 'Example Location Type'},
        location_name_singular={'en': 'Example Location'},
        location_name_plural={'en': 'Example Locations'},
        admin_only=False,
        enable_parent_location=True,
        enable_sub_locations=True,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=False,
        enable_capacities=False,
        show_location_log=True,
    )
    location_type = sampledb.models.locations.LocationType.query.filter_by(id=locations.LocationType.LOCATION).first()
    assert location_type.id == locations.LocationType.LOCATION
    assert location_type.name == {'en': 'Example Location Type'}
    assert location_type.location_name_singular == {'en': 'Example Location'}
    assert location_type.location_name_plural == {'en': 'Example Locations'}
    assert not location_type.admin_only
    assert location_type.enable_parent_location
    assert location_type.enable_sub_locations
    assert location_type.enable_object_assignments
    assert location_type.enable_responsible_users
    assert not location_type.enable_instruments
    assert not location_type.enable_capacities


def test_get_location_type(component):
    location_type_id = locations.create_location_type(
        name={'en': 'Example Location Type'},
        location_name_singular={'en': 'Example Location'},
        location_name_plural={'en': 'Example Locations'},
        admin_only=False,
        enable_parent_location=True,
        enable_sub_locations=True,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=False,
        show_location_log=True,
    ).id
    location_type = locations.get_location_type(location_type_id=location_type_id)
    assert location_type.id == location_type_id
    assert location_type.name == {'en': 'Example Location Type'}
    assert location_type.location_name_singular == {'en': 'Example Location'}
    assert location_type.location_name_plural == {'en': 'Example Locations'}
    assert not location_type.admin_only
    assert location_type.enable_parent_location
    assert location_type.enable_sub_locations
    assert location_type.enable_object_assignments
    assert location_type.enable_responsible_users
    assert location_type.enable_instruments

    location_type_id = locations.create_location_type(
        name={'en': 'Shared Location Type'},
        location_name_singular={'en': 'Shared Location'},
        location_name_plural={'en': 'Shared Locations'},
        admin_only=True,
        enable_parent_location=False,
        enable_sub_locations=False,
        enable_object_assignments=False,
        enable_responsible_users=False,
        enable_instruments=False,
        enable_capacities=False,
        show_location_log=True,
        fed_id=1,
        component_id=component.id
    ).id
    location_type = locations.get_location_type(location_type_id=1, component_id=component.id)
    assert location_type.id == location_type_id
    assert location_type.name == {'en': 'Shared Location Type'}
    assert location_type.location_name_singular == {'en': 'Shared Location'}
    assert location_type.location_name_plural == {'en': 'Shared Locations'}
    assert location_type.admin_only
    assert not location_type.enable_parent_location
    assert not location_type.enable_sub_locations
    assert not location_type.enable_object_assignments
    assert not location_type.enable_responsible_users
    assert not location_type.enable_instruments


def test_get_location_types():
    location_type_id = locations.create_location_type(
        name={'en': 'Example Location Type'},
        location_name_singular={'en': 'Example Location'},
        location_name_plural={'en': 'Example Locations'},
        admin_only=False,
        enable_parent_location=True,
        enable_sub_locations=True,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=False,
        show_location_log=True,
    ).id

    location_types = locations.get_location_types()
    location_types.sort(key=lambda location_type: location_type.id)
    assert location_types[0].id == locations.LocationType.LOCATION
    assert location_types[1].id == location_type_id


def test_set_location_responsible_users(user):
    location = locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=locations.LocationType.LOCATION
    )
    assert location.responsible_users == []
    locations.set_location_responsible_users(location.id, [user.id])
    location = locations.get_location(location.id)
    assert location.responsible_users == [user]
    locations.set_location_responsible_users(location.id, [])
    location = locations.get_location(location.id)
    assert location.responsible_users == []


def test_get_descendent_location_ids():
    locations_tree = {
        1: {
            4: {
                6: {},
                7: {}
            },
            5: {}
        },
        2: {
            8: {}
        },
        3: {}
    }
    assert sampledb.logic.locations.get_descendent_location_ids(locations_tree[1]) == {4, 5, 6, 7}
    assert sampledb.logic.locations.get_descendent_location_ids(locations_tree[2]) == {8}
    assert sampledb.logic.locations.get_descendent_location_ids(locations_tree[3]) == set()
    assert sampledb.logic.locations.get_descendent_location_ids(locations_tree[1][4]) == {6, 7}
    assert sampledb.logic.locations.get_descendent_location_ids(locations_tree[1][5]) == set()
    assert sampledb.logic.locations.get_descendent_location_ids(locations_tree[1][4][6]) == set()
    assert sampledb.logic.locations.get_descendent_location_ids(locations_tree[1][4][7]) == set()
    assert sampledb.logic.locations.get_descendent_location_ids(locations_tree[2][8]) == set()


def test_get_current_object_location_assignments(user: User, object: Object):
    with pytest.raises(errors.ObjectDoesNotExistError):
        locations.get_current_object_location_assignments([object.id + 1])
    object1 = object
    object2 = objects.create_object(user_id=user.id, action_id=object.action_id, data=object.data)
    assert locations.get_current_object_location_assignments([object1.id, object2.id]) == {
        object1.id: None,
        object2.id: None
    }
    sampledb.logic.locations.assign_location_to_object(object1.id, None, user.id, user.id, None)
    object1_assignment = sampledb.logic.locations.get_current_object_location_assignment(object1.id)
    assert locations.get_current_object_location_assignments([object1.id, object2.id]) == {
        object1.id: object1_assignment,
        object2.id: None
    }
    sampledb.logic.locations.assign_location_to_object(object1.id, None, user.id, user.id, None)
    assert locations.get_current_object_location_assignments([object1.id, object2.id]) != {
        object1.id: object1_assignment,
        object2.id: None
    }
    object1_assignment = sampledb.logic.locations.get_current_object_location_assignment(object1.id)
    assert locations.get_current_object_location_assignments([object1.id, object2.id]) == {
        object1.id: object1_assignment,
        object2.id: None
    }
    sampledb.logic.locations.assign_location_to_object(object2.id, None, user.id, user.id, None)
    assert locations.get_current_object_location_assignments([object1.id, object2.id]) != {
        object1.id: object1_assignment,
        object2.id: None
    }
    object2_assignment = sampledb.logic.locations.get_current_object_location_assignment(object2.id)
    assert locations.get_current_object_location_assignments([object1.id, object2.id]) == {
        object1.id: object1_assignment,
        object2.id: object2_assignment
    }


def test_get_and_set_location_capacities(user, location):
    with pytest.raises(errors.LocationDoesNotExistError):
        locations.get_location_capacities(location.id + 1)
    with pytest.raises(errors.LocationDoesNotExistError):
        locations.set_location_capacity(location.id + 1, sampledb.models.ActionType.SAMPLE_CREATION, 1)
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        locations.set_location_capacity(location.id, sampledb.models.ActionType.SAMPLE_CREATION - 1000, 1)
    with pytest.raises(errors.LocationDoesNotExistError):
        locations.clear_location_capacities(location.id + 1)
    location_type = locations.get_location_type(locations.LocationType.LOCATION)
    locations.update_location_type(
        location_type_id=locations.LocationType.LOCATION,
        name=location_type.name,
        location_name_singular=location_type.location_name_singular,
        location_name_plural=location_type.location_name_plural,
        admin_only=location_type.admin_only,
        enable_parent_location=location_type.enable_parent_location,
        enable_sub_locations=location_type.enable_sub_locations,
        enable_object_assignments=location_type.enable_object_assignments,
        enable_responsible_users=location_type.enable_responsible_users,
        enable_instruments=location_type.enable_instruments,
        enable_capacities=True,
        show_location_log=location_type.show_location_log
    )
    assert locations.get_location_capacities(location.id) == {}
    locations.set_location_capacity(location.id, sampledb.models.ActionType.SAMPLE_CREATION, 5)
    assert locations.get_location_capacities(location.id) == {sampledb.models.ActionType.SAMPLE_CREATION: 5}
    locations.set_location_capacity(location.id, sampledb.models.ActionType.SAMPLE_CREATION, 15)
    assert locations.get_location_capacities(location.id) == {sampledb.models.ActionType.SAMPLE_CREATION: 15}
    locations.set_location_capacity(location.id, sampledb.models.ActionType.SAMPLE_CREATION, None)
    assert locations.get_location_capacities(location.id) == {sampledb.models.ActionType.SAMPLE_CREATION: None}
    locations.set_location_capacity(location.id, sampledb.models.ActionType.SAMPLE_CREATION, 0)
    assert locations.get_location_capacities(location.id) == {}
    locations.set_location_capacity(location.id, sampledb.models.ActionType.SAMPLE_CREATION, 1)
    locations.set_location_capacity(location.id, sampledb.models.ActionType.MEASUREMENT, None)
    assert locations.get_location_capacities(location.id) == {
        sampledb.models.ActionType.SAMPLE_CREATION: 1,
        sampledb.models.ActionType.MEASUREMENT: None
    }
    locations.clear_location_capacities(location.id)
    assert locations.get_location_capacities(location.id) == {}


def test_get_assigned_object_count_by_action_types(user, object, object2, location):
    with pytest.raises(errors.LocationDoesNotExistError):
        locations.get_assigned_object_count_by_action_types(location.id + 1)
    assert locations.get_assigned_object_count_by_action_types(location.id) == {}
    sampledb.logic.locations.assign_location_to_object(object.id, location.id, None, user.id, None)
    assert locations.get_assigned_object_count_by_action_types(location.id) == {
        sampledb.models.ActionType.SAMPLE_CREATION: 1
    }
    sampledb.logic.locations.assign_location_to_object(object2.id, location.id, None, user.id, None)
    assert locations.get_assigned_object_count_by_action_types(location.id) == {
        sampledb.models.ActionType.SAMPLE_CREATION: 2
    }
    assert locations.get_assigned_object_count_by_action_types(location.id, ignored_object_ids=[object.id]) == {
        sampledb.models.ActionType.SAMPLE_CREATION: 1
    }
    sampledb.logic.locations.assign_location_to_object(object.id, None, user.id, user.id, None)
    assert locations.get_assigned_object_count_by_action_types(location.id) == {
        sampledb.models.ActionType.SAMPLE_CREATION: 1
    }
    assert locations.get_assigned_object_count_by_action_types(location.id, ignored_object_ids=[object2.id]) == {}
    sampledb.logic.locations.assign_location_to_object(object2.id, None, user.id, user.id, None)
    assert locations.get_assigned_object_count_by_action_types(location.id) == {}


def test_assigned_object_to_location_with_capacity(user, object, location):
    location_type = locations.get_location_type(locations.LocationType.LOCATION)
    locations.update_location_type(
        location_type_id=locations.LocationType.LOCATION,
        name=location_type.name,
        location_name_singular=location_type.location_name_singular,
        location_name_plural=location_type.location_name_plural,
        admin_only=location_type.admin_only,
        enable_parent_location=location_type.enable_parent_location,
        enable_sub_locations=location_type.enable_sub_locations,
        enable_object_assignments=location_type.enable_object_assignments,
        enable_responsible_users=location_type.enable_responsible_users,
        enable_instruments=location_type.enable_instruments,
        enable_capacities=True,
        show_location_log=location_type.show_location_log
    )
    assert sampledb.logic.locations.get_current_object_location_assignment(object.id) is None
    with pytest.raises(errors.ExceedingLocationCapacityError):
        sampledb.logic.locations.assign_location_to_object(object.id, location.id, None, user.id, None)
    assert sampledb.logic.locations.get_current_object_location_assignment(object.id) is None
    sampledb.logic.locations.set_location_capacity(location.id, sampledb.models.ActionType.SAMPLE_CREATION, 1)
    sampledb.logic.locations.assign_location_to_object(object.id, location.id, None, user.id, None)
    assert sampledb.logic.locations.get_current_object_location_assignment(object.id).location_id == location.id
    assert sampledb.logic.locations.get_current_object_location_assignment(object.id).responsible_user_id is None
    sampledb.logic.locations.assign_location_to_object(object.id, location.id, user.id, user.id, None)
    assert sampledb.logic.locations.get_current_object_location_assignment(object.id).location_id == location.id
    assert sampledb.logic.locations.get_current_object_location_assignment(object.id).responsible_user_id == user.id


def test_location_is_public(user, location):
    assert not sampledb.logic.location_permissions.location_is_public(location.id)
    sampledb.logic.location_permissions.set_location_permissions_for_all_users(location.id, sampledb.models.Permissions.WRITE)
    assert sampledb.logic.location_permissions.location_is_public(location.id)
    sampledb.logic.location_permissions.set_user_location_permissions(location.id, user.id, sampledb.models.Permissions.READ)
    assert not sampledb.logic.location_permissions.location_is_public(location.id)
    sampledb.logic.location_permissions.set_user_location_permissions(location.id, user.id, sampledb.models.Permissions.NONE)
    assert sampledb.logic.location_permissions.location_is_public(location.id)
