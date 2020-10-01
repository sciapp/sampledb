# coding: utf-8
"""

"""

import datetime
import pytest

import sampledb
from sampledb.models import User, UserType, Action, Object
from sampledb.logic import files, objects, actions, errors


@pytest.fixture
def user():
    user = User(name='User', email="example@fz-juelich.de", type=UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return user


@pytest.fixture
def action():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Example Action',
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
        description='',
        instrument_id=None
    )
    return action


@pytest.fixture
def object(user: User, action: Action):
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    return objects.create_object(user_id=user.id, action_id=action.id, data=data)


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
        files.update_file_information(object_id=object.object_id, file_id=file.id+1, user_id=user.id, title='Title', description='Description')
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
