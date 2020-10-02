# coding: utf-8
"""

"""

import os
import json
import requests
import pytest
import itsdangerous
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
import sampledb.logic


SCHEMA_DIR = os.path.abspath(os.path.join(os.path.dirname(sampledb.__file__), 'schemas'))


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def test_get_objects(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    action1 = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    action2 = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    action1 = sampledb.logic.actions.create_action(sampledb.models.ActionType.MEASUREMENT, 'Example Action', '', schema)
    action2 = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    action1 = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    action2 = sampledb.logic.actions.create_action(sampledb.models.ActionType.MEASUREMENT, 'Example Action', '', schema)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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


def test_objects_referencable(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action1 = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    action2 = sampledb.logic.actions.create_action(sampledb.models.ActionType.MEASUREMENT, 'Example Action', '', schema)
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

    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@fz-juelich.de', type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=objects[0].object_id, user_id=new_user_id, permissions=sampledb.logic.object_permissions.Permissions.READ)
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=objects[1].object_id, user_id=new_user_id, permissions=sampledb.logic.object_permissions.Permissions.WRITE)
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=objects[2].object_id, user_id=new_user_id, permissions=sampledb.logic.object_permissions.Permissions.GRANT)

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/referencable')
    assert r.status_code == 200
    data = json.loads(r.content)
    assert len(data['referencable_objects']) == 4
    assert data['referencable_objects'] == [
        {'action_id': 2, 'id': 4, 'max_permission': 3, 'text': 'Other Object (#4)'},
        {'action_id': 1, 'id': 3, 'max_permission': 3, 'text': 'Example42 (#3)'},
        {'action_id': 1, 'id': 2, 'max_permission': 3, 'text': 'Example2 (#2)'},
        {'action_id': 1, 'id': 1, 'max_permission': 3, 'text': 'Example1 (#1)'}
    ]

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user_id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/referencable?required_perm=WRITE')
    assert r.status_code == 200
    data = json.loads(r.content)
    assert len(data['referencable_objects']) == 2
    assert data['referencable_objects'] == [
        {'action_id': 1, 'id': 3, 'max_permission': 3, 'text': 'Example42 (#3)'},
        {'action_id': 1, 'id': 2, 'max_permission': 2, 'text': 'Example2 (#2)'}
    ]


