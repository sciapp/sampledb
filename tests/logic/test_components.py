# coding: utf-8
'''

'''
import datetime
from uuid import uuid4

import pytest

from sampledb import models, logic
from sampledb.logic.components import add_component, update_component, validate_address
from sampledb.logic.errors import InvalidComponentAddressError, ComponentAlreadyExistsError, InvalidComponentUUIDError, ComponentDoesNotExistError, InvalidComponentNameError, InsecureComponentAddressError


def test_create_component():
    assert len(models.components.Component.query.all()) == 0

    component_id = add_component('28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', address='https://example.com', description='').id

    assert len(models.components.Component.query.all()) == 1
    component = models.components.Component.query.filter_by(id=component_id).first()
    assert component is not None
    assert component.id == component_id
    assert component.address == 'https://example.com'
    assert component.uuid == '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
    assert component.name == 'Example Component'
    assert component.description == ''
    assert component.last_sync_timestamp is None


def test_create_duplicate_component():
    add_component(uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', address='https://example.com', description='')
    assert len(models.components.Component.query.all()) == 1

    with pytest.raises(ComponentAlreadyExistsError):
        add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component 2', description='')

    with pytest.raises(ComponentAlreadyExistsError):
        add_component(address='https://example.com', uuid='cf7118a7-6976-5b1a-9a39-7adc72f591a4', name='Example Component', description='')

    assert len(models.components.Component.query.all()) == 1


def test_create_component_with_empty_address():
    assert len(models.components.Component.query.all()) == 0

    with pytest.raises(InvalidComponentAddressError):
        add_component(uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', address='', description='')

    assert len(models.components.Component.query.all()) == 0


def test_create_component_with_empty_uuid():
    assert len(models.components.Component.query.all()) == 0

    with pytest.raises(InvalidComponentUUIDError):
        add_component(uuid='', name='Example Component', address='https://example.com', description='')

    assert len(models.components.Component.query.all()) == 0


def test_create_component_with_long_name():
    assert len(models.components.Component.query.all()) == 0

    with pytest.raises(InvalidComponentNameError):
        add_component(name='A' * 101, uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', description='')

    assert len(models.components.Component.query.all()) == 0

    component_id = add_component(name='A' * 100, uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', description='').id

    assert len(models.components.Component.query.all()) == 1
    component = models.components.Component.query.filter_by(id=component_id).first()
    assert component is not None
    assert component.id == component_id
    assert component.name == 'A' * 100
    assert component.uuid == '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
    assert component.address is None
    assert component.description == ''


def test_create_component_with_invalid_uuid():
    assert len(models.components.Component.query.all()) == 0

    with pytest.raises(InvalidComponentUUIDError):
        add_component(uuid='28b8d3ca-fb5f-59d9-8090-bfdd6d07a71', name='Example Component', description='', address=None)

    assert len(models.components.Component.query.all()) == 0


def test_get_component():
    component_id = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='').id
    assert len(models.components.Component.query.all()) == 1

    component = logic.components.get_component(component_id)

    assert component is not None
    assert component.id == component_id
    assert component.address == 'https://example.com'
    assert component.uuid == '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
    assert component.name == 'Example Component'
    assert component.description == ''


def test_get_component_by_uuid():
    component_id = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='').id
    assert len(models.components.Component.query.all()) == 1

    component = logic.components.get_component_by_uuid('28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71')

    assert component is not None
    assert component.id == component_id
    assert component.address == 'https://example.com'
    assert component.uuid == '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
    assert component.name == 'Example Component'
    assert component.description == ''


def test_get_component_id_by_uuid():
    component_id = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='').id

    assert logic.components.get_component_id_by_uuid('28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71') == component_id
    assert logic.components.get_component_id_by_uuid('28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71X') is None
    assert logic.components.get_component_id_by_uuid('28b8d3ca-fb5f-59d9-8090-bfdbd6d07a72') is None
    assert logic.components.get_component_id_by_uuid(None) is None


def test_get_component_that_does_not_exist():
    component_id = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='').id
    assert len(models.components.Component.query.all()) == 1

    with pytest.raises(ComponentDoesNotExistError):
        logic.components.get_component(component_id + 1)


