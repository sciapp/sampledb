import json
import datetime
import hashlib
from copy import deepcopy

import pytest

import sampledb
import sampledb.models
import sampledb.logic
from sampledb.logic.federation import conflicts

DATA_1 = {
    "name": {
        "text": {
            "en": "Test-Object"
        },
        "_type": "text"
    },
    "subobject": {
        "name": {
            "text": {
                "en": "Test-Subobject"
            },
            "_type": "text"
        }
    }
}

DATA_2 = {
    "name": {
        "text": {
            "en": "Example Object"
        },
        "_type": "text"
    },
    "array": [
        {
            "text": {
                "en": "First note"
            },
            "_type": "text"
        },
        {
            "text": {
                "en": "Second note"
            },
            "_type": "text"
        }
    ]
}

SCHEMA_1 = {
    "title": {
        "en": "Object Information"
    },
    "type": "object",
    "properties": {
        "name": {
            "type": "text",
            "title": {
                "en": "Name"
            }
        },
        "subobject": {
            "type": "object",
            "title": {
                "en": "Subobject"
            },
            "properties": {
                "name": {
                    "type": "text",
                    "title": {
                        "en": "Subobject – Name"
                    }
                }
            }
        }
    },
    "required": [
        "name"
    ],
    "propertyOrder": [
        "name"
    ],
}

SCHEMA_2 = {
    "title": {
        "en": "Object Information"
    },
    "type": "object",
    "properties": {
        "name": {
            "title": {
                "en": "Name"
            },
            "type": "text"
        },
        "array": {
            "title": "Notes",
            "type": "array",
            "items": {
                "title": "Note",
                "type": "text"
            },
            "minItems": 1,
            "maxItems": 10,
        }
    },
    "required": [
        "name"
    ],
    "propertyOrder": [
        "name"
    ]
}

UUID1 = "e8e37a3f-ac02-48d4-90cc-585c660e7f59"


@pytest.fixture
def component():
    component = sampledb.models.Component(UUID1, name="Test Component", description="")
    sampledb.db.session.add(component)
    sampledb.db.session.commit()
    assert component.id is not None  # Force attribute refresh
    return sampledb.logic.components.Component.from_database(component)


@pytest.fixture
def user():
    user = sampledb.models.User("Test User", "testuser@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert user.id is not None  # Force attribute refresh
    return sampledb.logic.users.User.from_database(user)


@pytest.fixture
def component_user(component):
    component_user = sampledb.models.User("Test User", "testuser@example.com", type=sampledb.models.UserType.FEDERATION_USER, component_id=component.id, fed_id=1)
    sampledb.db.session.add(component_user)
    sampledb.db.session.commit()
    assert component_user.id is not None  # Force attribute refresh
    return sampledb.logic.users.User.from_database(component_user)


@pytest.fixture
def action(user):
    return sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema=SCHEMA_1,
        user_id=user.id
    )


@pytest.fixture
def action_array(user):
    return sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema=SCHEMA_2,
        user_id=user.id,
    )


@pytest.fixture
def object(user, action):
    return sampledb.logic.objects.create_object(
        action_id=action.id,
        data=DATA_1,
        user_id=user.id
    )


@pytest.fixture
def object_array(user, action_array):
    return sampledb.logic.objects.create_object(
        action_id=action_array.id,
        data=DATA_2,
        user_id=user.id
    )


def test_calculate_data_hash(object):
    assert conflicts.calculate_data_hash(None, object.schema, object_id=object.id) is None
    assert conflicts.calculate_data_hash(object.data, None, object_id=object.id) is None
    assert conflicts.calculate_data_hash(object.data, object.schema, object_id=object.id) is not None


def test_calculate_metadata_hash(component_user):
    dt = datetime.datetime.now()
    datetime_pattern = "%Y-%m-%d %H:%M:%S"
    hash_fed_user = conflicts.calculate_metadata_hash(user_id=component_user.id, utc_datetime=dt)
    assert hash_fed_user is not None
    test_hash = hashlib.sha256(json.dumps({
        'user': {
            'fed_uuid': UUID1,
            'user_id': component_user.fed_id
        },
        'utc_datetime': dt.strftime(datetime_pattern)
    }, sort_keys=True).encode('utf-8')).hexdigest()

    assert hash_fed_user == test_hash

    hash_automerge = conflicts.calculate_metadata_hash(user_id=None, utc_datetime=dt)
    assert hash_automerge is not None
    test_hash = hashlib.sha256(json.dumps({
        'user': 'automerged',
        'utc_datetime': dt.strftime(datetime_pattern)
    }, sort_keys=True).encode('utf-8')).hexdigest()

    assert hash_automerge == test_hash


