# coding: utf-8
"""

"""

import datetime
import os

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
    return user


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


def test_files(user: User, object: Object, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

    start_datetime = datetime.datetime.utcnow()
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: stream.write(b"1"))
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    file = files.get_files_for_object(object_id=object.object_id)[0]
    assert file.id == 0
    assert file.user_id == user.id
    assert file.uploader == user
    assert file.object_id == object.object_id
    assert file.original_file_name == "test.png"
    assert file.utc_datetime >= start_datetime
    assert file.utc_datetime <= datetime.datetime.utcnow()
    assert file.real_file_name == tmpdir.join(str(object.action_id)).join(str(object.id)).join("0000_test.png")
    assert file.open().read() == b"1"
    files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="example.txt", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 2
    file2, file1 = files.get_files_for_object(object_id=object.object_id)
    assert file1.original_file_name == "example.txt"
    assert file2.original_file_name == "test.png"
    assert file1.id == 1
    assert file2.id == 0
    assert file2.utc_datetime >= start_datetime
    assert file2.utc_datetime <= datetime.datetime.utcnow()


def test_invalid_file_name(user: User, object: Object, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="t" * 146 + ".png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    with pytest.raises(errors.FileNameTooLongError):
        files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="t" * 147 + ".png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1


def test_same_file_name(user: User, object: Object, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

    files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: None)
    files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: None)
    file1, file2 = files.get_files_for_object(object_id=object.object_id)
    assert file1.original_file_name == file2.original_file_name
    assert file1.real_file_name != file2.real_file_name


def test_file_exists(user: User, object: Object, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    tmpdir.join(str(object.action_id)).join(str(object.id)).join("0000_test.png").write("", ensure=True)

    with pytest.raises(FileExistsError):
        files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0


def test_too_many_files(user: User, object: Object, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir
    files.MAX_NUM_FILES = 1

    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    with pytest.raises(errors.TooManyFilesForObjectError):
        files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    files.MAX_NUM_FILES = 10000


def test_get_file(user: User, object: Object, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir
    assert files.get_file_for_object(object_id=object.object_id, file_id=0) is None
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: None)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    assert files.get_file_for_object(object_id=object.object_id, file_id=0) is not None


def test_file_information(user: User, object: Object, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_local_file(object_id=object.object_id, user_id=user.id, file_name="test.png", save_content=lambda stream: stream.write(b"1"))

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

    with pytest.raises(files.FileDoesNotExistError):
        files.update_file_information(object_id=object.object_id, file_id=file.id + 1, user_id=user.id, title='Title', description='Description')
    assert len(file.log_entries) == 3


def test_invalid_file_storage(user: User, object: Object, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    db_file = files._create_db_file(object_id=object.object_id, user_id=user.id, data={"storage": "web", "url": "http://localhost/"})
    file = files.File.from_database(db_file)

    with pytest.raises(errors.InvalidFileStorageError):
        file.original_file_name

    with pytest.raises(errors.InvalidFileStorageError):
        file.real_file_name

    with pytest.raises(errors.InvalidFileStorageError):
        file.open()


def test_create_url_file(user: User, object: Object, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_url_file(object.id, user.id, "http://localhost")
    assert len(files.get_files_for_object(object_id=object.object_id)) == 1
    file = files.get_files_for_object(object_id=object.object_id)[0]
    assert file.storage == 'url'
    assert file.title == 'http://localhost'
    assert file.data['url'] == 'http://localhost'


def test_hide_file(user: User, object: Object, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

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
    dt = datetime.datetime.fromtimestamp(1430674212)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_fed_file(
        object_id=object.object_id,
        user_id=user.id,
        data={"storage": "url", "url": "https://example.com/file"},
        save_content=None,
        utc_datetime=dt,
        fed_id=1,
        component_id=component.id
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
        component_id=component.id
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
        component_id=component.id
    )
    assert len(files.get_files_for_object(object_id=object.object_id)) == 3
    file = files.get_files_for_object(object_id=object.object_id)[-1]
    assert file.id == 2
    assert file.user_id == user.id
    assert file.uploader == user
    assert file.object_id == object.object_id
    assert file.utc_datetime == dt


def test_create_fed_url_file_invalid_params(object, user, component):
    dt = datetime.datetime.fromtimestamp(1430674212)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    with pytest.raises(TypeError):
        files.create_fed_file(
            object_id=object.object_id,
            user_id=user.id,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=1,
            component_id=None
        )
    with pytest.raises(TypeError):
        files.create_fed_file(
            object_id=object.object_id,
            user_id=user.id,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=None,
            component_id=component.id
        )
    with pytest.raises(TypeError):
        files.create_fed_file(
            object_id=object.object_id,
            user_id=user.id,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=None,
            component_id=None
        )
    with pytest.raises(errors.ComponentDoesNotExistError):
        files.create_fed_file(
            object_id=object.object_id,
            user_id=user.id,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=1,
            component_id=component.id + 1
        )
    with pytest.raises(errors.ObjectDoesNotExistError):
        files.create_fed_file(
            object_id=object.object_id + 1,
            user_id=user.id,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=1,
            component_id=component.id
        )
    with pytest.raises(errors.UserDoesNotExistError):
        files.create_fed_file(
            object_id=object.object_id,
            user_id=user.id + 1,
            data={"storage": "url", "url": "https://example.com/file"},
            save_content=None,
            utc_datetime=dt,
            fed_id=1,
            component_id=component.id
        )
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0


def test_create_fed_binary_file(object, user, component):
    dt = datetime.datetime.fromtimestamp(1430674212)
    binary_data = os.urandom(256)
    assert len(files.get_files_for_object(object_id=object.object_id)) == 0
    files.create_fed_file(
        object_id=object.object_id,
        user_id=user.id,
        data={"storage": "database", "original_file_name": "testfile"},
        save_content=lambda stream: stream.write(binary_data),
        utc_datetime=dt,
        fed_id=1,
        component_id=component.id
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
        component_id=component.id
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

