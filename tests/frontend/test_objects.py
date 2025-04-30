# coding: utf-8
"""

"""

import datetime
import os
import json
from copy import deepcopy

import requests
import pytest
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

import sampledb
import sampledb.models
import sampledb.logic

from ..conftest import wait_for_page_load

SCHEMA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'schemas'))
OBJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'objects'))
UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
UUID_2 = '1e59c517-bd11-4390-aeb4-971f20b06612'
REFERENCES_SCHEMA = {'title': 'Table and List', 'type': 'object', 'properties': {'name': {'title': 'Object Name', 'type': 'text'}, 'user1': {'title': 'User 1', 'type': 'user'}, 'object1': {'title': 'Object 1', 'type': 'object_reference'}, 'user2': {'title': 'User 2', 'type': 'user'}, 'object2': {'title': 'Object 2', 'type': 'object_reference'}, 'user3': {'title': 'User 3', 'type': 'user'}, 'object3': {'title': 'Object 3', 'type': 'object_reference'}, 'user4': {'title': 'User 4', 'type': 'user'}, 'object4': {'title': 'Object 4', 'type': 'object_reference'}, 'userlist': {'title': 'User List', 'type': 'array', 'style': 'list', 'items': {'title': 'User', 'type': 'user'}}, 'objectlist': {'title': 'Object List', 'type': 'array', 'style': 'list', 'items': {'title': 'Object', 'type': 'object_reference'}}, 'usertable': {'title': 'User Table', 'type': 'array', 'style': 'table', 'items': {'type': 'array', 'title': 'User Row', 'items': {'title': 'User', 'type': 'user'}}}, 'objecttable': {'title': 'Object Table', 'type': 'array', 'style': 'table', 'items': {'type': 'array', 'title': 'Object Row', 'items': {'title': 'Object', 'type': 'object_reference'}}}}, 'propertyOrder': ['name', 'user1', 'object1', 'user2', 'object2', 'user3', 'object3', 'user4', 'object4', 'userlist', 'objectlist', 'usertable', 'objecttable'], 'required': ['name']}
REFERENCES_DATA_FRAME = {'name': {'text': {'en': 'Test Object'}, '_type': 'text'}, 'user1': {'_type': 'user'}, 'user2': {'_type': 'user'}, 'user3': {'_type': 'user'}, 'user4': {'_type': 'user'}, 'object1': {'_type': 'object_reference'}, 'object2': {'_type': 'object_reference'}, 'object3': {'_type': 'object_reference'}, 'object4': {'_type': 'object_reference'}, 'userlist': [{'_type': 'user'}, {'_type': 'user'}, {'_type': 'user'}, {'_type': 'user'}], 'objectlist': [{'_type': 'object_reference'}, {'_type': 'object_reference'}, {'_type': 'object_reference'}, {'_type': 'object_reference'}], 'usertable': [[{'_type': 'user', 'user_id': 6}, {'_type': 'user', 'user_id': 3, 'component_uuid': '7c3db1e8-15ba-4d86-885f-792e054d9c73'}], [{'_type': 'user', 'user_id': 5}, {'_type': 'user', 'user_id': 3, 'component_uuid': '208363a4-941b-4071-b6f1-f7803bcbe923'}]], 'objecttable': [[{'_type': 'object_reference'}, {'_type': 'object_reference'}], [{'_type': 'object_reference'}, {'_type': 'object_reference'}]]}


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