def test_create_object_version_conflict(object, component):
    conflict = conflicts.create_object_version_conflict(
        object_id=object.id,
        fed_version_id=2,
        component_id=component.id,
        base_version_id=1
    )

    assert conflict is not None
    assert conflict.object_id == object.id
    assert conflict.fed_version_id == 2
    assert conflict.component_id == component.id

    conflict2 = conflicts.create_object_version_conflict(
        object_id=object.id,
        fed_version_id=3,
        component_id=component.id,
        base_version_id=1
    )

    assert conflict2 is not None
    assert conflicts.get_object_version_conflict(object_id=object.id, fed_version_id=2, component_id=component.id).discarded


def test_solving_strategy_automerge_success(object, component, action, user, component_user):
    data_modified_local = deepcopy(DATA_1)
    data_modified_local['name']['text']['en'] = "Test-Object v2"
    data_modified_imported = deepcopy(DATA_1)
    data_modified_imported['subobject']['name']['text']['en'] = "Subobject v2"

    conflicting_version = sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object.id,
        fed_version_id=1,
        version_component_id=component.id,
        data=data_modified_imported,
        schema=action.schema,
        action_id=action.id,
        utc_datetime=datetime.datetime.now(),
        user_id=component_user.id,
        local_parent=object.version_id,
        hash_data=conflicts.calculate_data_hash(data_modified_imported, action.schema),
        hash_metadata=conflicts.calculate_metadata_hash(component_user.id, utc_datetime=datetime.datetime.now()),
        imported_from_component_id=component.id,
    )

    conflict = conflicts.create_object_version_conflict(
        object_id=object.id,
        fed_version_id=conflicting_version.fed_version_id,
        component_id=component.id,
        base_version_id=object.version_id
    )

    sampledb.logic.objects.update_object(object_id=object.id, data=data_modified_local, user_id=user.id)

    conflicts.solve_conflict_by_strategy(conflict=conflict, solving_strategy=conflicts.SolvingStrategy.AUTOMERGE)

    object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert object.version_id == 2
    assert object.data['name']['text']['en'] == "Test-Object v2"
    assert object.data['subobject']['name']['text']['en'] == "Subobject v2"
    assert not conflicts.get_object_version_conflict(object_id=conflict.object_id, fed_version_id=conflict.fed_version_id, component_id=conflict.component_id).discarded
    assert conflicts.get_object_version_conflict(object_id=conflict.object_id, fed_version_id=conflict.fed_version_id, component_id=conflict.component_id).version_solved_in == object.version_id


def test_solving_strategy_automerge_fail(object, component, action, user, component_user):
    data_modified_local = deepcopy(DATA_1)
    data_modified_local['name']['text']['en'] = "Test-Object v2"
    data_modified_imported = deepcopy(DATA_1)
    data_modified_imported['name']['text']['en'] = "Test-Object v2B"

    sampledb.logic.objects.update_object(object_id=object.id, data=data_modified_local, user_id=user.id)

    conflicting_version = sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object.id,
        fed_version_id=1,
        version_component_id=component.id,
        data=data_modified_imported,
        schema=action.schema,
        action_id=action.id,
        utc_datetime=datetime.datetime.now(),
        user_id=component_user.id,
        local_parent=object.version_id,
        hash_data=conflicts.calculate_data_hash(data_modified_imported, action.schema),
        hash_metadata=conflicts.calculate_metadata_hash(component_user.id, utc_datetime=datetime.datetime.now()),
        imported_from_component_id=component.id,
    )

    conflict = conflicts.create_object_version_conflict(
        object_id=object.id,
        fed_version_id=conflicting_version.fed_version_id,
        component_id=component.id,
        base_version_id=object.version_id
    )

    with pytest.raises(sampledb.logic.errors.FailedSolvingByStrategyError):
        conflicts.solve_conflict_by_strategy(conflict=conflict, solving_strategy=conflicts.SolvingStrategy.AUTOMERGE)

    latest_local_object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert latest_local_object.version_id == object.version_id + 1
    assert latest_local_object.data == data_modified_local

    conflict = conflicts.get_object_version_conflict(object_id=conflict.object_id, fed_version_id=conflict.fed_version_id, component_id=conflict.component_id)
    assert conflict.version_solved_in is None