def test_get_object(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@fz-juelich.de', type=sampledb.models.UserType.PERSON)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@fz-juelich.de', type=sampledb.models.UserType.PERSON)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.post(flask_server.base_url + 'objects/{}/permissions/request'.format(object.object_id), allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'] == flask_server.base_url + 'objects/{}'.format(object.object_id)
    notifications = sampledb.logic.notifications.get_notifications(user.id, unread_only=True)
    for notification in notifications:
        assert notification.type != sampledb.logic.notifications.NotificationType.RECEIVED_OBJECT_PERMISSIONS_REQUEST



def test_get_object_edit_form(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@fz-juelich.de', type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=object.object_id, user_id=new_user_id, permissions=sampledb.logic.object_permissions.Permissions.READ)
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user_id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 403


def test_get_object_version(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@fz-juelich.de', type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user_id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/versions/0'.format(object.object_id))
    assert r.status_code == 403


def test_get_object_versions(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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



def test_edit_object_action_add(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data=object_data,
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    assert 'object__multilayer__2__films__0__elements__1' not in r.content.decode('utf-8')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'action_object__multilayer__2__films__0__elements__?__add': 'action_object__multilayer__2__films__0__elements__?__add', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__checkbox__hidden': 'checkbox exists', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__substrate__text': 'GaAs', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__created__datetime': '2017-02-24 11:56:00', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__name__text': 'OMBE-100', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1', 'object__dropdown__text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    assert 'object__multilayer__2__films__0__elements__1' in r.content.decode('utf-8')


def test_edit_object_previous_actions(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data=object_data,
        user_id=user.id,
        action_id=action.id
    )
    previous_actions = ['action_object__multilayer__2__films__0__elements__?__add']
    serializer = itsdangerous.URLSafeSerializer(flask_server.app.config['SECRET_KEY'])
    previous_actions = serializer.dumps(previous_actions)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    assert 'object__multilayer__2__films__0__elements__1' not in r.content.decode('utf-8')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'previous_actions': previous_actions, 'action_object__multilayer__2__films__0__elements__?__add': 'action_object__multilayer__2__films__0__elements__?__add', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__checkbox__hidden': 'checkbox exists', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__substrate__text': 'GaAs', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__created__datetime': '2017-02-24 11:56:00', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__name__text': 'OMBE-100', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1', 'object__dropdown__text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    assert 'object__multilayer__2__films__0__elements__1' in r.content.decode('utf-8')
    assert 'object__multilayer__2__films__0__elements__2' in r.content.decode('utf-8')


def test_edit_object_previous_actions_invalid_key(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data=object_data,
        user_id=user.id,
        action_id=action.id
    )
    previous_actions = ['action_object__multilayer__2__films__0__elements__?_add']
    serializer = itsdangerous.URLSafeSerializer('invalid key')
    previous_actions = serializer.dumps(previous_actions)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    assert 'object__multilayer__2__films__0__elements__1' not in r.content.decode('utf-8')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'previous_actions': previous_actions, 'action_object__multilayer__2__films__0__elements__?__add': 'action_object__multilayer__2__films__0__elements__?__add', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__checkbox__hidden': 'checkbox exists', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__substrate__text': 'GaAs', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__created__datetime': '2017-02-24 11:56:00', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__name__text': 'OMBE-100', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1', 'object__dropdown__text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 400


def test_edit_object_previous_actions_invalid_action(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data=object_data,
        user_id=user.id,
        action_id=action.id
    )
    previous_actions = ['invalid']
    serializer = itsdangerous.URLSafeSerializer(flask_server.app.config['SECRET_KEY'])
    previous_actions = serializer.dumps(previous_actions)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    assert 'object__multilayer__2__films__0__elements__1' not in r.content.decode('utf-8')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'previous_actions': previous_actions, 'action_object__multilayer__2__films__0__elements__?__add': 'action_object__multilayer__2__films__0__elements__?__add', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__checkbox__hidden': 'checkbox exists', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__substrate__text': 'GaAs', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__created__datetime': '2017-02-24 11:56:00', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__name__text': 'OMBE-100', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1', 'object__dropdown__text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 400


def test_edit_object_action_delete(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data=object_data,
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    assert 'object__multilayer__2__films__0__elements__0' in r.content.decode('utf-8')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    # Try violating minItems first
    form_data = {'csrf_token': csrf_token, 'action_object__multilayer__2__films__0__elements__0__delete': 'action_object__multilayer__2__films__0__elements__0__delete', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__checkbox__hidden': 'checkbox exists', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__substrate__text': 'GaAs', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__created__datetime': '2017-02-24 11:56:00', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__name__text': 'OMBE-100', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1', 'object__dropdown__text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    assert 'object__multilayer__2__films__0__elements__0' in r.content.decode('utf-8')
    # Delete something that may actually be deleted
    assert 'object__multilayer__3' in r.content.decode('utf-8')
    form_data = {'csrf_token': csrf_token, 'action_object__multilayer__3__delete': 'action_object__multilayer__3__delete', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__checkbox__hidden': 'checkbox exists', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__substrate__text': 'GaAs', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__created__datetime': '2017-02-24 11:56:00', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__name__text': 'OMBE-100', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1', 'object__dropdown__text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    assert 'object__multilayer__3' not in r.content.decode('utf-8')


def test_new_object(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '2','action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 2
    objects = sampledb.logic.objects.get_objects()
    assert objects[1].data['name']['text'] == "OMBE-100-001"
    assert objects[0].data['name']['text'] == "OMBE-100-002"


def test_new_object_batch_invalid_number(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': 'invalid','action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0


def test_new_object_batch_float_number(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '2.0','action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 2


def test_new_object_batch_invalid_float_number(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement_batch.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0
    with flask_server.app.app_context():
        assert sampledb.logic.user_log.get_user_log_entries(user.id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'input_num_batch_objects': '2.5','action_submit': 'action_submit', 'object__name__text': 'OMBE-100', 'object__substrate__text': 'GaAs', 'object__checkbox__hidden': 'checkbox exists', 'object__created__datetime': '2017-02-24 11:56:00', 'object__dropdown__text': 'Option A', 'object__multilayer__2__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__1__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__0__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__substrate_temperature__magnitude': '130', 'object__multilayer__1__films__0__elements__0__rate__magnitude': '1', 'object__multilayer__0__films__0__thickness__magnitude': '5', 'object__multilayer__1__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__elements__0__name__text': 'Ag', 'object__multilayer__2__films__1__elements__0__rate__magnitude': '0.05', 'object__multilayer__0__films__0__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__thickness__magnitude': '1500', 'object__multilayer__0__films__0__thickness__units': 'Å', 'object__multilayer__0__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__name__text': 'Pd', 'object__multilayer__3__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__3__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__2__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__elements__0__rate__magnitude': '0.01', 'object__multilayer__2__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__1__name__text': 'Fe', 'object__multilayer__2__films__1__oxygen_flow__units': 'cm**3/s', 'object__multilayer__2__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__1__films__0__name__text': 'Buffer Layer', 'object__multilayer__2__repetitions__magnitude': '10', 'object__multilayer__2__films__1__elements__0__name__text': 'Fe', 'object__multilayer__2__films__1__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__substrate_temperature__units': 'degC', 'object__multilayer__0__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__3__films__0__thickness__magnitude': '150', 'object__multilayer__2__films__0__elements__0__frequency_change__magnitude': '', 'object__multilayer__1__repetitions__magnitude': '1', 'object__multilayer__2__films__1__substrate_temperature__units': 'degC', 'object__multilayer__2__films__1__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__0__thickness__magnitude': '150', 'object__multilayer__0__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__2__films__0__name__text': 'Pd', 'object__multilayer__1__films__0__elements__0__frequency_change__units': 'Hz / s', 'object__multilayer__2__films__1__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__1__thickness__magnitude': '10', 'object__multilayer__3__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__0__repetitions__magnitude': '2', 'object__multilayer__1__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__0__oxygen_flow__units': 'cm**3/s', 'object__multilayer__3__films__0__elements__0__rate__magnitude': '0.1', 'object__multilayer__1__films__0__substrate_temperature__magnitude': '130', 'object__multilayer__0__films__0__elements__0__fraction__magnitude': '', 'object__multilayer__2__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__2__films__1__thickness__units': 'Å', 'object__multilayer__0__films__0__name__text': 'Seed Layer', 'object__multilayer__1__films__0__thickness__units': 'Å', 'object__multilayer__3__films__0__oxygen_flow__magnitude': '0', 'object__multilayer__3__films__0__name__text': 'Pd Layer', 'object__multilayer__2__films__0__thickness__units': 'Å', 'object__multilayer__1__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__0__films__0__elements__0__rate__units': 'Å/s', 'object__multilayer__3__films__0__substrate_temperature__magnitude': '100', 'object__multilayer__3__repetitions__magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 0


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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', {
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
    assert not sampledb.logic.object_permissions.object_is_public(object.object_id)

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    user_csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'user_permissions-0-csrf_token'})['value']

    form_data = {
        'edit_user_permissions': 'edit_user_permissions',
        'csrf_token': csrf_token,
        'public_permissions': 'read',
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
    assert sampledb.logic.object_permissions.object_is_public(object.object_id)
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
        'edit_user_permissions': 'edit_user_permissions',
        'csrf_token': csrf_token,
        'public_permissions': 'none',
        'user_permissions-0-csrf_token': user_csrf_token,
        'user_permissions-0-user_id': '42',
        'user_permissions-0-permissions': 'read',
    }
    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    current_permissions = sampledb.logic.object_permissions.get_object_permissions_for_users(object.object_id)
    assert current_permissions == {
        user.id: sampledb.logic.object_permissions.Permissions.GRANT
    }
    assert not sampledb.logic.object_permissions.object_is_public(object.object_id)

    form_data = {
        'edit_user_permissions': 'edit_user_permissions',
        'csrf_token': csrf_token,
        'public_permissions': 'none',
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
    assert not sampledb.logic.object_permissions.object_is_public(object.object_id)

    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 403


def test_object_permissions_add_user(flask_server, user):
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', {
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
    assert not sampledb.logic.object_permissions.object_is_public(object.object_id)

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').findAll('input', {'name': 'csrf_token'})[1]['value']

    with flask_server.app.app_context():
        user2 = sampledb.models.User(name="New User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
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
    assert not sampledb.logic.object_permissions.object_is_public(object.object_id)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', {
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
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
        if input_field['name'].startswith('object'):
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
            "text": "Test"
        },
        "name_2": {
            "_type": "text",
            "text": "Test-2"
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
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
        if input_field['name'].startswith('object'):
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
            "text": "Test"
        },
        "name_2": {
            "_type": "text",
            "text": "Test-2"
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    name = 'Example1'
    object = sampledb.logic.objects.create_object(
            data={'name': {'_type': 'text', 'text': name}, 'name2': {'_type': 'text', 'text': name}},
            user_id=user.id,
            action_id=action.id
        )
    schema["properties"]["name2"]["type"] = "bool"
    sampledb.logic.actions.update_action(action.id, 'New Example Action', '', schema)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'previous_object_id': object.id})
    assert r.status_code == 200
    assert len(sampledb.logic.objects.get_objects()) == 1
    with flask_server.app.app_context():
        assert len(sampledb.logic.user_log.get_user_log_entries(user.id)) == 1
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    object_name = document.find('input', {'name': 'object__name2__text'})['value']
    assert object_name == name
    form_data = {'csrf_token': csrf_token, 'action_submit': 'action_submit', 'object__name__text': name, 'object__name2__text': name}
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
                    "title": "Entry",
                    "maxItems": 5,
                    "minItems": 1,
                    "items": {
                        "type": "text",
                        "title": "",
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={"name": {"text": "Test", "_type": "text"}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}'.format(object.id), params={'mode': 'edit'})
    assert r.status_code == 200


def test_edit_nested_array(flask_server, user):
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
                    "title": "Entry",
                    "maxItems": 5,
                    "minItems": 1,
                    "items": {
                        "type": "text",
                        "title": "",
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
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.logic.objects.create_object(
        data={"name": {"text": "Test", "_type": "text"}},
        user_id=user.id,
        action_id=action.id
    )

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}'.format(object.id), params={'mode': 'edit'})
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    previous_actions = document.find('input', {'name': 'previous_actions'})['value']
    form_data = {'csrf_token': csrf_token, 'previous_actions': previous_actions, 'object__name__text': 'Test', 'action_object__nested_array__?__add': 'action_object__nested_array__?__add'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.id), params={'mode': 'edit'}, data=form_data)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    previous_actions = document.find('input', {'name': 'previous_actions'})['value']
    form_data = {'csrf_token': csrf_token, 'previous_actions': previous_actions, 'object__name__text': 'Test', 'action_object__nested_array__?__add': 'action_object__nested_array__?__add'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.id), params={'mode': 'edit'}, data=form_data)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    csrf_token = document.find('input', {'name': 'csrf_token'})['value']
    previous_actions = document.find('input', {'name': 'previous_actions'})['value']
    form_data = {'csrf_token': csrf_token, 'previous_actions': previous_actions, 'object__name__text': 'Test', 'action_submit': 'action_submit'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.id), params={'mode': 'edit'}, data=form_data, allow_redirects=False)
    assert r.status_code == 302


def test_new_object_with_instrument_log_entry(flask_server, user):
    with flask_server.app.app_context():
        instrument = sampledb.logic.instruments.create_instrument('Test Instrument', '')
        sampledb.logic.instruments.add_instrument_responsible_user(instrument.id, user.id)
        category = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument.id,
            'Error',
            sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
        )
        assert instrument.id is not None
        assert category.id is not None
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json'), encoding="utf-8"))
    action = sampledb.logic.actions.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema, instrument.id)
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