@pytest.fixture
def simple_action():
    action = sampledb.models.actions.Action(
        action_type_id=sampledb.models.actions.ActionType.SAMPLE_CREATION,
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
    sampledb.db.session.add(action)
    sampledb.db.session.commit()
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def simple_object(user, simple_action):
    object = sampledb.logic.objects.create_object(user_id=user.id, action_id=simple_action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    return object


@pytest.fixture
def component():
    component = sampledb.logic.components.add_component(
        uuid=UUID_1,
        name='Component',
        address='https://example.com',
        description='Component description'
    )

    return component


def test_get_objects(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    names = ['Example1', 'Example2', 'Example42']
    objects = [
        sampledb.logic.objects.create_object(
            data={'name': {'_type': 'text', 'text': name}},
            user_id=user.id,
            action_id=action.id
        )
        for name in names
    ]
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert len(document.find('tbody').find_all('tr')) == 3
    for name in names:
        assert name in str(document.find('tbody'))


def test_get_objects_by_action_id(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action1 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(
        action_id=action1.id,
        permissions=sampledb.models.Permissions.READ
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action1.id,
        name='Example Action 1',
        description=''
    )
    action2 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(
        action_id=action2.id,
        permissions=sampledb.models.Permissions.READ
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action2.id,
        name='Example Action 2',
        description=''
    )
    names = ['Example1', 'Example2', 'Example42']
    objects = [
        sampledb.logic.objects.create_object(
            data={'name': {'_type': 'text', 'text': name}},
            user_id=user.id,
            action_id=action1.id
        )
        for name in names
    ]
    sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Other Object'}},
        user_id=user.id,
        action_id=action2.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects?action={}'.format(action1.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert len(document.find('tbody').find_all('tr')) == 3
    for name in names:
        assert name in str(document.find('tbody'))


def test_get_objects_by_project_id(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    names = ['Example1', 'Example2']
    objects = [
        sampledb.logic.objects.create_object(
            data={'name': {'_type': 'text', 'text': name}},
            user_id=user.id,
            action_id=action.id
        )
        for name in names
    ]
    project = sampledb.logic.projects.create_project("Example Project", "", user.id)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/?project={}'.format(project.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('tbody') is None or len(document.find('tbody').find_all('tr')) == 0
    assert document.find('tbody') is None or 'Example1' not in str(document.find('tbody'))

    sampledb.logic.object_permissions.set_project_object_permissions(objects[0].id, project.id, sampledb.logic.object_permissions.Permissions.READ)
    r = session.get(flask_server.base_url + 'objects/?project={}'.format(project.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert len(document.find('tbody').find_all('tr')) == 1
    assert 'Example1' in str(document.find('tbody'))


def test_get_objects_by_action_type(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action1 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.MEASUREMENT,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action1.id,
        name='Example Action 1',
        description=''
    )
    action2 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action2.id,
        name='Example Action 2',
        description=''
    )
    names = ['Example1', 'Example2', 'Example42']
    objects = [
        sampledb.logic.objects.create_object(
            data={'name': {'_type': 'text', 'text': name}},
            user_id=user.id,
            action_id=action1.id
        )
        for name in names
    ]
    sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Other Object'}},
        user_id=user.id,
        action_id=action2.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects?t=measurements')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert len(document.find('tbody').find_all('tr')) == 3
    for name in names:
        assert name in str(document.find('tbody'))


def test_get_objects_by_action_id_and_type(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action1 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(
        action_id=action1.id,
        permissions=sampledb.models.Permissions.READ
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action1.id,
        name='Example Action 1',
        description=''
    )
    action2 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.MEASUREMENT,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(
        action_id=action2.id,
        permissions=sampledb.models.Permissions.READ
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action2.id,
        name='Example Action 2',
        description=''
    )
    names = ['Example1', 'Example2', 'Example42']
    objects = [
        sampledb.logic.objects.create_object(
            data={'name': {'_type': 'text', 'text': name}},
            user_id=user.id,
            action_id=action1.id
        )
        for name in names
    ]
    sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Other Object'}},
        user_id=user.id,
        action_id=action2.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects?action={}&t=samples'.format(action1.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert len(document.find('tbody').find_all('tr')) == 3
    for name in names:
        assert name in str(document.find('tbody'))


def test_search_objects(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    names = ['Example1', 'Example2', 'Example12']
    objects = [
        sampledb.logic.objects.create_object(
            data={'name': {'_type': 'text', 'text': name}},
            user_id=user.id,
            action_id=action.id
        )
        for name in names
    ]
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects', params={'q': 'Example1'})
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert len(document.find('tbody').find_all('tr')) == len([name for name in names if 'Example1' in name])
    for name in names:
        if 'Example1' in name:
            assert name in str(document.find('tbody'))
        else:
            assert name not in str(document.find('tbody'))

    schema = action.schema
    schema['properties']['object_reference'] = {
        'title': 'Object Reference',
        'type': 'object_reference'
    }
    sampledb.logic.actions.update_action(
        action_id=action.id,
        schema=schema
    )
    object = sampledb.logic.objects.create_object(
        data={
            'name': {
                '_type': 'text',
                'text': 'Example4'
            },
            'object_reference': {
                '_type': 'object_reference',
                'object_id': objects[0].id
            }
        },
        user_id=user.id,
        action_id=action.id
    )
    r = session.get(flask_server.base_url + 'objects', params={'q': '*object_reference.name == "Example1"'})
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert len(document.find('tbody').find_all('tr')) == 1
    for name in names + ['Example4']:
        if 'Example4' in name:
            assert name in str(document.find('tbody'))
        else:
            assert name not in str(document.find('tbody'))

def test_objects_referencable(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action1 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    schema['properties']['tags'] = {'title': 'Tags', 'type': 'tags'}
    schema['required'].append('tags')
    action2 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.MEASUREMENT,
        schema=schema
    )
    names = ['Example1', 'Example2', '<b>Example42</b>']
    objects = [
        sampledb.logic.objects.create_object(
            data={'name': {'_type': 'text', 'text': name}},
            user_id=user.id,
            action_id=action1.id
        )
        for name in names
    ]
    other_object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Other Object'}, 'tags': {'_type': 'tags', 'tags': ['a', 'b']}},
        user_id=user.id,
        action_id=action2.id
    )
    action1_id = action1.id
    action2_id = action2.id

    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@example.com', type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=objects[0].object_id, user_id=new_user_id, permissions=sampledb.logic.object_permissions.Permissions.READ)
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=objects[1].object_id, user_id=new_user_id, permissions=sampledb.logic.object_permissions.Permissions.WRITE)
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=objects[2].object_id, user_id=new_user_id, permissions=sampledb.logic.object_permissions.Permissions.GRANT)

    component = sampledb.logic.components.add_component(address=None, uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='')
    fed_object = sampledb.logic.objects.insert_fed_object_version(1, 0, component.id, None, schema, {'name': {'_type': 'text', 'text': 'Fed Object'}, 'tags': {'_type': 'tags', 'tags': ['a', 'b']}}, None, None)
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=fed_object.object_id, user_id=user.id, permissions=sampledb.logic.object_permissions.Permissions.READ)

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/referencable')
    assert r.status_code == 200
    data = json.loads(r.content)
    assert len(data['referencable_objects']) == 5
    assert data['referencable_objects'] == [
        {'action_id': None, 'id': fed_object.object_id, 'is_fed': True, 'max_permission': 1, 'text': f'Fed Object (#{fed_object.object_id}, #{fed_object.fed_object_id} @ Example Component)', 'unescaped_text': f'Fed Object (#{fed_object.object_id}, #{fed_object.fed_object_id} @ Example Component)', 'tags': ['a', 'b'], 'is_eln_imported': False},
        {'action_id': action2_id, 'id': other_object.object_id, 'is_fed': False, 'max_permission': 3, 'text': f'Other Object (#{other_object.object_id})', 'unescaped_text': f'Other Object (#{other_object.object_id})', 'tags': ['a', 'b'], 'is_eln_imported': False},
        {'action_id': action1_id, 'id': objects[2].object_id, 'is_fed': False, 'max_permission': 3, 'text': f'&lt;b&gt;Example42&lt;/b&gt; (#{objects[2].object_id})', 'unescaped_text': f'<b>Example42</b> (#{objects[2].object_id})', 'tags': [], 'is_eln_imported': False},
        {'action_id': action1_id, 'id': objects[1].object_id, 'is_fed': False, 'max_permission': 3, 'text': f'Example2 (#{objects[1].object_id})', 'unescaped_text': f'Example2 (#{objects[1].object_id})', 'tags': [], 'is_eln_imported': False},
        {'action_id': action1_id, 'id': objects[0].object_id, 'is_fed': False, 'max_permission': 3, 'text': f'Example1 (#{objects[0].object_id})', 'unescaped_text': f'Example1 (#{objects[0].object_id})', 'tags': [], 'is_eln_imported': False}
    ]

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user_id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/referencable?required_perm=WRITE')
    assert r.status_code == 200
    data = json.loads(r.content)
    assert len(data['referencable_objects']) == 2
    assert data['referencable_objects'] == [
        {'action_id': action1_id, 'id': objects[2].object_id, 'is_fed': False, 'max_permission': 3, 'text': f'&lt;b&gt;Example42&lt;/b&gt; (#{objects[2].object_id})', 'unescaped_text': f'<b>Example42</b> (#{objects[2].object_id})', 'tags': [], 'is_eln_imported': False},
        {'action_id': action1_id, 'id': objects[1].object_id, 'is_fed': False, 'max_permission': 2, 'text': f'Example2 (#{objects[1].object_id})', 'unescaped_text': f'Example2 (#{objects[1].object_id})', 'tags': [], 'is_eln_imported': False}
    ]


def test_get_object(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}'.format(object.object_id))
    assert r.status_code == 200
    assert 'Example' in r.content.decode('utf-8')
    assert 'Save' not in r.content.decode('utf-8')


def test_get_object_no_permissions(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@example.com', type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user_id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}'.format(object.object_id))
    assert r.status_code == 403
    assert '/objects/{}/permissions/request'.format(object.object_id) in r.content.decode('utf-8')

    sampledb.logic.users.set_user_readonly(user.id, True)

    r = session.get(flask_server.base_url + 'objects/{}'.format(object.object_id))
    assert r.status_code == 403
    assert '/objects/{}/permissions/request'.format(object.object_id) not in r.content.decode('utf-8')


def test_request_object_permissions(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@example.com', type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user_id)).status_code == 200
    r = session.post(flask_server.base_url + 'objects/{}/permissions/request'.format(object.object_id))
    assert r.status_code == 200
    notifications = sampledb.logic.notifications.get_notifications(user.id, unread_only=True)
    for notification in notifications:
        if notification.type == sampledb.logic.notifications.NotificationType.RECEIVED_OBJECT_PERMISSIONS_REQUEST:
            assert notification.data['requester_id'] == new_user_id
            assert notification.data['object_id'] == object.id
            break
    else:
        assert False


def test_request_object_permissions_with_enough_permissions(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.post(flask_server.base_url + 'objects/{}/permissions/request'.format(object.object_id), allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'] == '/objects/{}'.format(object.object_id)
    notifications = sampledb.logic.notifications.get_notifications(user.id, unread_only=True)
    for notification in notifications:
        assert notification.type != sampledb.logic.notifications.NotificationType.RECEIVED_OBJECT_PERMISSIONS_REQUEST



def test_get_object_edit_form(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    assert 'Example' in r.content.decode('utf-8')
    assert 'Save' in r.content.decode('utf-8')


def test_get_object_edit_form_read_permissions(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@example.com', type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=object.object_id, user_id=new_user_id, permissions=sampledb.logic.object_permissions.Permissions.READ)
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user_id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 403


def test_get_object_version(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/versions/0'.format(object.object_id))
    assert r.status_code == 200
    assert 'Example' in r.content.decode('utf-8')
    assert 'Save' not in r.content.decode('utf-8')


def test_get_object_version_no_permissions(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@example.com', type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user_id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/versions/0'.format(object.object_id))
    assert r.status_code == 403


def test_get_object_versions(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/versions/'.format(object.object_id))
    assert r.status_code == 200
    assert 'objects/{}/versions/0'.format(object.object_id) in r.content.decode('utf-8')


def test_edit_object(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    object_data = json.load(open(os.path.join(OBJECTS_DIR, 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data=object_data,
        user_id=user.id,
        action_id=action.id
    )

    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user.id)
        object_log_entries = sampledb.logic.object_log.get_object_log_entries(object.object_id)
        assert len(user_log_entries) == 1
        assert len(object_log_entries) == 1
        creation_user_log_entry = user_log_entries[0]
        creation_object_log_entry = object_log_entries[0]
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'action_submit': 'action_submit', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__checkbox__hidden': 'checkbox exists', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__substrate__text': 'GaAs', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__created__datetime': '2017-02-24 11:56:00', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__name__text': 'OMBE-100', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1', 'object__dropdown__text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    object = sampledb.logic.objects.get_object(object_id=object.object_id, version_id=1)
    assert object is not None
    assert object.data['name']['text'] == 'OMBE-100'
    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user.id)
        user_log_entries.sort(key=lambda log_entry: log_entry.utc_datetime)
        assert len(user_log_entries) == 2
        assert user_log_entries[0].type == sampledb.models.UserLogEntryType.CREATE_OBJECT
        assert user_log_entries[0].user_id == user.id
        assert user_log_entries[0].data == creation_user_log_entry.data
        assert user_log_entries[1].type == sampledb.models.UserLogEntryType.EDIT_OBJECT
        assert user_log_entries[1].user_id == user.id
        assert user_log_entries[1].data == {
            'object_id': object.object_id,
            'version_id': object.version_id
        }
        object_log_entries = sampledb.logic.object_log.get_object_log_entries(object.object_id)
        object_log_entries.sort(key=lambda log_entry: log_entry.utc_datetime)
        assert len(object_log_entries) == 2
        assert object_log_entries[0].type == sampledb.models.ObjectLogEntryType.CREATE_OBJECT
        assert object_log_entries[0].user_id == user.id
        assert object_log_entries[0].object_id == object.object_id
        assert object_log_entries[0].data == creation_object_log_entry.data
        assert object_log_entries[1].type == sampledb.models.ObjectLogEntryType.EDIT_OBJECT
        assert object_log_entries[1].user_id == user.id
        assert object_log_entries[1].object_id == object.object_id
        assert object_log_entries[1].data == {
            'version_id': object.version_id
        }


def test_edit_object_action_add(flask_server, driver, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    object_data = json.load(open(os.path.join(OBJECTS_DIR, 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data=object_data,
        user_id=user.id,
        action_id=action.id
    )

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'objects/{object.object_id}?mode=edit')

    assert 'object__multilayer__2__films__0__elements__1' not in driver.page_source
    driver.find_element(By.ID, 'action_object__multilayer__2__films__0__elements__?__add').click()
    assert 'object__multilayer__2__films__0__elements__1' in driver.page_source


def test_edit_object_array_buttons(flask_server, driver, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    object_data = json.load(open(os.path.join(OBJECTS_DIR, 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data=object_data,
        user_id=user.id,
        action_id=action.id
    )

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'objects/{object.object_id}?mode=edit')

    array_buttons = driver.execute_script("return window.arrayButtons")
    assert 'action_object__multilayer__2__films__0__elements__?__add' not in array_buttons
    driver.find_element(By.ID, 'action_object__multilayer__2__films__0__elements__?__add').click()
    array_buttons = driver.execute_script("return window.arrayButtons")
    assert 'action_object__multilayer__2__films__0__elements__?__add' in array_buttons
    assert 'action_object__multilayer__2__films__0__elements__1__delete' not in array_buttons
    driver.find_element(By.ID, 'action_object__multilayer__2__films__0__elements__1__delete').click()
    array_buttons = driver.execute_script("return window.arrayButtons")
    assert 'action_object__multilayer__2__films__0__elements__1__delete' in array_buttons


def test_edit_object_action_delete(flask_server, driver, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    object_data = json.load(open(os.path.join(OBJECTS_DIR, 'ombe-1.sampledb.json'), encoding="utf-8"))
    schema['properties']['multilayer']['items']['properties']['films']['items']['required'] = ['elements']
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data=object_data,
        user_id=user.id,
        action_id=action.id
    )

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'objects/{object.object_id}?mode=edit')

    # Try violating minItems first
    assert driver.find_element(By.ID, 'action_object__multilayer__2__films__0__elements__0__delete')
    driver.find_element(By.ID, 'action_object__multilayer__2__films__0__elements__0__delete').click()
    assert driver.find_element(By.ID, 'action_object__multilayer__2__films__0__elements__0__delete')

    # Delete something that may actually be deleted
    assert driver.find_element(By.ID, 'action_object__multilayer__3__delete')
    driver.find_element(By.ID, 'action_object__multilayer__3__delete').click()
    assert not driver.find_elements(By.ID, 'action_object__multilayer__3__delete')


def test_new_object(flask_server, driver, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'objects/new?action_id={action.id}')

    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []

    driver.find_element(By.ID, 'action_object__multilayer__?__add').click()
    driver.find_element(By.ID, 'action_object__multilayer__?__add').click()
    driver.find_element(By.ID, 'action_object__multilayer__?__add').click()
    driver.find_element(By.ID, 'action_object__multilayer__2__films__?__add').click()

    driver.find_element(By.NAME, "object__name__text_en").send_keys('3')

    driver.find_element(By.XPATH, "//select[@name='object__dropdown__text']/following-sibling::button").click()
    driver.find_element(By.XPATH, "//select[@name='object__dropdown__text']/following-sibling::div/div/ul/li/a/span[text()='Option A']/parent::a/parent::li").click()

    driver.find_element(By.NAME, 'object__substrate__text_en').send_keys("Ag")

    with wait_for_page_load(driver):
        driver.find_element(By.NAME, 'action_submit').click()

    assert len(sampledb.logic.objects.get_objects()) == 1
    object = sampledb.logic.objects.get_objects()[0]
    assert len(object.data['multilayer']) == 4
    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user.id)
        assert len(user_log_entries) == 1
        assert user_log_entries[0].type == sampledb.models.UserLogEntryType.CREATE_OBJECT
        assert user_log_entries[0].user_id == user.id
        assert user_log_entries[0].data == {
            'object_id': object.object_id
        }
        object_log_entries = sampledb.logic.object_log.get_object_log_entries(object.object_id)
        assert len(object_log_entries) == 1
        assert object_log_entries[0].type == sampledb.models.ObjectLogEntryType.CREATE_OBJECT
        assert object_log_entries[0].user_id == user.id
        assert object_log_entries[0].object_id == object.object_id
        assert object_log_entries[0].data == {}


def test_new_object_batch(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '3', 'input_first_number_batch': '0', 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    objects = sampledb.logic.objects.get_objects()
    assert len(objects) == 3
    assert objects[2].data['name']['text']['en'] == "OMBE-100-000"
    assert objects[1].data['name']['text']['en'] == "OMBE-100-001"
    assert objects[0].data['name']['text']['en'] == "OMBE-100-002"


def test_new_object_batch_invalid_number(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': 'invalid', 'input_first_number_batch': '1', 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0


def test_new_object_batch_float_number(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '2.0', 'input_first_number_batch': '1', 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 2


def test_new_object_batch_invalid_float_number(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '2.5', 'input_first_number_batch': '1', 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0


def test_new_object_batch_number_exceeds_max(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': str(flask_server.app.config['MAX_BATCH_SIZE'] + 1), 'input_first_number_batch': '1', 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0


def test_new_object_batch_number_below_one(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '0', 'input_first_number_batch': '1', 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0


def test_new_object_batch_number_below_one(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '0', 'input_first_number_batch': '1', 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0


def test_new_object_batch_invalid_first_number(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '3', 'input_first_number_batch': 'invalid', 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0


def test_new_object_batch_invalid_float_first_number(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '3', 'input_first_number_batch': '2.3', 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0


def test_new_object_batch_float_first_number(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '3', 'input_first_number_batch': '1e2', 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    objects = sampledb.logic.objects.get_objects()
    assert len(objects) == 3
    assert objects[2].data['name']['text']['en'] == "OMBE-100-100"
    assert objects[1].data['name']['text']['en'] == "OMBE-100-101"
    assert objects[0].data['name']['text']['en'] == "OMBE-100-102"


def test_new_object_javascript_fields_array(flask_server, driver, user):
    schema = {
        "title": "Javascript Fields",
        "type": "object",
        "properties": {
            "name": {
                "title": "Object Name",
                "type": "text"
            },
            "datetime": {
                "title": "Datetime",
                "type": "array",
                "style": "list",
                "items": {
                    "title": "Datetime",
                    "type": "datetime"
                }
            },
            "obj_ref": {
                "title": "Object Reference",
                "type": "array",
                "style": "list",
                "items": {
                    "title": "Object Reference",
                    "type": "object_reference"
                }
            },
            "sample": {
                "title": "Samples",
                "type": "array",
                "style": "list",
                "items": {
                    "title": "Sample",
                    "type": "sample"
                }
            },
            "choices": {
                "title": "Choices",
                "type": "array",
                "style": "list",
                "items": {
                    "title": "Choices",
                    "type": "text",
                    "choices": ["A", "B", "C", "D"]
                }
            }
        },
        "required": ["name"]
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )

    data = {'name': {'_type': 'text', 'text': 'object_version_0'}}
    example_object = sampledb.logic.objects.create_object(
        data=data,
        user_id=user.id,
        action_id=action.id
    )

    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Javascript Fields',
        description=''
    )

    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)

    driver.get(f"{flask_server.base_url}users/{user.id}/autologin")
    driver.get(f"{flask_server.base_url}objects/new?action_id={action.id}")

    assert len(sampledb.logic.objects.get_objects()) == 1

    driver.find_element(By.ID, 'action_object__datetime__?__add').click()
    driver.find_element(By.ID, 'action_object__obj_ref__?__add').click()
    driver.find_element(By.ID, 'action_object__sample__?__add').click()
    driver.find_element(By.ID, 'action_object__choices__?__add').click()

    assert not driver.find_element(By.CSS_SELECTOR, '[data-array-container="list"][data-id-prefix="object__datetime_"] [data-array-item="list"]:not(.array-template)').find_elements(By.CLASS_NAME, 'bootstrap-datetimepicker-widget')
    driver.find_element(By.CSS_SELECTOR, '[data-array-container="list"][data-id-prefix="object__datetime_"] [data-array-item="list"]:not(.array-template) .input-group-addon').click()
    assert driver.find_element(By.CSS_SELECTOR, '[data-array-container="list"][data-id-prefix="object__datetime_"] [data-array-item="list"]:not(.array-template)').find_elements(By.CLASS_NAME, 'bootstrap-datetimepicker-widget') is not None

    datetime = driver.execute_script("return $('[name=\"object__datetime__0__datetime\"]').val()")

    driver.find_element(By.XPATH, '//select[@name="object__obj_ref__0__oid"]/following-sibling::button').click()
    driver.find_element(By.XPATH, f'//select[@name="object__obj_ref__0__oid"]/following-sibling::div/div/ul/li/a/span[text()[contains(.,"{example_object.id}")]]/parent::a/parent::li').click()

    driver.find_element(By.XPATH, '//select[@name="object__sample__0__oid"]/following-sibling::button').click()
    driver.find_element(By.XPATH, f'//select[@name="object__sample__0__oid"]/following-sibling::div/div/ul/li/a/span[text()[contains(.,"{example_object.id}")]]/parent::a/parent::li').click()

    driver.find_element(By.XPATH, '//select[@name="object__choices__0__text"]/following-sibling::button').click()
    driver.find_element(By.XPATH, '//select[@name="object__choices__0__text"]/following-sibling::div/div/ul/li/a/span[text()="D"]/parent::a/parent::li').click()

    with wait_for_page_load(driver):
        driver.find_element(By.NAME, 'action_submit').click()

    assert len(sampledb.logic.objects.get_objects()) == 2

    object_id = int(driver.current_url.split('/')[-1])
    object = sampledb.logic.objects.get_object(object_id)

    assert object.data['datetime'][0]['utc_datetime'] == datetime
    assert object.data['obj_ref'][0]['object_id'] == example_object.id
    assert object.data['sample'][0]['object_id'] == example_object.id
    assert object.data['choices'][0]['text'] == 'D'


def test_restore_object_version(flask_server, user):
    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    data = {'name': {'_type': 'text', 'text': 'object_version_0'}}
    object = sampledb.logic.objects.create_object(
        data=data,
        user_id=user.id,
        action_id=action.id
    )
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'object_version_0'
    data['name']['text'] = 'object_version_1'
    sampledb.models.Objects.update_object(object.object_id, data=data, schema=schema, user_id=user.id)
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 0))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    r = session.post(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 0), data={'csrf_token': csrf_token})
    assert r.status_code == 200

    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'object_version_0'


def test_restore_object_version_invalid_data(flask_server, user):
    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    data = {'name': {'_type': 'text', 'text': 'object_version_0'}}
    object = sampledb.logic.objects.create_object(
        data=data,
        user_id=user.id,
        action_id=action.id
    )
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'object_version_0'
    data['name']['text'] = 'object_version_1'
    sampledb.models.Objects.update_object(object.object_id, data=data, schema=schema, user_id=user.id)
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(42, 0))
    assert r.status_code == 404
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    r = session.get(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 2))
    assert r.status_code == 404
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    r = session.get(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 0))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']

    r = session.post(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(42, 0), data={'csrf_token': csrf_token})
    assert r.status_code == 404
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    r = session.post(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 2), data={'csrf_token': csrf_token})
    assert r.status_code == 404
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    r = session.post(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 1), data={'csrf_token': csrf_token})
    assert r.status_code == 404
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'


def test_update_object_permissions(flask_server, user):
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
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
    })
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    data = {'name': {'_type': 'text', 'text': 'object_version_0'}}
    object = sampledb.logic.objects.create_object(
        data=data,
        user_id=user.id,
        action_id=action.id
    )

    current_permissions = sampledb.logic.object_permissions.get_object_permissions_for_users(object.object_id)
    assert current_permissions == {
        user.id: sampledb.logic.object_permissions.Permissions.GRANT
    }
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object.object_id)

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    user_csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'user_permissions-0-csrf_token'})['value']

    form_data = {
        'edit_permissions': 'edit_permissions',
        'csrf_token': csrf_token,
        'all_user_permissions': 'read',
        'anonymous_user_permissions': 'none',
        'user_permissions-0-csrf_token': user_csrf_token,
        'user_permissions-0-user_id': str(user.id),
        'user_permissions-0-permissions': 'grant',
    }
    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user.id)
        assert len(user_log_entries) == 1
        assert user_log_entries[0].type == sampledb.logic.user_log.UserLogEntryType.CREATE_OBJECT

    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    current_permissions = sampledb.logic.object_permissions.get_object_permissions_for_users(object.object_id)
    assert current_permissions == {
        user.id: sampledb.logic.object_permissions.Permissions.GRANT
    }
    assert sampledb.models.Permissions.READ in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object.object_id)
    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user.id)
        user_log_entries.sort(key=lambda log_entry: log_entry.utc_datetime)
        assert len(user_log_entries) == 2
        assert user_log_entries[0].type == sampledb.models.UserLogEntryType.CREATE_OBJECT
        assert user_log_entries[0].user_id == user.id
        assert user_log_entries[1].type == sampledb.models.UserLogEntryType.EDIT_OBJECT_PERMISSIONS
        assert user_log_entries[1].user_id == user.id
        assert user_log_entries[1].data == {
            'object_id': object.object_id
        }

    form_data = {
        'edit_permissions': 'edit_permissions',
        'csrf_token': csrf_token,
        'all_user_permissions': 'none',
        'anonymous_user_permissions': 'none',
        'user_permissions-0-csrf_token': user_csrf_token,
        'user_permissions-0-user_id': str(user.id + 1000),
        'user_permissions-0-permissions': 'read',
    }
    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    current_permissions = sampledb.logic.object_permissions.get_object_permissions_for_users(object.object_id)
    assert current_permissions == {
        user.id: sampledb.logic.object_permissions.Permissions.GRANT
    }
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object.object_id)

    form_data = {
        'edit_permissions': 'edit_permissions',
        'csrf_token': csrf_token,
        'all_user_permissions': 'none',
        'anonymous_user_permissions': 'none',
        'user_permissions-0-csrf_token': user_csrf_token,
        'user_permissions-0-user_id': str(user.id),
        'user_permissions-0-permissions': 'read',
    }
    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    current_permissions = sampledb.logic.object_permissions.get_object_permissions_for_users(object.object_id)
    assert current_permissions == {
        user.id: sampledb.logic.object_permissions.Permissions.READ
    }
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object.object_id)

    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 403


def test_object_permissions_add_user(flask_server, user):
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
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
    })
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    data = {'name': {'_type': 'text', 'text': 'object_version_0'}}
    object = sampledb.logic.objects.create_object(
        data=data,
        user_id=user.id,
        action_id=action.id
    )

    current_permissions = sampledb.logic.object_permissions.get_object_permissions_for_users(object.object_id)
    assert current_permissions == {
        user.id: sampledb.logic.object_permissions.Permissions.GRANT
    }
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object.object_id)

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find_all('input', {'name': 'csrf_token'})[1]['value']

    with flask_server.app.app_context():
        user2 = sampledb.models.User(name="New User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user2)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user2.id is not None

    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user.id)
        user_log_entries.sort(key=lambda log_entry: log_entry.utc_datetime)
        assert len(user_log_entries) == 1
        assert user_log_entries[0].type == sampledb.models.UserLogEntryType.CREATE_OBJECT
        assert user_log_entries[0].user_id == user.id
    form_data = {
        'add_user_permissions': 'add_user_permissions',
        'csrf_token': csrf_token,
        'user_id': str(user2.id),
        'permissions': 'write',
    }
    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    current_permissions = sampledb.logic.object_permissions.get_object_permissions_for_users(object.object_id)
    assert current_permissions == {
        user.id: sampledb.logic.object_permissions.Permissions.GRANT,
        user2.id: sampledb.logic.object_permissions.Permissions.WRITE
    }
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object.object_id)
    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user.id)
        user_log_entries.sort(key=lambda log_entry: log_entry.utc_datetime)
        assert len(user_log_entries) == 2
        assert user_log_entries[0].type == sampledb.models.UserLogEntryType.CREATE_OBJECT
        assert user_log_entries[0].user_id == user.id
        assert user_log_entries[1].type == sampledb.models.UserLogEntryType.EDIT_OBJECT_PERMISSIONS
        assert user_log_entries[1].user_id == user.id
        assert user_log_entries[1].data == {
            'object_id': object.object_id
        }