def test_solving_strategy_apply_local(object, component, action, user, component_user):
    data_modified_local = deepcopy(DATA_1)
    data_modified_local['name']['text']['en'] = "Test-Object A"
    data_modified_imported = deepcopy(DATA_1)
    data_modified_imported['name']['text']['en'] = "Subobject B"

    conflicting_version = sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object.id,
        fed_version_id=1,
        version_component_id=component.id,
        data=data_modified_imported,
        schema=action.schema,
        action_id=action.id,
        utc_datetime=datetime.datetime.now(),
        user_id=component_user.id,
        local_parent=object.version_id,
        hash_data=conflicts.calculate_data_hash(data_modified_imported, action.schema),
        hash_metadata=conflicts.calculate_metadata_hash(component_user.id, utc_datetime=datetime.datetime.now()),
        imported_from_component_id=component.id,
    )

    conflict = conflicts.create_object_version_conflict(
        object_id=object.id,
        fed_version_id=conflicting_version.fed_version_id,
        component_id=component.id,
        base_version_id=object.version_id
    )

    sampledb.logic.objects.update_object(object_id=object.id, data=data_modified_local, user_id=user.id)

    conflicts.solve_conflict_by_strategy(conflict=conflict, solving_strategy=conflicts.SolvingStrategy.APPLY_LOCAL)

    object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert object.version_id == 2
    assert object.data == data_modified_local
    assert object.component_id is None
    assert not conflicts.get_object_version_conflict(object_id=conflict.object_id, fed_version_id=conflict.fed_version_id, component_id=conflict.component_id).discarded
    assert conflicts.get_object_version_conflict(object_id=conflict.object_id, fed_version_id=conflict.fed_version_id, component_id=conflict.component_id).version_solved_in == object.version_id


def test_solving_strategy_apply_imported(object, component, action, user, component_user):
    data_modified_local = deepcopy(DATA_1)
    data_modified_local['name']['text']['en'] = "Test-Object A"
    data_modified_imported = deepcopy(DATA_1)
    data_modified_imported['name']['text']['en'] = "Test-Object B"

    conflicting_version = sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object.id,
        fed_version_id=1,
        version_component_id=component.id,
        data=data_modified_imported,
        schema=action.schema,
        action_id=action.id,
        utc_datetime=datetime.datetime.now(),
        user_id=component_user.id,
        local_parent=object.version_id,
        hash_data=conflicts.calculate_data_hash(data_modified_imported, action.schema),
        hash_metadata=conflicts.calculate_metadata_hash(component_user.id, utc_datetime=datetime.datetime.now()),
        imported_from_component_id=component.id,
    )

    conflict = conflicts.create_object_version_conflict(
        object_id=object.id,
        fed_version_id=conflicting_version.fed_version_id,
        component_id=component.id,
        base_version_id=object.version_id
    )

    sampledb.logic.objects.update_object(object_id=object.id, data=data_modified_local, user_id=user.id)

    conflicts.solve_conflict_by_strategy(conflict=conflict, solving_strategy=conflicts.SolvingStrategy.APPLY_IMPORTED)

    object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert object.version_id == 2
    assert object.data == data_modified_imported
    assert object.version_component_id == component.id
    assert not conflicts.get_object_version_conflict(object_id=conflict.object_id, fed_version_id=conflict.fed_version_id, component_id=conflict.component_id).discarded
    assert conflicts.get_object_version_conflict(object_id=conflict.object_id, fed_version_id=conflict.fed_version_id, component_id=conflict.component_id).version_solved_in == object.version_id