def test_get_component_by_uuid_that_does_not_exist():
    add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='')
    assert len(models.components.Component.query.all()) == 1

    with pytest.raises(ComponentDoesNotExistError):
        logic.components.get_component_by_uuid('28b8d3ca-fb5f-59d9-8090-bfdbd6d07a72')


def test_get_components():
    components = logic.components.get_components()
    assert len(components) == 0

    component_id = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component 1', description='').id

    components = logic.components.get_components()
    assert len(components) == 1
    component = components[0]
    assert component.id == component_id
    assert component.address == 'https://example.com'
    assert component.uuid == '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
    assert component.name == 'Example Component 1'
    assert component.description == ''
    assert component.last_sync_timestamp is None

    add_component(address='https://example.com/sampledb', uuid='cf7118a7-6976-5b1a-9a39-7adc72f591a4', name='Example Component 2', description='')
    components = logic.components.get_components()
    assert len(components) == 2
    assert {components[0].name, components[1].name} == {'Example Component 1', 'Example Component 2'}


def test_update_component():
    component_id = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='').id
    assert len(models.components.Component.query.all()) == 1

    update_component(component_id=component_id, address='https://example.com/sampledb', name='Test Component', description='Test Description')

    component = models.components.Component.query.filter_by(id=component_id).first()
    assert component is not None
    assert component.id == component_id
    assert component.address == 'https://example.com/sampledb'
    assert component.uuid == '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
    assert component.name == 'Test Component'
    assert component.description == 'Test Description'
    assert component.last_sync_timestamp is None


def test_update_component_that_does_not_exist():
    component_id = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='').id
    assert len(models.components.Component.query.all()) == 1

    with pytest.raises(ComponentDoesNotExistError):
        update_component(component_id=component_id + 1, address='https://example.com', name='Test Component', description='Test Description')

    component = models.components.Component.query.filter_by(id=component_id).first()
    assert component is not None
    assert component.id == component_id
    assert component.name == 'Example Component'
    assert component.description == ''
    assert component.last_sync_timestamp is None


def test_update_component_with_existing_name():
    add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='')
    component_id = add_component(address='https://example.com/sampledb', uuid='cf7118a7-6976-5b1a-9a39-7adc72f591a4', name='Example Component 2', description='').id
    assert len(models.components.Component.query.all()) == 2

    with pytest.raises(ComponentAlreadyExistsError):
        update_component(component_id=component_id, address='https://example.com/sampledb', name='Example Component', description='')

    component = models.components.Component.query.filter_by(id=component_id).first()
    assert component is not None
    assert component.id == component_id
    assert component.address == 'https://example.com/sampledb'
    assert component.uuid == 'cf7118a7-6976-5b1a-9a39-7adc72f591a4'
    assert component.name == 'Example Component 2'
    assert component.description == ''
    assert component.last_sync_timestamp is None


def test_update_component_with_empty_address():
    component_id = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='').id
    assert len(models.components.Component.query.all()) == 1

    with pytest.raises(InvalidComponentAddressError):
        update_component(component_id=component_id, address='', name='Test Component', description='Test Description')

    component = models.components.Component.query.filter_by(id=component_id).first()
    assert component is not None
    assert component.id == component_id
    assert component.address == 'https://example.com'
    assert component.name == 'Example Component'
    assert component.description == ''
    assert component.last_sync_timestamp is None