def test_object_permissions_add_group(flask_server, user):
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
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
    })
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    data = {'name': {'_type': 'text', 'text': 'object_version_0'}}
    object = sampledb.logic.objects.create_object(
        data=data,
        user_id=user.id,
        action_id=action.id
    )

    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id).id

    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object.object_id) == {}

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find_all('input', {'name': 'csrf_token'})[2]['value']

    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user.id)
        user_log_entries.sort(key=lambda log_entry: log_entry.utc_datetime)
        assert len(user_log_entries) == 1
        assert user_log_entries[0].type == sampledb.models.UserLogEntryType.CREATE_OBJECT
        assert user_log_entries[0].user_id == user.id
    form_data = {
        'add_group_permissions': 'add_group_permissions',
        'csrf_token': csrf_token,
        'group_id': str(group_id),
        'permissions': 'write',
    }
    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object.object_id) == {
        group_id: sampledb.logic.object_permissions.Permissions.WRITE
    }

    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user.id)
        user_log_entries.sort(key=lambda log_entry: log_entry.utc_datetime)
        assert len(user_log_entries) == 2
        assert user_log_entries[0].type == sampledb.models.UserLogEntryType.CREATE_OBJECT
        assert user_log_entries[0].user_id == user.id
        assert user_log_entries[1].type == sampledb.models.UserLogEntryType.EDIT_OBJECT_PERMISSIONS
        assert user_log_entries[1].user_id == user.id
        assert user_log_entries[1].data == {
            'object_id': object.object_id
        }