def test_differing_version_length_local_higher(object, component, action, user, component_user):
    data_modified_local_1 = deepcopy(DATA_1)
    data_modified_local_1['name']['text']['en'] = "Test-Object A"
    data_modified_local_2 = deepcopy(data_modified_local_1)
    data_modified_local_2['name']['text']['en'] = "Test-Object A.2"
    data_modified_imported = deepcopy(DATA_1)
    data_modified_imported['subobject']['name']['text']['en'] = "Subobject B"

    sampledb.logic.objects.update_object(object_id=object.id, data=data_modified_local_1, user_id=user.id)
    sampledb.logic.objects.update_object(object_id=object.id, data=data_modified_local_2, user_id=user.id)

    conflicting_version = sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object.id,
        fed_version_id=1,
        version_component_id=component.id,
        data=data_modified_imported,
        schema=action.schema,
        action_id=action.id,
        utc_datetime=datetime.datetime.now(),
        user_id=component_user.id,
        local_parent=object.version_id,
        hash_data=conflicts.calculate_data_hash(data_modified_imported, action.schema),
        hash_metadata=conflicts.calculate_metadata_hash(component_user.id, utc_datetime=datetime.datetime.now()),
        imported_from_component_id=component.id,
    )

    conflict = conflicts.create_object_version_conflict(
        object_id=object.id,
        fed_version_id=conflicting_version.fed_version_id,
        component_id=component.id,
        base_version_id=object.version_id
    )

    conflicts.solve_conflict_by_strategy(conflict=conflict, solving_strategy=conflicts.SolvingStrategy.AUTOMERGE)

    latest_object = sampledb.logic.objects.get_object(object_id=conflict.object_id)
    assert latest_object.version_id == 3
    assert latest_object.data['name'] == data_modified_local_2['name']
    assert latest_object.data['subobject'] == data_modified_imported['subobject']
    conflict = conflicts.get_object_version_conflict(object_id=conflict.object_id, fed_version_id=conflict.fed_version_id, component_id=conflict.component_id)
    assert conflict.version_solved_in == latest_object.version_id


def test_differing_version_length_imported_higher(object, component, action, user, component_user):
    data_modified_local = deepcopy(DATA_1)
    data_modified_local['name']['text']['en'] = "Test-Object A"
    data_modified_imported_1 = deepcopy(DATA_1)
    data_modified_imported_1['subobject']['name']['text']['en'] = "Subobject B.1"
    data_modified_imported_2 = deepcopy(data_modified_imported_1)
    data_modified_imported_2['subobject']['name']['text']['en'] = "Subobject B.2"

    sampledb.logic.objects.update_object(object_id=object.id, data=data_modified_local, user_id=user.id)

    sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object.id,
        fed_version_id=1,
        version_component_id=component.id,
        data=data_modified_imported_1,
        schema=action.schema,
        action_id=action.id,
        utc_datetime=datetime.datetime.now(),
        user_id=component_user.id,
        local_parent=object.version_id,
        hash_data=conflicts.calculate_data_hash(data_modified_imported_1, action.schema),
        hash_metadata=conflicts.calculate_metadata_hash(component_user.id, utc_datetime=datetime.datetime.now()),
        imported_from_component_id=component.id,
    )

    conflicting_version = sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object.id,
        fed_version_id=2,
        version_component_id=component.id,
        data=data_modified_imported_2,
        schema=action.schema,
        action_id=action.id,
        utc_datetime=datetime.datetime.now(),
        user_id=component_user.id,
        local_parent=object.version_id,
        hash_data=conflicts.calculate_data_hash(data_modified_imported_2, action.schema),
        hash_metadata=conflicts.calculate_metadata_hash(component_user.id, utc_datetime=datetime.datetime.now()),
        imported_from_component_id=component.id,
    )

    conflict = conflicts.create_object_version_conflict(
        object_id=object.id,
        fed_version_id=conflicting_version.fed_version_id,
        component_id=component.id,
        base_version_id=object.version_id
    )

    conflicts.solve_conflict_by_strategy(conflict=conflict, solving_strategy=conflicts.SolvingStrategy.AUTOMERGE)

    latest_object = sampledb.logic.objects.get_object(object_id=conflict.object_id)
    assert latest_object.version_id == 2
    assert latest_object.data['name'] == data_modified_local['name']
    assert latest_object.data['subobject'] == data_modified_imported_2['subobject']
    conflict = conflicts.get_object_version_conflict(object_id=conflict.object_id, fed_version_id=conflict.fed_version_id, component_id=conflict.component_id)
    assert conflict.version_solved_in == latest_object.version_id