def test_update_component_with_long_name():
    component_id = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='').id
    assert len(models.components.Component.query.all()) == 1

    with pytest.raises(InvalidComponentNameError):
        update_component(component_id=component_id, name='A' * 101, description='')

    component = models.components.Component.query.filter_by(id=component_id).first()
    assert component is not None
    assert component.id == component_id
    assert component.address == 'https://example.com'
    assert component.name == 'Example Component'
    assert component.description == ''
    assert component.last_sync_timestamp is None

    update_component(component_id=component_id, name='A' * 100, description='')

    component = models.components.Component.query.filter_by(id=component_id).first()
    assert component is not None
    assert component.id == component_id
    assert component.name == 'A' * 100
    assert component.address is None
    assert component.description == ''
    assert component.last_sync_timestamp is None


def test_get_name():
    uuid = uuid4()
    component = add_component(address='https://example.com', uuid=str(uuid), name='Example Component', description='')
    assert component.get_name() == component.name
    assert component.get_name() == 'Example Component'

    uuid = uuid4()
    component = add_component(address='https://example.com/sampledb', uuid=str(uuid), name=None, description='')
    assert component.get_name() == 'example.com/sampledb'

    uuid = uuid4()
    component = add_component(address=None, uuid=str(uuid), name=None, description='')
    assert component.get_name() == 'Database #' + str(component.id)


def test_add_component_no_https():
    uuid = uuid4()
    address = 'example.com'
    component = add_component(address=address, uuid=str(uuid), name='Component', description='')
    assert component.address == 'https://' + address


def test_validate_address():
    assert validate_address('example.com') == 'https://example.com'
    assert validate_address('www.example.com') == 'https://www.example.com'
    assert validate_address('https://www.example.com') == 'https://www.example.com'
    assert validate_address('https://example.com:1234') == 'https://example.com:1234'
    assert validate_address('https://example.com') == 'https://example.com'
    assert validate_address('https://example.com', allow_http=True) == 'https://example.com'
    assert validate_address('https://example.com', max_length=23) == 'https://example.com'
    assert validate_address('https://www.{}.com'.format('a' * 61)) == 'https://www.{}.com'.format('a' * 61)

    with pytest.raises(InvalidComponentAddressError):
        validate_address('example')
    with pytest.raises(InvalidComponentAddressError):
        validate_address('')
    with pytest.raises(InvalidComponentAddressError):
        validate_address('com')
    with pytest.raises(InvalidComponentAddressError):
        validate_address('ftp://example.com')
    with pytest.raises(InvalidComponentAddressError):
        validate_address('https://www.example.com', max_length=10)
    with pytest.raises(InsecureComponentAddressError):
        validate_address('http://example.com')


def test_update_last_sync_timestamp():
    component = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='')
    assert component.last_sync_timestamp is None
    timestamp = datetime.datetime.utcnow()
    component.update_last_sync_timestamp(last_sync_timestamp=timestamp)
    component = logic.components.get_component(component.id)
    assert component.last_sync_timestamp == timestamp


def test_get_object_ids_for_component_id():
    component = add_component(
        address='https://example.com',
        uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71',
        name='Example Component',
        description=''
    )
    assert not logic.components.get_object_ids_for_component_id(component.id)
    with pytest.raises(logic.errors.ComponentDoesNotExistError):
        logic.components.get_object_ids_for_component_id(component.id + 1)
    action = logic.actions.create_action(
        action_type_id=models.ActionType.SAMPLE_CREATION,
        schema=None,
        fed_id=1,
        component_id=component.id
    )
    object = logic.objects.insert_fed_object_version(
        fed_object_id=1,
        fed_version_id=1,
        component_id=component.id,
        action_id=action.id,
        schema=None,
        data=None,
        user_id=None,
        utc_datetime=None
    )
    assert logic.components.get_object_ids_for_component_id(component.id) == {object.id}


def test_check_component_exists():
    component_id = add_component(address='https://example.com', uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='').id
    logic.components.check_component_exists(component_id)
    with pytest.raises(logic.errors.ComponentDoesNotExistError):
        logic.components.check_component_exists(component_id + 1)
