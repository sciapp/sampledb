# coding: utf-8
"""

"""
from copy import deepcopy
import pytest

from sampledb import models, db
from sampledb import logic
from sampledb.logic import errors
from sampledb.logic.shares import add_object_share, update_object_share, get_share, get_object_if_shared, get_shares_for_object, get_shares_for_component, get_all_shares

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
UUID_2 = '1e59c517-bd11-4390-aeb4-971f20b06612'
UUID_3 = 'a0c0725f-850e-492d-8a3b-88c5bc037f02'
POLICY = {'access': {'data': True, 'action': True, 'users': False, 'files': False, 'comments': True, 'object_location_assignments': True}, 'permissions': {'users': {'1': 'read', '2': 'grant'}}}


@pytest.fixture
def user():
    user = models.User(name='User', email='example@example.com', affiliation='FZJ', type=models.UserType.PERSON)
    db.session.add(user)
    db.session.commit()
    # force attribute refresh
    assert user.id is not None
    return user


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
def object(user, action):
    object = logic.objects.create_object(user_id=user.id, action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    return object


@pytest.fixture
def objects(user, action):
    object1 = logic.objects.create_object(user_id=user.id, action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    object2 = logic.objects.create_object(user_id=user.id, action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    return object1, object2


@pytest.fixture
def component():
    component = logic.components.add_component(address=None, uuid=UUID_1, name='Example component', description='')
    return component


@pytest.fixture
def components():
    component1 = logic.components.add_component(address=None, uuid=UUID_2, name='Example component 1', description='')
    component2 = logic.components.add_component(address=None, uuid=UUID_3, name='Example component 2', description='')
    return component1, component2


def test_add_object_share(object, component):
    assert len(models.ObjectShare.query.all()) == 0
    assert len(models.FedObjectLogEntry.query.all()) == 0
    share = add_object_share(object.object_id, component.id, POLICY)
    assert share.object_id == object.object_id
    assert share.component_id == component.id
    assert share.policy == POLICY
    assert len(models.ObjectShare.query.all()) == 1
    log_entries = models.FedObjectLogEntry.query.all()
    assert len(log_entries) == 1
    assert log_entries[0].object_id == object.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].type == models.FedObjectLogEntryType.ADD_POLICY


def test_add_object_share_exceptions(object, component):
    with pytest.raises(errors.ObjectDoesNotExistError):
        add_object_share(object.object_id + 1, component.id, POLICY)
    with pytest.raises(errors.ComponentDoesNotExistError):
        add_object_share(object.object_id, component.id + 1, POLICY)
    assert len(models.ObjectShare.query.all()) == 0
    assert len(models.FedObjectLogEntry.query.all()) == 0
    add_object_share(object.object_id, component.id, POLICY)
    with pytest.raises(errors.ShareAlreadyExistsError):
        add_object_share(object.object_id, component.id, POLICY)
    assert len(models.ObjectShare.query.all()) == 1
    assert len(models.FedObjectLogEntry.query.all()) == 1


def test_update_object_share(object, component):
    assert len(models.FedObjectLogEntry.query.all()) == 0
    add_object_share(object.object_id, component.id, POLICY)
    assert len(models.ObjectShare.query.all()) == 1
    assert len(models.FedObjectLogEntry.query.all()) == 1
    policy = deepcopy(POLICY)
    policy['access']['comments'] = False
    policy['permissions']['users']['1'] = 'grant'
    policy['permissions']['users']['42'] = 'grant'
    share = update_object_share(object.object_id, component.id, policy)
    assert share.object_id == object.object_id
    assert share.component_id == component.id
    assert share.policy == policy
    assert len(models.ObjectShare.query.all()) == 1
    log_entries = models.FedObjectLogEntry.query.all()
    assert len(log_entries) == 2
    assert log_entries[0].object_id == object.id
    assert log_entries[0].component_id == component.id
    assert log_entries[0].type == models.FedObjectLogEntryType.ADD_POLICY
    assert log_entries[1].object_id == object.id
    assert log_entries[1].component_id == component.id
    assert log_entries[1].type == models.FedObjectLogEntryType.UPDATE_OBJECT_POLICY


def test_update_object_share_exceptions(object, component):
    with pytest.raises(errors.ShareDoesNotExistError):
        update_object_share(object.object_id, component.id, POLICY)
    assert len(models.ObjectShare.query.all()) == 0
    assert len(models.FedObjectLogEntry.query.all()) == 0
    add_object_share(object.object_id, component.id, POLICY)
    with pytest.raises(errors.ObjectDoesNotExistError):
        update_object_share(object.object_id + 1, component.id, POLICY)
    with pytest.raises(errors.ComponentDoesNotExistError):
        update_object_share(object.object_id, component.id + 1, POLICY)
    assert len(models.ObjectShare.query.all()) == 1
    assert len(models.FedObjectLogEntry.query.all()) == 1


def test_get_share(object, component):
    created_share = add_object_share(object.object_id, component.id, POLICY)
    share = get_share(object.object_id, component.id)
    assert created_share == share
    assert created_share.object_id == share.object_id
    assert created_share.component_id == share.component_id
    assert created_share.policy == share.policy


def test_get_share_exceptions(object, component):
    with pytest.raises(errors.ShareDoesNotExistError):
        get_share(object.object_id, component.id)
    add_object_share(object.object_id, component.id, POLICY)
    with pytest.raises(errors.ObjectDoesNotExistError):
        get_share(object.object_id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        get_share(object.object_id, component.id + 1)


def test_get_object_if_shared(object, component):
    add_object_share(object.object_id, component.id, POLICY)
    obj = get_object_if_shared(object.object_id, component.id)
    assert obj.object_id == object.object_id
    assert obj == object


def test_get_object_if_shared_exceptions(object, component):
    with pytest.raises(errors.ObjectDoesNotExistError):
        get_object_if_shared(object.object_id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        get_object_if_shared(object.object_id, component.id + 1)
    with pytest.raises(errors.ObjectNotSharedError):
        get_object_if_shared(object.object_id, component.id)


def test_get_shares_for_object(objects, components):
    object1, object2 = objects
    component1, component2 = components
    shares = get_shares_for_object(object1.object_id)
    assert shares == []

    share1 = add_object_share(object1.object_id, component1.id, POLICY)
    share2 = add_object_share(object1.object_id, component2.id, POLICY)
    share3 = add_object_share(object2.object_id, component1.id, POLICY)
    share4 = add_object_share(object2.object_id, component2.id, POLICY)

    shares = get_shares_for_object(object1.object_id)
    assert len(shares) == 2
    assert share1 in shares
    assert share2 in shares
    shares = get_shares_for_object(object2.object_id)
    assert len(shares) == 2
    assert share3 in shares
    assert share4 in shares


def test_get_shares_for_object_exceptions(object):
    with pytest.raises(errors.ObjectDoesNotExistError):
        get_shares_for_object(object.object_id + 1)


def test_get_shares_for_component(objects, components):
    object1, object2 = objects
    component1, component2 = components
    shares = get_shares_for_component(component1.id)
    assert shares == []

    share1 = add_object_share(object1.object_id, component1.id, POLICY)
    share2 = add_object_share(object1.object_id, component2.id, POLICY)
    share3 = add_object_share(object2.object_id, component1.id, POLICY)
    share4 = add_object_share(object2.object_id, component2.id, POLICY)

    shares = get_shares_for_component(component1.id)
    assert len(shares) == 2
    assert share1 in shares
    assert share3 in shares
    shares = get_shares_for_component(component2.id)
    assert len(shares) == 2
    assert share2 in shares
    assert share4 in shares


def test_get_shares_for_component_exceptions(component):
    with pytest.raises(errors.ComponentDoesNotExistError):
        get_shares_for_component(component.id + 1)


def test_get_all_shares(objects, components):
    object1, object2 = objects
    component1, component2 = components
    shares = get_shares_for_component(component1.id)
    assert shares == []

    share1 = add_object_share(object1.object_id, component1.id, POLICY)
    share2 = add_object_share(object1.object_id, component2.id, POLICY)
    share3 = add_object_share(object2.object_id, component1.id, POLICY)
    share4 = add_object_share(object2.object_id, component2.id, POLICY)

    shares = get_all_shares()
    assert len(shares) == 4
    assert share1 in shares
    assert share2 in shares
    assert share3 in shares
    assert share4 in shares