def test_automerge_partial_changes(object, component, action, user, component_user):
    data_modified_local = deepcopy(DATA_1)
    data_modified_local['name']['text']['en'] = "Test-Object A"
    data_modified_imported = deepcopy(DATA_1)
    data_modified_imported['name']['text']['en'] = "Test-Object B"

    conflicting_version = sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object.id,
        fed_version_id=1,
        version_component_id=component.id,
        data=data_modified_imported,
        schema=action.schema,
        action_id=action.id,
        utc_datetime=datetime.datetime.now(),
        user_id=component_user.id,
        local_parent=object.version_id,
        hash_data=conflicts.calculate_data_hash(data_modified_imported, action.schema),
        hash_metadata=conflicts.calculate_metadata_hash(component_user.id, utc_datetime=datetime.datetime.now()),
        imported_from_component_id=component.id,
    )

    conflict = conflicts.create_object_version_conflict(
        object_id=object.id,
        fed_version_id=conflicting_version.fed_version_id,
        component_id=component.id,
        base_version_id=object.version_id
    )

    sampledb.logic.objects.update_object(object_id=object.id, data=data_modified_local, user_id=user.id)

    fully_solved, new_data = conflicts.automerge_conflict(object_version_conflict=conflict)

    assert not fully_solved
    assert 'local' in new_data['name']
    assert new_data['name']['local'] == data_modified_local['name']
    assert 'imported' in new_data['name']
    assert new_data['name']['imported'] == data_modified_imported['name']


def test_merge_array_conflict_automerge_successful(object_array, component, action_array, user, component_user):
    data_modified_local = deepcopy(DATA_2)
    data_modified_local['array'][0]['text']['en'] = "First note v2"
    data_modified_imported = deepcopy(DATA_2)
    data_modified_imported['array'].append({
        'text': {'en': 'Imported Note'}, '_type': 'text'
    })

    sampledb.logic.objects.update_object(
        object_id=object_array.id,
        data=data_modified_local,
        user_id=user.id
    )

    conflicting_version = sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object_array.id,
        fed_version_id=1,
        version_component_id=component.id,
        data=data_modified_imported,
        schema=action_array.schema,
        action_id=action_array.id,
        utc_datetime=datetime.datetime.now(),
        user_id=user.id,
        local_parent=object_array.version_id,
        hash_data=conflicts.calculate_data_hash(data=data_modified_local, schema=action_array.schema),
        hash_metadata=conflicts.calculate_metadata_hash(user_id=user.id, utc_datetime=datetime.datetime.now()),
        imported_from_component_id=component.id,
    )

    conflict = conflicts.create_object_version_conflict(
        object_id=object_array.id,
        fed_version_id=conflicting_version.fed_version_id,
        component_id=component.id,
        base_version_id=object_array.version_id
    )

    conflicts.solve_conflict_by_strategy(conflict, solving_strategy=conflicts.SolvingStrategy.AUTOMERGE)

    latest_object = sampledb.logic.objects.get_object(object_id=object_array.id)
    assert latest_object.data['array'][0] == data_modified_local['array'][0]
    assert len(latest_object.data['array']) == 3
    assert latest_object.data['array'][2] == data_modified_imported['array'][2]


def test_merge_array_conflict_automerge_unsuccessful(object_array, component, action_array, user, component_user):
    data_modified_local = deepcopy(DATA_2)
    data_modified_local['array'].append({
        'text': {'en': 'Local Note'}, '_type': 'text'
    })
    data_modified_imported = deepcopy(DATA_2)
    data_modified_imported['array'].append({
        'text': {'en': 'Imported Note'}, '_type': 'text'
    })

    sampledb.logic.objects.update_object(
        object_id=object_array.id,
        data=data_modified_local,
        user_id=user.id
    )

    conflicting_version = sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object_array.id,
        fed_version_id=1,
        version_component_id=component.id,
        data=data_modified_imported,
        schema=action_array.schema,
        action_id=action_array.id,
        utc_datetime=datetime.datetime.now(),
        user_id=user.id,
        local_parent=object_array.version_id,
        hash_data=conflicts.calculate_data_hash(data=data_modified_imported, schema=object_array.schema),
        hash_metadata=conflicts.calculate_metadata_hash(user_id=user.id, utc_datetime=datetime.datetime.now()),
        imported_from_component_id=component.id,
    )

    conflict = conflicts.create_object_version_conflict(
        object_id=object_array.id,
        fed_version_id=conflicting_version.fed_version_id,
        component_id=component.id,
        base_version_id=object_array.version_id
    )

    with pytest.raises(sampledb.logic.errors.FailedSolvingByStrategyError):
        conflicts.solve_conflict_by_strategy(conflict, solving_strategy=conflicts.SolvingStrategy.AUTOMERGE)

    conflicts.solve_conflict_by_strategy(conflict, solving_strategy=conflicts.SolvingStrategy.APPLY_LOCAL)

    latest_object = sampledb.logic.objects.get_object(object_id=object_array.id)
    assert latest_object.data['array'] == data_modified_local['array']
