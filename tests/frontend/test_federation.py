# coding: utf-8
"""

"""

import requests
import pytest
from uuid import uuid4
from bs4 import BeautifulSoup

from sampledb.logic.components import add_component, get_components
from sampledb.logic.component_authentication import add_own_token_authentication
from sampledb import models, db


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = models.User(name="Basic User", email="example@example.com", type=models.UserType.PERSON)
        db.session.add(user)
        db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


@pytest.fixture
def admin(flask_server):
    with flask_server.app.app_context():
        user = models.User(name="Administrator", email="admin@example.com", type=models.UserType.PERSON)
        user.is_admin = True
        db.session.add(user)
        db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


@pytest.fixture
def components():
    components = [
        add_component(
            uuid=str(uuid4()),
            name='Component 1',
            address='https://example.com',
            description='Component description'
        ), add_component(
            uuid=str(uuid4()),
            name=None,
            address='https://example.com',
            description='Component description'
        ), add_component(
            uuid=str(uuid4()),
            name='Component 3',
            address=None,
            description='Component description'
        ), add_component(
            uuid=str(uuid4()),
            name=None,
            address=None,
            description='Component description'
        )
    ]

    return get_components()     # for consistent order


@pytest.fixture
def component():
    component = add_component(
        uuid=str(uuid4()),
        name='Component',
        address='https://example.com',
        description='Component description'
    )

    return component


def test_get_components(flask_server, user, components):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'other-databases')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    components_list = document.find('ul', id='components_list')
    assert components_list is not None
    lis = components_list.find_all('li')
    assert len(lis) == 4
    for i, component in enumerate(components):
        links = lis[i].find_all('a')
        assert links[0]['href'] == '/other-databases/' + str(component.id)
        if component.address is None:
            assert len(links) == 1
        else:
            assert len(links) == 2
            assert links[1]['href'] == component.address
            assert links[1].getText() == component.address
        assert links[0].getText() == component.get_name()


def test_add_database_button_admin(flask_server, admin):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(admin.id)).status_code == 200
    r = session.get(flask_server.base_url + 'other-databases')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find(id='addComponentModal') is not None
    assert document.find('button', string='Add Database') is not None


def test_add_database_button_user(flask_server, user):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'other-databases')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('div', id='addComponentModal') is None
    assert document.find('button', string='Add Database') is None


def test_get_component_user(flask_server, user, component):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'other-databases/' + str(component.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('div', id='editComponentModal') is None
    assert document.find('button', string='Edit Database') is None
    assert document.find('button', form='syncComponentForm') is None
    assert document.find('div', id='apiTokenDiv') is None
    assert document.find('div', id='createApiTokenModal') is None
    assert document.find('div', id='createOwnApiTokenModal') is None
    assert document.find('form', id='syncComponentForm') is None


def test_get_component_admin(flask_server, admin, component):
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(admin.id)).status_code == 200
    r = session.get(flask_server.base_url + 'other-databases/' + str(component.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('div', id='editComponentModal') is not None
    assert document.find('button', string='Edit Database') is not None
    assert document.find('div', id='apiTokenDiv') is not None
    assert document.find('div', id='createApiTokenModal') is not None
    assert document.find('div', id='createOwnApiTokenModal') is not None
    assert document.find('form', id='syncComponentForm') is None
    add_own_token_authentication(
        component_id=component.id,
        token='.' * 64,
        description=''
    )
    r = session.get(flask_server.base_url + 'other-databases/' + str(component.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('form', id='syncComponentForm') is not None
