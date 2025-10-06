# coding: utf-8
"""

"""

import datetime
import os
import time

import numpy as np
import pytest

import sampledb
from sampledb.models import User, UserType, Action, Object
from sampledb.logic import files, objects, actions, errors, components

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'


@pytest.fixture
def user():
    user = User(name='User', email="example@example.com", type=UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
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
def component():
    component = components.add_component(address=None, uuid=UUID_1, name='Example component', description='')
    return component


def test_files(user: User, object: Object):
    start_datetime = datetime.datetime.now(datetime.timezone.utc)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_database_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: stream.write(b"1"))
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    file = files.get_files_for_object(object_id=object.object_id)[0]
    assert file.id == 0
    assert file.user_id == user.id
    assert file.uploader == user
    assert file.object_id == object.object_id
    assert file.original_file_name == "test.png"
    assert file.utc_datetime >= start_datetime
    assert file.utc_datetime <= datetime.datetime.now(datetime.timezone.utc)
    assert file.open().read() == b"1"
    files.create_database_file(object_id=object.object_id, user_id=user.id, file_name="example.txt", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 2
    file2, file1 = files.get_files_for_object(object_id=object.object_id)
    assert file1.original_file_name == "example.txt"
    assert file2.original_file_name == "test.png"
    assert file1.id == 1
    assert file2.id == 0
    assert file2.utc_datetime >= start_datetime
    assert file2.utc_datetime <= datetime.datetime.now(datetime.timezone.utc)


def test_invalid_file_name(user: User, object: Object):
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_database_file(object_id=object.object_id, user_id=user.id, file_name="t" * 146 + ".png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    with pytest.raises(errors.FileNameTooLongError):
        files.create_database_file(object_id=object.object_id, user_id=user.id, file_name="t" * 147 + ".png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1


def test_too_many_files(user: User, object: Object):
    files.MAX_NUM_FILES = 1

    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_database_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    with pytest.raises(errors.TooManyFilesForObjectError):
        files.create_database_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    files.MAX_NUM_FILES = 10000


def test_get_file(user: User, object: Object):
    assert files.get_file_for_object(object_id=object.object_id, file_id=0) is None
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_database_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    assert files.get_file_for_object(object_id=object.object_id, file_id=0) is not None


def test_file_information(user: User, object: Object):
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_database_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: stream.write(b"1"))

    file = files.get_file_for_object(object.object_id, 0)

    assert file.title == file.original_file_name
    assert file.description is None
    files.update_file_information(object_id=object.object_id, file_id=file.id, user_id=user.id, title='Title', description='')
    file = files.get_file_for_object(object.object_id, 0)
    assert file.title == 'Title'
    assert file.description is None
    assert len(file.log_entries) == 1
    log_entry = file.log_entries[0]
    assert log_entry.type == files.FileLogEntryType.EDIT_TITLE
    assert log_entry.data == {'title': 'Title'}
    files.update_file_information(object_id=object.object_id, file_id=file.id, user_id=user.id, title='Title', description='Description')
    file = files.get_file_for_object(object.object_id, 0)
    assert file.title == 'Title'
    assert file.description == 'Description'
    assert len(file.log_entries) == 2
    log_entry = file.log_entries[1]
    assert log_entry.type == files.FileLogEntryType.EDIT_DESCRIPTION
    assert log_entry.data == {'description': 'Description'}
    files.update_file_information(object_id=object.object_id, file_id=file.id, user_id=user.id, title='', description='Description')
    file = files.get_file_for_object(object.object_id, 0)
    assert file.title == file.original_file_name
    assert file.description == 'Description'
    assert len(file.log_entries) == 3
    log_entry = file.log_entries[2]
    assert log_entry.type == files.FileLogEntryType.EDIT_TITLE
    assert log_entry.data == {'title': file.original_file_name}

    with pytest.raises(files.FileDoesNotExistError):
        files.update_file_information(object_id=object.object_id, file_id=file.id + 1, user_id=user.id, title='Title', description='Description')
    assert len(file.log_entries) == 3


def test_url_file_information(user: User, object: Object):
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0

    files.create_url_file(object_id=object.object_id, user_id=user.id, url='http://example.com/example')

    file = files.get_file_for_object(object.object_id, 0)

    assert file.title == file.url
    assert file.description is None
    files.update_file_information(object_id=object.object_id, file_id=file.id, user_id=user.id, title='Title', description='')
    file = files.get_file_for_object(object.object_id, 0)
    assert file.title == 'Title'
    assert file.description is None
    assert len(file.log_entries) == 1
    log_entry = file.log_entries[0]
    assert log_entry.type == files.FileLogEntryType.EDIT_TITLE
    assert log_entry.data == {'title': 'Title'}
    files.update_file_information(object_id=object.object_id, file_id=file.id, user_id=user.id, title='Title', description='Description')
    file = files.get_file_for_object(object.object_id, 0)
    assert file.title == 'Title'
    assert file.description == 'Description'
    assert len(file.log_entries) == 2
    log_entry = file.log_entries[1]
    assert log_entry.type == files.FileLogEntryType.EDIT_DESCRIPTION
    assert log_entry.data == {'description': 'Description'}
    files.update_file_information(object_id=object.object_id, file_id=file.id, user_id=user.id, title='', description='Description')
    file = files.get_file_for_object(object.object_id, 0)
    assert file.title == file.url
    assert file.description == 'Description'
    assert len(file.log_entries) == 3
    log_entry = file.log_entries[2]
    assert log_entry.type == files.FileLogEntryType.EDIT_TITLE
    assert log_entry.data == {'title': file.url}
    files.update_file_information(object_id=object.object_id, file_id=file.id, user_id=user.id, title='', description='Description', url='https://example.com/example')
    file = files.get_file_for_object(object.object_id, 0)
    assert file.url == 'https://example.com/example'
    assert file.description == 'Description'
    assert len(file.log_entries) == 4
    log_entry = file.log_entries[3]
    assert log_entry.type == files.FileLogEntryType.EDIT_URL
    assert log_entry.data == {'url': file.url}

    with pytest.raises(files.FileDoesNotExistError):
        files.update_file_information(object_id=object.object_id, file_id=file.id + 1, user_id=user.id, title='Title', description='Description')
    assert len(file.log_entries) == 4


def test_invalid_file_storage(user: User, object: Object):
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    db_file = files._create_db_file(object_id=object.object_id, user_id=user.id, data={"storage": "web", "url": "http://localhost/"})
    file = files.File.from_database(db_file)

    with pytest.raises(errors.InvalidFileStorageError):
        file.original_file_name

    with pytest.raises(errors.InvalidFileStorageError):
        file.open()


def test_create_url_file(user: User, object: Object):
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_url_file(object.id, user.id, "http://localhost")
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    file = files.get_files_for_object(object_id=object.object_id)[0]
    assert file.storage == 'url'
    assert file.title == 'http://localhost'
    assert file.data['url'] == 'http://localhost'


def test_hide_file(user: User, object: Object):
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_url_file(object.id, user.id, "http://localhost")
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    file = files.get_files_for_object(object_id=object.object_id)[0]
    assert not file.is_hidden
    assert file.hide_reason is None
    files.hide_file(file.object_id, file.id, user.id, "Reason")
    # Reload file as hiding state is cached
    file = files.get_files_for_object(object_id=object.object_id)[0]
    assert file.is_hidden
    assert file.hide_reason == "Reason"


def test_create_fed_url_file(object, user, component):
    dt = datetime.datetime.fromtimestamp(1430674212).replace(tzinfo=datetime.timezone.utc)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_fed_file(
        object_id=object.object_id,
        user_id=user.id,
        data={"storage": "url", "url": "https://example.com/file"},
        save_content=None,
        utc_datetime=dt,
        fed_id=1,
        component_id=component.id,
        imported_from_component_id=component.id,
    )
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    file = files.get_files_for_object(object_id=object.object_id)[-1]
    assert file.id == 0
    assert file.user_id == user.id
    assert file.uploader == user
    assert file.object_id == object.object_id
    assert file.url == "https://example.com/file"
    assert file.utc_datetime == dt

    files.create_fed_file(
        object_id=object.object_id,
        user_id=None,
        data={"storage": "url", "url": "https://example.com/file"},
        save_content=None,
        utc_datetime=dt,
        fed_id=2,
        component_id=component.id,
        imported_from_component_id=component.id,
    )
    assert len(files.get_files_for_object(object_id=object.object_id)) == 2
    file = files.get_files_for_object(object_id=object.object_id)[-1]
    assert file.id == 1
    assert file.user_id is None
    assert file.uploader is None
    assert file.object_id == object.object_id
    assert file.url == "https://example.com/file"
    assert file.utc_datetime == dt

    files.create_fed_file(
        object_id=object.object_id,
        user_id=user.id,
        data=None,
        save_content=None,
        utc_datetime=dt,
        fed_id=3,
        component_id=component.id,
        imported_from_component_id=component.id,
    )
    assert len(files.get_files_for_object(object_id=object.object_id)) == 3
    file = files.get_files_for_object(object_id=object.object_id)[-1]
    assert file.id == 2
    assert file.user_id == user.id
    assert file.uploader == user
    assert file.object_id == object.object_id
    assert file.utc_datetime == dt


def test_create_fed_url_file_invalid_params(object, user, component):
    dt = datetime.datetime.fromtimestamp(1430674212).replace(tzinfo=datetime.timezone.utc)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    with pytest.raises(TypeError):
        files.create_fed_file(
            object_id=object.object_id,
            user_id=user.id,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=1,
            component_id=None,
            imported_from_component_id=component.id,
        )
    with pytest.raises(TypeError):
        files.create_fed_file(
            object_id=object.object_id,
            user_id=user.id,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=None,
            component_id=component.id,
            imported_from_component_id=component.id,
        )
    with pytest.raises(errors.ComponentDoesNotExistError):
        files.create_fed_file(
            object_id=object.object_id,
            user_id=user.id,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=1,
            component_id=component.id + 1,
            imported_from_component_id=component.id,
        )
    with pytest.raises(errors.ObjectDoesNotExistError):
        files.create_fed_file(
            object_id=object.object_id + 1,
            user_id=user.id,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=1,
            component_id=component.id,
            imported_from_component_id=component.id,
        )
    with pytest.raises(errors.UserDoesNotExistError):
        files.create_fed_file(
            object_id=object.object_id,
            user_id=user.id + 1,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=1,
            component_id=component.id,
            imported_from_component_id=component.id,
        )
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0


def test_create_fed_binary_file(object, user, component):
    dt = datetime.datetime.fromtimestamp(1430674212).replace(tzinfo=datetime.timezone.utc)
    binary_data = os.urandom(256)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_fed_file(
        object_id=object.object_id,
        user_id=user.id,
        data={"storage": "database", "original_file_name": "testfile"},
        save_content=lambda stream: stream.write(binary_data),
        utc_datetime=dt,
        fed_id=1,
        component_id=component.id,
        imported_from_component_id=component.id,
    )
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    file = files.get_files_for_object(object_id=object.object_id)[-1]
    assert file.id == 0
    assert file.user_id == user.id
    assert file.uploader == user
    assert file.object_id == object.object_id
    assert file.original_file_name == "testfile"
    assert file.binary_data == binary_data
    assert file.utc_datetime == dt

    files.create_fed_file(
        object_id=object.object_id,
        user_id=None,
        data={"storage": "database", "original_file_name": "testfile"},
        save_content=lambda stream: stream.write(binary_data),
        utc_datetime=dt,
        fed_id=2,
        component_id=component.id,
        imported_from_component_id=component.id,
    )
    assert len(files.get_files_for_object(object_id=object.object_id)) == 2
    file = files.get_files_for_object(object_id=object.object_id)[-1]
    assert file.id == 1
    assert file.user_id is None
    assert file.uploader is None
    assert file.object_id == object.object_id
    assert file.original_file_name == 'testfile'
    assert file.binary_data == binary_data
    assert file.utc_datetime == dt


def test_replace_file_reference_ids():
    data = {
        'array': [
            {
                '_type': 'file',
                'file_id': -1
            }
        ]
    }
    sampledb.logic.temporary_files.replace_file_reference_ids(
        data,
        temporary_file_id_map={
            1: 15
        }
    )
    assert data == {
        'array': [
            {
                '_type': 'file',
                'file_id': 15
            }
        ]
    }


def test_get_referenced_temporary_file_ids():
    assert sampledb.logic.temporary_files.get_referenced_temporary_file_ids(
        data={
            'array': [
                {
                    '_type': 'file',
                    'file_id': -1
                },
                {
                    '_type': 'file',
                    'file_id': -2
                }
            ],
            'file': {
                '_type': 'file',
                'file_id': -1
            }
        }
    ) == {1, 2}


def test_deferred_attribute_performance(user: User, object: Object):
    large_file_content = b'a' * 1024 * 1024 * 5
    for _ in range(100):
        files.create_database_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: stream.write(large_file_content))
    sampledb.db.engine.dispose()
    start = time.time()
    for _ in range(10):
        all_files = sampledb.models.files.File.query.all()
        for file in all_files:
            assert file.id >= 0
            _ = file.binary_data
        sampledb.db.session.expire_all()
    models_with_data_access = time.time() - start
    start = time.time()
    for _ in range(10):
        all_files = sampledb.models.files.File.query.all()
        for file in all_files:
            assert file.id >= 0
        sampledb.db.session.expire_all()
    models_without_data_access = time.time() - start
    assert models_without_data_access < models_with_data_access / 2
    start = time.time()
    for _ in range(10):
        all_files = sampledb.logic.files.get_files_for_object(object.object_id)
        for file in all_files:
            assert file.id >= 0
            _ = file.binary_data
        sampledb.db.session.expire_all()
    logic_with_data_access = time.time() - start
    start = time.time()
    for _ in range(10):
        all_files = sampledb.logic.files.get_files_for_object(object.object_id)
        for file in all_files:
            assert file.id >= 0
        sampledb.db.session.expire_all()
    logic_without_data_access = time.time() - start
    assert models_without_data_access < models_with_data_access / 2
    assert logic_without_data_access < logic_with_data_access / 2
    assert np.isclose(logic_with_data_access, models_with_data_access, rtol=1)
    assert np.isclose(logic_without_data_access, models_without_data_access, rtol=2)