def test_edit_object_invalid_data(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    object_data = json.load(open(os.path.join(OBJECTS_DIR, 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data=object_data,
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    # contains invalid object name OBME-X
    form_data = {'csrf_token': csrf_token, 'action_submit': 'action_submit', 'object__name__text': 'OMBE-X', 'object__dropdown__text': 'Option A', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__3__repetitions__magnitude': '1', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': ''}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_object_versions(object.id)) == 1


def test_create_object_similar_property_names(flask_server, user):
    schema = {
      "title": "Object with one property name being a prefix of another property name",
      "type": "object",
      "properties": {
        "name": {
          "title": "First Name",
          "type": "text"
        },
        "name_2": {
          "title": "Second Name",
          "type": "text"
        }
      },
      "propertyOrder": ["name", "name_2"],
      "required": ["name", "name_2"]
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    assert len(sampledb.logic.objects.get_objects()) == 0
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new?action_id={}'.format(action.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    input_fields = document.find_all('input')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'action_submit': 'action_submit'}

    for input_field in input_fields:
        if input_field['name'].startswith('object') and not input_field['name'].endswith('__text_languages'):
            value = 'Test'
            if 'name_2' in input_field['name']:
                value = 'Test-2'
            form_data[input_field['name']] = value
    form_data['csrf_token'] = csrf_token
    r = session.post(flask_server.base_url + 'objects/new?action_id={}'.format(action.id), data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 1
    assert sampledb.logic.objects.get_objects()[0].data == {
        "name": {
            "_type": "text",
            "text": {
                'en': "Test"
            }
        },
        "name_2": {
            "_type": "text",
            "text": {
                'en': "Test-2"
            }
        }
    }


def test_edit_object_similar_property_names(flask_server, user):
    schema = {
      "title": "Object with one property name being a prefix of another property name",
      "type": "object",
      "properties": {
        "name": {
          "title": "First Name",
          "type": "text"
        },
        "name_2": {
          "title": "Second Name",
          "type": "text"
        }
      },
      "propertyOrder": ["name", "name_2"],
      "required": ["name", "name_2"]
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data={
            "name": {
                "_type": "text",
                "text": "Name-1"
            },
            "name_2": {
                "_type": "text",
                "text": "Name-2"
            }
        },
        user_id=user.id,
        action_id=action.id
    )
    assert len(sampledb.logic.objects.get_objects()) == 1
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    input_fields = document.find_all('input')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'action_submit': 'action_submit'}

    for input_field in input_fields:
        if input_field['name'].startswith('object') and not input_field['name'].endswith('__text_languages'):
            value = 'Test'
            if 'name_2' in input_field['name']:
                value = 'Test-2'
            form_data[input_field['name']] = value
    form_data['csrf_token'] = csrf_token
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.id), data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 1
    assert sampledb.logic.objects.get_object(object.id).data == {
        "name": {
            "_type": "text",
            "text": {
                'en': "Test"
            }
        },
        "name_2": {
            "_type": "text",
            "text": {
                'en': "Test-2"
            }
        }
    }


def test_copy_object(flask_server, user):
    schema = {
      "title": "Object",
      "type": "object",
      "properties": {
        "name": {
          "title": "First Name",
          "type": "text"
        },
        "name2": {
          "title": "Second Name",
          "type": "text"
        }
      },
      "propertyOrder": ["name", "name2"],
      "required": ["name", "name2"]
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    name = 'Example1'
    object = sampledb.logic.objects.create_object(
            data={'name': {'_type': 'text', 'text': name}, 'name2': {'_type': 'text', 'text': name}},
            user_id=user.id,
            action_id=action.id
        )
    schema["properties"]["name2"]["type"] = "bool"
    sampledb.logic.actions.update_action(
        action_id=action.id,
        schema=schema
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'previous_object_id': object.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 1
    with flask_server.app.app_context():
        assert len(sampledb.logic.user_log.get_user_log_entries(user.id)) == 1
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    object_name = document.find('input', {'name': 'object__name2__text_en'})['value']
    assert object_name == name
    form_data = {'csrf_token': csrf_token, 'action_submit': 'action_submit', 'object__name__text_en': name, 'object__name2__text_en': name}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': object.action_id, 'previous_object_id': object.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 2
    new_object = sampledb.logic.objects.get_objects()[0]
    assert object.data["name2"]["text"] == name
    with flask_server.app.app_context():
        user_log_entries = sampledb.logic.user_log.get_user_log_entries(user.id)
        assert len(user_log_entries) == 2
        assert user_log_entries[0].type == sampledb.models.UserLogEntryType.CREATE_OBJECT
        assert user_log_entries[0].user_id == user.id
        assert user_log_entries[0].data == {
            'object_id': new_object.object_id
        }
        object_log_entries = sampledb.logic.object_log.get_object_log_entries(new_object.object_id)
        assert len(object_log_entries) == 1
        assert object_log_entries[0].type == sampledb.models.ObjectLogEntryType.CREATE_OBJECT
        assert object_log_entries[0].user_id == user.id
        assert object_log_entries[0].object_id == new_object.object_id
        assert object_log_entries[0].data == {
            'previous_object_id': object.id
        }


def test_edit_empty_nested_array(flask_server, user):
    schema = {
        "type": "object",
        "title": "Nested Array Test",
        "properties": {
            "name": {
                "type": "text",
                "title": "Sample Name",
                "default": "",
                "maxLength": 100,
                "minLength": 1
            },
            "nested_array": {
                "type": "array",
                "title": "Nested Array",
                "style": "table",
                "minItems": 0,
                "items": {
                    "type": "array",
                    "title": "Inner Array",
                    "maxItems": 5,
                    "minItems": 1,
                    "items": {
                        "type": "text",
                        "title": "Entry",
                        "minLength": 0,
                        "multiline": True
                    }
                }
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "nested_array"],
        "displayProperties": []
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    object = sampledb.logic.objects.create_object(
        data={"name": {"text": "Test", "_type": "text"}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}'.format(object.id), params={'mode': 'edit'})
    assert r.status_code == 200


def test_new_object_with_instrument_log_entry(flask_server, user):
    with flask_server.app.app_context():
        instrument = sampledb.logic.instruments.create_instrument()
        sampledb.logic.instrument_translations.set_instrument_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            instrument_id=instrument.id,
            name="Example Instrument",
            description="This is an example instrument"
        )
        sampledb.logic.instruments.add_instrument_responsible_user(instrument.id, user.id)
        category = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument.id,
            'Error',
            sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
        )
        assert instrument.id is not None
        assert category.id is not None
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema,
        instrument_id=instrument.id
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    # create instrument log entry for new object
    form_data['create_instrument_log_entry'] = 'create_instrument_log_entry'
    form_data['instrument_log_categories'] = [str(category.id), '42']
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 1
    object = sampledb.logic.objects.get_objects()[0]
    with flask_server.app.app_context():
        instrument_log_entries = sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)
        assert len(instrument_log_entries) == 1
        log_entry = instrument_log_entries[0]
        assert log_entry.user_id == user.id
        assert log_entry.versions[0].content == ''
        assert log_entry.versions[0].categories == [category]
        assert len(log_entry.object_attachments) == 1
        assert log_entry.object_attachments[0].object_id == object.id


def test_object_federation_references(flask_server, user, simple_object, component):
    fed_user = sampledb.logic.users.create_user(fed_id=35, component_id=component.id, name='Example User', email=None, type=sampledb.models.UserType.FEDERATION_USER)
    fed_data = deepcopy(simple_object.data)
    fed_data['name']['text'] = 'Imported'
    fed_object = sampledb.logic.objects.insert_fed_object_version(
        fed_object_id=42,
        fed_version_id=0,
        component_id=component.id,
        action_id=None,
        user_id=fed_user.id,
        data=fed_data,
        schema=simple_object.schema,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=fed_object.object_id, user_id=user.id, permissions=sampledb.logic.object_permissions.Permissions.READ)

    data = deepcopy(REFERENCES_DATA_FRAME)
    data['user1']['user_id'] = fed_user.id    # imported user
    data['user2']['user_id'] = 12        # unknown user, unknown component
    data['user2']['component_uuid'] = UUID_2
    data['user3']['user_id'] = user.id      # local user
    data['user4']['user_id'] = fed_user.fed_id + 1  # unknown user, known component
    data['user4']['component_uuid'] = component.uuid

    data['object1']['object_id'] = fed_object.object_id  # imported object
    data['object2']['object_id'] = 6  # unknown object, unknown component
    data['object2']['component_uuid'] = UUID_2
    data['object3']['object_id'] = simple_object.object_id  # local object
    data['object4']['object_id'] = fed_object.fed_object_id + 1  # unknown object, known component
    data['object4']['component_uuid'] = component.uuid

    data['userlist'][0]['user_id'] = fed_user.id  # imported user
    data['userlist'][1]['user_id'] = 12  # unknown user, unknown component
    data['userlist'][1]['component_uuid'] = UUID_2
    data['userlist'][2]['user_id'] = user.id  # local user
    data['userlist'][3]['user_id'] = fed_user.fed_id + 1  # unknown user, known component
    data['userlist'][3]['component_uuid'] = component.uuid

    data['objectlist'][0]['object_id'] = fed_object.object_id  # imported object
    data['objectlist'][1]['object_id'] = 6  # unknown object, unknown component
    data['objectlist'][1]['component_uuid'] = UUID_2
    data['objectlist'][2]['object_id'] = simple_object.object_id  # local object
    data['objectlist'][3]['object_id'] = fed_object.fed_object_id + 1  # unknown object, known component
    data['objectlist'][3]['component_uuid'] = component.uuid

    data['usertable'][0][0]['user_id'] = fed_user.id  # imported user
    data['usertable'][0][1]['user_id'] = 12  # unknown user, unknown component
    data['usertable'][0][1]['component_uuid'] = UUID_2
    data['usertable'][1][0]['user_id'] = user.id  # local user
    data['usertable'][1][1]['user_id'] = fed_user.fed_id + 1  # unknown user, known component
    data['usertable'][1][1]['component_uuid'] = component.uuid

    data['objecttable'][0][0]['object_id'] = fed_object.object_id  # imported object
    data['objecttable'][0][1]['object_id'] = 6  # unknown object, unknown component
    data['objecttable'][0][1]['component_uuid'] = UUID_2
    data['objecttable'][1][0]['object_id'] = simple_object.object_id  # local object
    data['objecttable'][1][1]['object_id'] = fed_object.fed_object_id + 1  # unknown object, known component
    data['objecttable'][1][1]['component_uuid'] = component.uuid

    object = sampledb.logic.objects.insert_fed_object_version(
        fed_object_id=3,
        fed_version_id=0,
        component_id=component.id,
        action_id=None,
        user_id=fed_user.id,
        data=data,
        schema=REFERENCES_SCHEMA,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=object.object_id, user_id=user.id, permissions=sampledb.logic.object_permissions.Permissions.READ)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/' + str(object.object_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    # headline
    h1_fed_link = document.find('h1').find('a')
    h1_fed_symbol = h1_fed_link.find('i')
    assert h1_fed_link['href'] == component.address + '/objects/' + str(object.fed_object_id)
    assert 'fa' in h1_fed_symbol['class']
    assert 'fa-share-alt' in h1_fed_symbol['class']
    assert h1_fed_symbol['data-toggle'] == 'tooltip'
    assert h1_fed_symbol['title'] == '#' + str(object.fed_object_id) + ' @ ' + component.name

    # object name
    rows = document.find_all('div', class_='row')
    assert rows[2].find('div').getText().strip() == object.name['en']

    # imported user
    assert rows[3].find('div').getText().strip() == fed_user.name + ' (#' + str(fed_user.id) + ')'
    links = rows[3].find('div').find_all('a')
    assert len(links) == 2
    assert links[0].getText().strip() == fed_user.name + ' (#' + str(fed_user.id) + ')'
    assert links[0]['href'] == '/users/' + str(fed_user.id)
    assert links[1]['href'] == component.address + '/users/' + str(fed_user.fed_id)
    assert links[1].find('i')['data-toggle'] == 'tooltip'
    assert links[1].find('i')['title'] == '#' + str(fed_user.fed_id) + ' @ ' + component.name
    assert 'fa' in links[1].find('i')['class']
    assert 'fa-share-alt' in links[1].find('i')['class']

    # imported object
    assert rows[4].find('div').getText().strip() == fed_object.name + ' (#' + str(fed_object.object_id) + ')'
    links = rows[4].find('div').find_all('a')
    assert len(links) == 2
    assert links[0].getText().strip() == fed_object.name + ' (#' + str(fed_object.object_id) + ')'
    assert links[0]['href'] == '/objects/' + str(fed_object.object_id)
    assert links[1]['href'] == component.address + '/objects/' + str(fed_object.fed_object_id)
    assert links[1].find('i')['data-toggle'] == 'tooltip'
    assert links[1].find('i')['title'] == '#' + str(fed_object.fed_object_id) + ' @ ' + component.name
    assert 'fa' in links[1].find('i')['class']
    assert 'fa-share-alt' in links[1].find('i')['class']

    # unknown user, unknown DB
    assert rows[5].find('div').getText().strip() == '#12 @ Unknown database (' + UUID_2[:8] + ')'
    assert len(rows[5].find('div').find_all('a')) == 0
    assert rows[5].find('div').find('i')['data-toggle'] == 'tooltip'
    assert rows[5].find('div').find('i')['title'] == '#12 @ Unknown database (' + UUID_2[:8] + ')'
    assert 'fa' in rows[5].find('div').find('i')['class']
    assert 'fa-share-alt' in rows[5].find('div').find('i')['class']

    # unknown object, unknown DB
    assert rows[6].find('div').getText().strip() == '#6 @ Unknown database (' + UUID_2[:8] + ')'
    assert len(rows[6].find('div').find_all('a')) == 0
    assert rows[6].find('div').find('i')['data-toggle'] == 'tooltip'
    assert rows[6].find('div').find('i')['title'] == '#6 @ Unknown database (' + UUID_2[:8] + ')'
    assert 'fa' in rows[6].find('div').find('i')['class']
    assert 'fa-share-alt' in rows[6].find('div').find('i')['class']

    # local user
    assert rows[7].find('div').getText().strip() == user.name + ' (#' + str(user.id) + ')'
    links = rows[7].find('div').find_all('a')
    assert len(links) == 1
    assert links[0].getText().strip() == user.name + ' (#' + str(user.id) + ')'
    assert links[0]['href'] == '/users/' + str(user.id)

    # local object
    assert rows[8].find('div').getText().strip() == simple_object.name + ' (#' + str(simple_object.object_id) + ')'
    links = rows[8].find('div').find_all('a')
    assert len(links) == 1
    assert links[0].getText().strip() == simple_object.name + ' (#' + str(simple_object.object_id) + ')'
    assert links[0]['href'] == '/objects/' + str(simple_object.object_id)

    # unknown user, known DB
    assert rows[9].find('div').getText().strip() == '#' + str(fed_user.fed_id + 1) + ' @ ' + component.get_name()
    links = rows[9].find('div').find_all('a')
    assert len(links) == 1
    assert links[0]['href'] == component.address + '/users/' + str(fed_user.fed_id + 1)
    assert links[0].find('i')['data-toggle'] == 'tooltip'
    assert links[0].find('i')['title'] == '#' + str(fed_user.fed_id + 1) + ' @ ' + component.name
    assert 'fa' in links[0].find('i')['class']
    assert 'fa-share-alt' in links[0].find('i')['class']

    # unknown object, known DB
    assert rows[10].find('div').getText().strip() == '#' + str(fed_object.fed_object_id + 1) + ' @ ' + component.get_name()
    links = rows[10].find('div').find_all('a')
    assert len(links) == 1
    assert links[0]['href'] == component.address + '/objects/' + str(fed_object.fed_object_id + 1)
    assert links[0].find('i')['data-toggle'] == 'tooltip'
    assert links[0].find('i')['title'] == '#' + str(fed_object.fed_object_id + 1) + ' @ ' + component.name
    assert 'fa' in links[0].find('i')['class']
    assert 'fa-share-alt' in links[0].find('i')['class']

    li = rows[11].find('ul').find_all('li')

    # imported user
    assert li[0].getText().strip() == fed_user.name + ' (#' + str(fed_user.id) + ')'
    links = li[0].find_all('a')
    assert len(links) == 2
    assert links[0].getText().strip() == fed_user.name + ' (#' + str(fed_user.id) + ')'
    assert links[0]['href'] == '/users/' + str(fed_user.id)
    assert links[1]['href'] == component.address + '/users/' + str(fed_user.fed_id)
    assert links[1].find('i')['data-toggle'] == 'tooltip'
    assert links[1].find('i')['title'] == '#' + str(fed_user.fed_id) + ' @ ' + component.name
    assert 'fa' in links[1].find('i')['class']
    assert 'fa-share-alt' in links[1].find('i')['class']

    # unknown user, unknown DB
    assert li[1].getText().strip() == '#12 @ Unknown database (' + UUID_2[:8] + ')'
    assert len(li[1].find_all('a')) == 0
    assert li[1].find('i')['data-toggle'] == 'tooltip'
    assert li[1].find('i')['title'] == '#12 @ Unknown database (' + UUID_2[:8] + ')'
    assert 'fa' in li[1].find('i')['class']
    assert 'fa-share-alt' in li[1].find('i')['class']

    # local user
    assert li[2].getText().strip() == user.name + ' (#' + str(user.id) + ')'
    links = li[2].find_all('a')
    assert len(links) == 1
    assert links[0].getText().strip() == user.name + ' (#' + str(user.id) + ')'
    assert links[0]['href'] == '/users/' + str(user.id)

    # unknown user, known DB
    assert li[3].getText().strip() == '#' + str(fed_user.fed_id + 1) + ' @ ' + component.get_name()
    links = li[3].find_all('a')
    assert len(links) == 1
    assert links[0]['href'] == component.address + '/users/' + str(fed_user.fed_id + 1)
    assert links[0].find('i')['data-toggle'] == 'tooltip'
    assert links[0].find('i')['title'] == '#' + str(fed_user.fed_id + 1) + ' @ ' + component.name
    assert 'fa' in links[0].find('i')['class']
    assert 'fa-share-alt' in links[0].find('i')['class']

    li = rows[12].find('ul').find_all('li')

    # imported object
    assert li[0].getText().strip() == fed_object.name + ' (#' + str(fed_object.object_id) + ')'
    links = li[0].find_all('a')
    assert len(links) == 2
    assert links[0].getText().strip() == fed_object.name + ' (#' + str(fed_object.object_id) + ')'
    assert links[0]['href'] == '/objects/' + str(fed_object.object_id)
    assert links[1]['href'] == component.address + '/objects/' + str(fed_object.fed_object_id)
    assert links[1].find('i')['data-toggle'] == 'tooltip'
    assert links[1].find('i')['title'] == '#' + str(fed_object.fed_object_id) + ' @ ' + component.name
    assert 'fa' in links[1].find('i')['class']
    assert 'fa-share-alt' in links[1].find('i')['class']

    # unknown object, unknown DB
    assert li[1].getText().strip() == '#6 @ Unknown database (' + UUID_2[:8] + ')'  # Object
    assert len(li[1].find_all('a')) == 0
    assert li[1].find('i')['data-toggle'] == 'tooltip'
    assert li[1].find('i')['title'] == '#6 @ Unknown database (' + UUID_2[:8] + ')'
    assert 'fa' in li[1].find('i')['class']
    assert 'fa-share-alt' in li[1].find('i')['class']

    # local object
    assert li[2].getText().strip() == simple_object.name + ' (#' + str(simple_object.object_id) + ')'
    links = li[2].find_all('a')
    assert len(links) == 1
    assert links[0].getText().strip() == simple_object.name + ' (#' + str(simple_object.object_id) + ')'
    assert links[0]['href'] == '/objects/' + str(simple_object.object_id)

    # unknown object, known DB
    assert li[3].getText().strip() == '#' + str(fed_object.fed_object_id + 1) + ' @ ' + component.get_name()
    links = li[3].find_all('a')
    assert len(links) == 1
    assert links[0]['href'] == component.address + '/objects/' + str(fed_object.fed_object_id + 1)
    assert links[0].find('i')['data-toggle'] == 'tooltip'
    assert links[0].find('i')['title'] == '#' + str(fed_object.fed_object_id + 1) + ' @ ' + component.name
    assert 'fa' in links[0].find('i')['class']
    assert 'fa-share-alt' in links[0].find('i')['class']

    tables = document.find_all('table', class_='table')
    td = tables[0].find_all('td')

    # imported user
    assert td[0].getText().strip() == fed_user.name + ' (#' + str(fed_user.id) + ')'
    links = td[0].find_all('a')
    assert len(links) == 2
    assert links[0].getText().strip() == fed_user.name + ' (#' + str(fed_user.id) + ')'
    assert links[0]['href'] == '/users/' + str(fed_user.id)
    assert links[1]['href'] == component.address + '/users/' + str(fed_user.fed_id)
    assert links[1].find('i')['data-toggle'] == 'tooltip'
    assert links[1].find('i')['title'] == '#' + str(fed_user.fed_id) + ' @ ' + component.name
    assert 'fa' in links[1].find('i')['class']
    assert 'fa-share-alt' in links[1].find('i')['class']

    # unknown user, unknown DB
    assert td[1].getText().strip() == '#12 @ Unknown database (' + UUID_2[:8] + ')'
    assert len(td[1].find_all('a')) == 0
    assert td[1].find('i')['data-toggle'] == 'tooltip'
    assert td[1].find('i')['title'] == '#12 @ Unknown database (' + UUID_2[:8] + ')'
    assert 'fa' in td[1].find('i')['class']
    assert 'fa-share-alt' in td[1].find('i')['class']

    # local user
    assert td[2].getText().strip() == user.name + ' (#' + str(user.id) + ')'
    links = td[2].find_all('a')
    assert len(links) == 1
    assert links[0].getText().strip() == user.name + ' (#' + str(user.id) + ')'
    assert links[0]['href'] == '/users/' + str(user.id)

    # unknown user, known DB
    assert td[3].getText().strip() == '#' + str(fed_user.fed_id + 1) + ' @ ' + component.get_name()
    links = td[3].find_all('a')
    assert len(links) == 1
    assert links[0]['href'] == component.address + '/users/' + str(fed_user.fed_id + 1)
    assert links[0].find('i')['data-toggle'] == 'tooltip'
    assert links[0].find('i')['title'] == '#' + str(fed_user.fed_id + 1) + ' @ ' + component.name
    assert 'fa' in links[0].find('i')['class']
    assert 'fa-share-alt' in links[0].find('i')['class']

    td = tables[1].find_all('td')

    # imported object
    assert td[0].getText().strip() == fed_object.name + ' (#' + str(fed_object.object_id) + ')'
    links = td[0].find_all('a')
    assert len(links) == 2
    assert links[0].getText().strip() == fed_object.name + ' (#' + str(fed_object.object_id) + ')'
    assert links[0]['href'] == '/objects/' + str(fed_object.object_id)
    assert links[1]['href'] == component.address + '/objects/' + str(fed_object.fed_object_id)
    assert links[1].find('i')['data-toggle'] == 'tooltip'
    assert links[1].find('i')['title'] == '#' + str(fed_object.fed_object_id) + ' @ ' + component.name
    assert 'fa' in links[1].find('i')['class']
    assert 'fa-share-alt' in links[1].find('i')['class']

    # unknown object, unknown DB
    assert td[1].getText().strip() == '#6 @ Unknown database (' + UUID_2[:8] + ')'  # Object
    assert len(td[1].find_all('a')) == 0
    assert td[1].find('i')['data-toggle'] == 'tooltip'
    assert td[1].find('i')['title'] == '#6 @ Unknown database (' + UUID_2[:8] + ')'
    assert 'fa' in td[1].find('i')['class']
    assert 'fa-share-alt' in td[1].find('i')['class']

    # local object
    assert td[2].getText().strip() == simple_object.name + ' (#' + str(simple_object.object_id) + ')'
    links = td[2].find_all('a')
    assert len(links) == 1
    assert links[0].getText().strip() == simple_object.name + ' (#' + str(simple_object.object_id) + ')'
    assert links[0]['href'] == '/objects/' + str(simple_object.object_id)

    # unknown object, known component
    assert td[3].getText().strip() == '#' + str(fed_object.fed_object_id + 1) + ' @ ' + component.get_name()
    links = td[3].find_all('a')
    assert len(links) == 1
    assert links[0]['href'] == component.address + '/objects/' + str(fed_object.fed_object_id + 1)
    assert links[0].find('i')['data-toggle'] == 'tooltip'
    assert links[0].find('i')['title'] == '#' + str(fed_object.fed_object_id + 1) + ' @ ' + component.name
    assert 'fa' in links[0].find('i')['class']
    assert 'fa-share-alt' in links[0].find('i')['class']


def test_update_recipes_for_input(mock_current_user):
    mock_current_user.id = 1

    schema = {
        'type': 'object',
        'title': 'Example Schema',
        'properties': {
            'name': {
                'type': 'text',
                'title': 'Name'
            }
        },
        'required': ['name']
    }
    sampledb.logic.schemas.validate_schema(schema)
    original_schema = deepcopy(schema)
    sampledb.frontend.objects.object_form._update_recipes_for_input(schema)
    assert schema == original_schema
    schema = {
        'type': 'object',
        'title': 'Example Schema',
        'properties': {
            'name': {
                'type': 'text',
                'title': 'Name'
            },
            'simple_text': {
                'type': 'text',
                'title': {'en': 'Simple Text', 'de': 'Einfacher Text'},
                'languages': 'all'
            },
            'multiline_text': {
                'type': 'text',
                'title': {'en': 'Multiline Text', 'de': 'Mehrzeiliger Text'},
                'multiline': True,
                'languages': 'all'
            },
            'markdown_text': {
                'type': 'text',
                'title': {'en': 'Markdown Text', 'de': 'Markdown-Text'},
                'markdown': True,
                'languages': 'all'
            },
            'choices_text': {
                'type': 'text',
                'title': {'en': 'Choices Text', 'de': 'Auswahl-Text'},
                'choices': [
                    {'en': 'Option A', 'de': 'Option A'},
                    {'en': 'Option B', 'de': 'Option B'},
                ],
                'languages': 'all'
            },
            'length_quantity': {
                'type': 'quantity',
                'title': {'en': 'Length Quantity', 'de': 'Langen-Größe'},
                'units': 'm'
            },
            'time_quantity': {
                'type': 'quantity',
                'title': {'en': 'Time Quantity', 'de': 'Zeit-Größe'},
                'units': 'min'
            },
            'percent_quantity': {
                'type': 'quantity',
                'title': {'en': 'Percent Quantity', 'de': 'Prozent-Größe'},
                'units': 'percent'
            },
            'datetime': {
                'type': 'datetime',
                'title': {'en': 'Datetime', 'de': 'Zeitpunkt'}
            },
            'bool': {
                'type': 'bool',
                'title': {'en': 'Boolean', 'de': 'Wahrheitswert'}
            }
        },
        'required': ['name'],
        'recipes': [
            {
                'name': {
                    'en': 'Recipe 1',
                    'de': 'Rezept 1'
                },
                'property_values': {
                    'simple_text': {
                        'text': {
                            'en': 'Text (en)',
                            'de': 'Text (de)'
                        },
                        '_type': 'text'
                    },
                    'multiline_text': {
                        'text': {
                            'en': 'Text (en)',
                            'de': 'Text (de)'
                        },
                        '_type': 'text'
                    },
                    'markdown_text': {
                        'text': {
                            'en': 'Text (en)',
                            'de': 'Text (de)'
                        },
                        '_type': 'text',
                        'is_markdown': True
                    },
                    'choices_text': {
                        'text': {
                            'en': 'Option A',
                            'de': 'Option A'
                        },
                        '_type': 'text'
                    },
                    'length_quantity': {
                        'magnitude_in_base_units': 1.5,
                        'magnitude': 1.5,
                        'units': 'm',
                        '_type': 'quantity'
                    },
                    'time_quantity': {
                        'magnitude_in_base_units': 90,
                        'magnitude': 1.5,
                        'units': 'min',
                        '_type': 'quantity'
                    },
                    'percent_quantity': {
                        'magnitude_in_base_units': 0.15,
                        'magnitude': 15,
                        'units': 'percent',
                        '_type': 'quantity'
                    },
                    'datetime': {
                        'utc_datetime': '2023-01-02 03:04:05',
                        '_type': 'datetime'
                    },
                    'bool': {
                        'value': True,
                        '_type': 'bool'
                    }
                }
            }
        ],
    }
    sampledb.logic.schemas.validate_schema(schema)
    original_schema = deepcopy(schema)
    sampledb.frontend.objects.object_form._update_recipes_for_input(schema)
    original_schema['recipes'][0]['name'] = 'Recipe 1'
    original_schema['recipes'][0]['property_values']['simple_text'] = {
        'title': 'Simple Text',
        'type': 'text',
        'value': {
            'en': 'Text (en)',
            'de': 'Text (de)'
        }
    }
    original_schema['recipes'][0]['property_values']['multiline_text'] = {
        'title': 'Multiline Text',
        'type': 'multiline',
        'value': {
            'en': 'Text (en)',
            'de': 'Text (de)'
        }
    }
    original_schema['recipes'][0]['property_values']['markdown_text'] = {
        'title': 'Markdown Text',
        'type': 'markdown',
        'value': {
            'en': 'Text (en)',
            'de': 'Text (de)'
        }
    }
    original_schema['recipes'][0]['property_values']['choices_text'] = {
        'title': 'Choices Text',
        'type': 'choice',
        'value': {
            'en': 'Option A',
            'de': 'Option A'
        }
    }
    original_schema['recipes'][0]['property_values']['length_quantity'] = {
        'title': 'Length Quantity',
        'type': 'quantity',
        'value': '1.5',
        'units': 'm'
    }
    original_schema['recipes'][0]['property_values']['time_quantity'] = {
        'title': 'Time Quantity',
        'type': 'quantity',
        'value': '01:30',
        'units': 'min'
    }
    original_schema['recipes'][0]['property_values']['percent_quantity'] = {
        'title': 'Percent Quantity',
        'type': 'quantity',
        'value': '15',
        'units': 'percent'
    }
    original_schema['recipes'][0]['property_values']['datetime'] = {
        'title': 'Datetime',
        'type': 'datetime',
        'value': '2023-01-02 03:04:05'
    }
    original_schema['recipes'][0]['property_values']['bool'] = {
        'title': 'Boolean',
        'type': 'bool',
        'value': True
    }
    assert schema == original_schema
