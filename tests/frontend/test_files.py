# coding: utf-8
"""

"""

import io
import json
import os
import requests
import pytest
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
import sampledb.logic


from tests.test_utils import flask_server, app, app_context


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def test_get_file_list(flask_server, user, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        }, 'required': ['name']
    }
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example Object'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}'.format(object.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    file_table = document.find('table', {'id': 'file_table'})
    assert file_table is None

    sampledb.logic.files.create_file(object.id, user.id, 'example_file.txt', lambda stream: stream.write('Example Content'.encode('utf-8')))

    r = session.get(flask_server.base_url + 'objects/{}'.format(object.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    file_table = document.find('table', {'id': 'file_table'})
    assert file_table is not None
    file_table_rows = file_table.find('tbody').find_all('tr')
    assert len(file_table_rows) == 1
    assert any('example_file.txt' in str(cell) for cell in file_table_rows[0].find_all('td'))


def test_get_file(flask_server, user, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        }, 'required': ['name']
    }
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example Object'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200

    sampledb.logic.files.create_file(object.id, user.id, 'example_file.txt', lambda stream: stream.write('Example Content'.encode('utf-8')))

    r = session.get(flask_server.base_url + 'objects/{}/files/0'.format(object.id))
    assert r.status_code == 200
    assert r.content == 'Example Content'.encode('utf-8')


def test_upload_files(flask_server, user, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        }, 'required': ['name']
    }
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example Object'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200

    assert len(sampledb.logic.files.get_files_for_object(object.id)) == 0

    r = session.get(flask_server.base_url + 'objects/{}'.format(object.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    file_form = document.find('form', {'action': '/objects/{}/files/'.format(object.id)})
    file_input = file_form.find('input', {'id': 'input-file-upload'})
    file_source = file_form.find('input', {'id': 'input-file-source-hidden'})
    csrf_token = file_form.find('input', {'name': 'csrf_token'})['value']

    files = [
        (file_input['name'], ('example1.txt', io.BytesIO("First Example Content".encode('utf-8')), 'text/plain')),
        (file_input['name'], ('example2.txt', io.BytesIO("Second Example Content".encode('utf-8')), 'text/plain'))
    ]

    data = {
        'csrf_token': csrf_token,
        file_source['name']: 'local'
    }

    r = session.post(flask_server.base_url + 'objects/{}/files/'.format(object.id), data=data, files=files)
    assert r.status_code == 200

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 2
    if files[0].original_file_name == 'example1.txt':
        file1, file2 = files
    else:
        file2, file1 = files
    assert file1.original_file_name == 'example1.txt'
    assert file2.original_file_name == 'example2.txt'
    assert file1.open().read().decode('utf-8') == 'First Example Content'
    assert file2.open().read().decode('utf-8') == 'Second Example Content'


def test_copy_files(flask_server, user, tmpdir):
    directory_function = lambda user_id: os.path.join(tmpdir, 'instrument_files')
    sampledb.logic.files.FILE_STORAGE_PATH = os.path.join(tmpdir, 'uploaded_files')
    sampledb.logic.files.FILE_SOURCES = {
        'instrument': sampledb.logic.files.LocalFileSource(directory_function)
    }
    os.mkdir(sampledb.logic.files.FILE_STORAGE_PATH)
    os.mkdir(directory_function(user.id))
    os.mkdir(os.path.join(directory_function(user.id), 'examples'))
    with open(os.path.join(directory_function(user.id), 'examples', 'example1.txt'), 'w') as file:
        file.write('First Example Content')
    with open(os.path.join(directory_function(user.id), 'examples', 'example2.txt'), 'w') as file:
        file.write('Second Example Content')

    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        }, 'required': ['name']
    }
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example Object'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200

    assert len(sampledb.logic.files.get_files_for_object(object.id)) == 0

    r = session.get(flask_server.base_url + 'objects/{}'.format(object.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    file_form = document.find('form', {'action': '/objects/{}/files/'.format(object.id)})
    file_input = file_form.find('input', {'id': 'input-file-names-hidden'})
    file_source = file_form.find('input', {'id': 'input-file-source-hidden'})
    csrf_token = file_form.find('input', {'name': 'csrf_token'})['value']

    data = {
        'csrf_token': csrf_token,
        file_source['name']: 'instrument',
        file_input['name']: json.dumps(['examples/example1.txt', 'examples/example2.txt'])
    }

    r = session.post(flask_server.base_url + 'objects/{}/files/'.format(object.id), data=data)
    assert r.status_code == 200

    files = sampledb.logic.files.get_files_for_object(object.id)
    assert len(files) == 2
    if files[0].original_file_name == 'example1.txt':
        file1, file2 = files
    else:
        file2, file1 = files
    assert file1.original_file_name == 'example1.txt'
    assert file2.original_file_name == 'example2.txt'
    assert file1.open().read().decode('utf-8') == 'First Example Content'
    assert file2.open().read().decode('utf-8') == 'Second Example Content'


def test_copy_missing_file(flask_server, user, tmpdir):
    directory_function = lambda user_id: os.path.join(tmpdir, 'instrument_files')
    sampledb.logic.files.FILE_STORAGE_PATH = os.path.join(tmpdir, 'uploaded_files')
    sampledb.logic.files.FILE_SOURCES = {
        'instrument': sampledb.logic.files.LocalFileSource(directory_function)
    }
    os.mkdir(sampledb.logic.files.FILE_STORAGE_PATH)
    os.mkdir(directory_function(user.id))
    os.mkdir(os.path.join(directory_function(user.id), 'examples'))

    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        }, 'required': ['name']
    }
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example Object'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200

    assert len(sampledb.logic.files.get_files_for_object(object.id)) == 0

    r = session.get(flask_server.base_url + 'objects/{}'.format(object.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    file_form = document.find('form', {'action': '/objects/{}/files/'.format(object.id)})
    file_input = file_form.find('input', {'id': 'input-file-names-hidden'})
    file_source = file_form.find('input', {'id': 'input-file-source-hidden'})
    csrf_token = file_form.find('input', {'name': 'csrf_token'})['value']

    data = {
        'csrf_token': csrf_token,
        file_source['name']: 'instrument',
        file_input['name']: json.dumps(['examples/example3.txt'])
    }

    r = session.post(flask_server.base_url + 'objects/{}/files/'.format(object.id), data=data)
    assert r.status_code == 200

    assert len(sampledb.logic.files.get_files_for_object(object.id)) == 0


def test_file_tree(flask_server, user: sampledb.models.User, tmpdir):
    directory_function = lambda user_id: os.path.join(tmpdir, 'instrument_files')
    sampledb.logic.files.FILE_STORAGE_PATH = os.path.join(tmpdir, 'uploaded_files')
    sampledb.logic.files.FILE_SOURCES = {
        'instrument': sampledb.logic.files.LocalFileSource(directory_function)
    }
    os.mkdir(sampledb.logic.files.FILE_STORAGE_PATH)
    os.mkdir(directory_function(user.id))
    os.mkdir(os.path.join(directory_function(user.id), 'subdirectory'))
    open(os.path.join(directory_function(user.id), 'example.txt'), 'w')
    open(os.path.join(directory_function(user.id), 'subdirectory', 'file1'), 'w')
    open(os.path.join(directory_function(user.id), 'subdirectory', 'file2'), 'w')

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200

    r = session.get(flask_server.base_url + 'files/', params={'file_source': 'instrument'})
    assert r.status_code == 200

    file_tree = r.json()

    assert file_tree == {
        'example.txt': 'File',
        'subdirectory': {
            'file1': 'File',
            'file2': 'File'
        }
    }


def test_file_tree_with_relative_path(flask_server, user: sampledb.models.User, tmpdir):
    directory_function = lambda user_id: os.path.join(tmpdir, 'instrument_files')
    sampledb.logic.files.FILE_STORAGE_PATH = os.path.join(tmpdir, 'uploaded_files')
    sampledb.logic.files.FILE_SOURCES = {
        'instrument': sampledb.logic.files.LocalFileSource(directory_function)
    }
    os.mkdir(sampledb.logic.files.FILE_STORAGE_PATH)
    os.mkdir(directory_function(user.id))
    os.mkdir(os.path.join(directory_function(user.id), 'subdirectory'))
    open(os.path.join(directory_function(user.id), 'example.txt'), 'w')
    open(os.path.join(directory_function(user.id), 'subdirectory', 'file1'), 'w')
    open(os.path.join(directory_function(user.id), 'subdirectory', 'file2'), 'w')

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200

    r = session.get(flask_server.base_url + 'files/', params={'file_source': 'instrument', 'relative_path': 'subdirectory'})
    assert r.status_code == 200

    file_tree = r.json()

    assert file_tree == {
        'file1': 'File',
        'file2': 'File'
    }


def test_file_tree_with_missing_relative_path(flask_server, user: sampledb.models.User, tmpdir):
    directory_function = lambda user_id: os.path.join(tmpdir, 'instrument_files')
    sampledb.logic.files.FILE_STORAGE_PATH = os.path.join(tmpdir, 'uploaded_files')
    sampledb.logic.files.FILE_SOURCES = {
        'instrument': sampledb.logic.files.LocalFileSource(directory_function)
    }
    os.mkdir(sampledb.logic.files.FILE_STORAGE_PATH)
    os.mkdir(directory_function(user.id))
    os.mkdir(os.path.join(directory_function(user.id), 'subdirectory'))
    open(os.path.join(directory_function(user.id), 'example.txt'), 'w')
    open(os.path.join(directory_function(user.id), 'subdirectory', 'file1'), 'w')
    open(os.path.join(directory_function(user.id), 'subdirectory', 'file2'), 'w')

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200

    r = session.get(flask_server.base_url + 'files/', params={'file_source': 'instrument', 'relative_path': 'unknown'})
    assert r.status_code == 404


def test_file_tree_for_unknown_file_source(flask_server, user: sampledb.models.User, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = os.path.join(tmpdir, 'uploaded_files')
    sampledb.logic.files.FILE_SOURCES = {}
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200

    r = session.get(flask_server.base_url + 'files/', params={'file_source': 'instrument'})
    assert r.status_code == 404


def test_update_file_information(flask_server, user, tmpdir):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        }, 'required': ['name']
    }
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example Object'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200

    sampledb.logic.files.create_file(object.id, user.id, 'example_file.txt', lambda stream: stream.write('Example Content'.encode('utf-8')))

    r = session.get(flask_server.base_url + 'objects/{}'.format(object.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    file_form = document.find('form', {'action': '/objects/{}/files/0'.format(object.id)})
    csrf_token = file_form.find('input', {'name': 'csrf_token'})['value']
    r = session.post(flask_server.base_url + 'objects/{}/files/0'.format(object.id), data={
        'csrf_token': csrf_token,
        'title': 'Title',
        'description': 'Description'
    })
    assert r.status_code == 200
    file = sampledb.logic.files.get_file_for_object(object.id, 0)
    assert file.title == 'Title'
    assert file.description == 'Description'
