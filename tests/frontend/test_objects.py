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
from sampledb.rest_api.objects import SCHEMA_DIR


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


def test_get_objects(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    names = ['Example1', 'Example2', 'Example42']
    objects = [
        sampledb.models.Objects.create_object(
            data={'name': {'_type': 'text', 'text': name}},
            schema=action.schema,
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


def test_search_objects(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    names = ['Example1', 'Example2', 'Example12']
    objects = [
        sampledb.models.Objects.create_object(
            data={'name': {'_type': 'text', 'text': name}},
            schema=action.schema,
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


def test_get_object(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        schema=action.schema,
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
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        schema=action.schema,
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


def test_get_object_edit_form(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        schema=action.schema,
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
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    with flask_server.app.app_context():
        new_user = sampledb.models.User(name='New User', email='example@fz-juelich.de', type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(new_user)
        sampledb.db.session.commit()
        new_user_id = new_user.id
    sampledb.logic.permissions.set_user_object_permissions(object_id=object.object_id, user_id=new_user_id, permissions=sampledb.logic.permissions.Permissions.READ)
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user_id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 403


def test_get_object_version(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        schema=action.schema,
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
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        schema=action.schema,
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
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data={'name': {'_type': 'text', 'text': 'Example'}},
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/versions/'.format(object.object_id))
    assert r.status_code == 200
    assert 'objects/{}/versions/0'.format(object.object_id) in r.content.decode('utf-8')


def test_edit_object(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json')))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data=object_data,
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'action_submit': 'action_submit', 'object_sample_oid': object.object_id, 'object_multilayer_2_films_0_elements_0_name_text': 'Pd', 'object_multilayer_3_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_1_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_0_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_checkbox_hidden': 'checkbox exists', 'object_multilayer_2_films_1_substrate_temperature_magnitude': '130', 'object_multilayer_1_films_0_elements_0_rate_magnitude': '1', 'object_multilayer_0_films_0_thickness_magnitude': '5', 'object_multilayer_1_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_elements_0_name_text': 'Ag', 'object_multilayer_2_films_1_elements_0_rate_magnitude': '0.05', 'object_multilayer_0_films_0_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_thickness_magnitude': '1500', 'object_multilayer_0_films_0_thickness_units': 'Å', 'object_multilayer_0_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_name_text': 'Pd', 'object_substrate_text': 'GaAs', 'object_multilayer_3_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_3_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_2_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_elements_0_rate_magnitude': '0.01', 'object_multilayer_2_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_1_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_units': 'cm**3/s', 'object_created_datetime': '2017-02-24 11:56:00', 'object_multilayer_2_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_1_films_0_name_text': 'Buffer Layer', 'object_multilayer_2_repetitions_magnitude': '10', 'object_multilayer_2_films_1_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_3_films_0_thickness_magnitude': '150', 'object_multilayer_2_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_repetitions_magnitude': '1', 'object_name_text': 'OMBE-100', 'object_multilayer_2_films_1_substrate_temperature_units': 'degC', 'object_multilayer_2_films_1_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_thickness_magnitude': '150', 'object_multilayer_0_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_2_films_0_name_text': 'Pd', 'object_multilayer_1_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_1_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_1_thickness_magnitude': '10', 'object_multilayer_3_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_0_repetitions_magnitude': '2', 'object_multilayer_1_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_3_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_1_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_0_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_thickness_units': 'Å', 'object_multilayer_0_films_0_name_text': 'Seed Layer', 'object_multilayer_1_films_0_thickness_units': 'Å', 'object_multilayer_3_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_name_text': 'Pd Layer', 'object_multilayer_2_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_0_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_3_repetitions_magnitude': '1', 'object_dropdown_text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    object = sampledb.models.Objects.get_object_version(object_id=object.object_id, version_id=1)
    assert object is not None
    assert object.data['name']['text'] == 'OMBE-100'
    assert object.data['sample']['object_id'] == object.object_id


def test_edit_object_action_add(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json')))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data=object_data,
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    assert 'object_multilayer_2_films_0_elements_1' not in r.content.decode('utf-8')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'action_object_multilayer_2_films_0_elements_?_add': 'action_object_multilayer_2_films_0_elements_?_add', 'object_multilayer_2_films_0_elements_0_name_text': 'Pd', 'object_multilayer_3_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_1_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_0_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_checkbox_hidden': 'checkbox exists', 'object_multilayer_2_films_1_substrate_temperature_magnitude': '130', 'object_multilayer_1_films_0_elements_0_rate_magnitude': '1', 'object_multilayer_0_films_0_thickness_magnitude': '5', 'object_multilayer_1_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_elements_0_name_text': 'Ag', 'object_multilayer_2_films_1_elements_0_rate_magnitude': '0.05', 'object_multilayer_0_films_0_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_thickness_magnitude': '1500', 'object_multilayer_0_films_0_thickness_units': 'Å', 'object_multilayer_0_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_name_text': 'Pd', 'object_substrate_text': 'GaAs', 'object_multilayer_3_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_3_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_2_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_elements_0_rate_magnitude': '0.01', 'object_multilayer_2_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_1_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_units': 'cm**3/s', 'object_created_datetime': '2017-02-24 11:56:00', 'object_multilayer_2_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_1_films_0_name_text': 'Buffer Layer', 'object_multilayer_2_repetitions_magnitude': '10', 'object_multilayer_2_films_1_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_3_films_0_thickness_magnitude': '150', 'object_multilayer_2_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_repetitions_magnitude': '1', 'object_name_text': 'OMBE-100', 'object_multilayer_2_films_1_substrate_temperature_units': 'degC', 'object_multilayer_2_films_1_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_thickness_magnitude': '150', 'object_multilayer_0_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_2_films_0_name_text': 'Pd', 'object_multilayer_1_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_1_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_1_thickness_magnitude': '10', 'object_multilayer_3_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_0_repetitions_magnitude': '2', 'object_multilayer_1_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_3_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_1_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_0_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_thickness_units': 'Å', 'object_multilayer_0_films_0_name_text': 'Seed Layer', 'object_multilayer_1_films_0_thickness_units': 'Å', 'object_multilayer_3_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_name_text': 'Pd Layer', 'object_multilayer_2_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_0_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_3_repetitions_magnitude': '1', 'object_dropdown_text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    assert 'object_multilayer_2_films_0_elements_1' in r.content.decode('utf-8')


def test_edit_object_previous_actions(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json')))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data=object_data,
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    previous_actions = ['action_object_multilayer_2_films_0_elements_?_add']
    serializer = itsdangerous.URLSafeSerializer(flask_server.app.config['SECRET_KEY'])
    previous_actions = serializer.dumps(previous_actions)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    assert 'object_multilayer_2_films_0_elements_1' not in r.content.decode('utf-8')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'previous_actions': previous_actions, 'action_object_multilayer_2_films_0_elements_?_add': 'action_object_multilayer_2_films_0_elements_?_add', 'object_multilayer_2_films_0_elements_0_name_text': 'Pd', 'object_multilayer_3_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_1_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_0_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_checkbox_hidden': 'checkbox exists', 'object_multilayer_2_films_1_substrate_temperature_magnitude': '130', 'object_multilayer_1_films_0_elements_0_rate_magnitude': '1', 'object_multilayer_0_films_0_thickness_magnitude': '5', 'object_multilayer_1_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_elements_0_name_text': 'Ag', 'object_multilayer_2_films_1_elements_0_rate_magnitude': '0.05', 'object_multilayer_0_films_0_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_thickness_magnitude': '1500', 'object_multilayer_0_films_0_thickness_units': 'Å', 'object_multilayer_0_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_name_text': 'Pd', 'object_substrate_text': 'GaAs', 'object_multilayer_3_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_3_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_2_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_elements_0_rate_magnitude': '0.01', 'object_multilayer_2_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_1_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_units': 'cm**3/s', 'object_created_datetime': '2017-02-24 11:56:00', 'object_multilayer_2_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_1_films_0_name_text': 'Buffer Layer', 'object_multilayer_2_repetitions_magnitude': '10', 'object_multilayer_2_films_1_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_3_films_0_thickness_magnitude': '150', 'object_multilayer_2_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_repetitions_magnitude': '1', 'object_name_text': 'OMBE-100', 'object_multilayer_2_films_1_substrate_temperature_units': 'degC', 'object_multilayer_2_films_1_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_thickness_magnitude': '150', 'object_multilayer_0_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_2_films_0_name_text': 'Pd', 'object_multilayer_1_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_1_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_1_thickness_magnitude': '10', 'object_multilayer_3_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_0_repetitions_magnitude': '2', 'object_multilayer_1_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_3_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_1_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_0_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_thickness_units': 'Å', 'object_multilayer_0_films_0_name_text': 'Seed Layer', 'object_multilayer_1_films_0_thickness_units': 'Å', 'object_multilayer_3_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_name_text': 'Pd Layer', 'object_multilayer_2_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_0_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_3_repetitions_magnitude': '1', 'object_dropdown_text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    assert 'object_multilayer_2_films_0_elements_1' in r.content.decode('utf-8')
    assert 'object_multilayer_2_films_0_elements_2' in r.content.decode('utf-8')


def test_edit_object_previous_actions_invalid_key(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json')))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data=object_data,
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    previous_actions = ['action_object_multilayer_2_films_0_elements_?_add']
    serializer = itsdangerous.URLSafeSerializer('invalid key')
    previous_actions = serializer.dumps(previous_actions)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    assert 'object_multilayer_2_films_0_elements_1' not in r.content.decode('utf-8')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'previous_actions': previous_actions, 'action_object_multilayer_2_films_0_elements_?_add': 'action_object_multilayer_2_films_0_elements_?_add', 'object_multilayer_2_films_0_elements_0_name_text': 'Pd', 'object_multilayer_3_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_1_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_0_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_checkbox_hidden': 'checkbox exists', 'object_multilayer_2_films_1_substrate_temperature_magnitude': '130', 'object_multilayer_1_films_0_elements_0_rate_magnitude': '1', 'object_multilayer_0_films_0_thickness_magnitude': '5', 'object_multilayer_1_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_elements_0_name_text': 'Ag', 'object_multilayer_2_films_1_elements_0_rate_magnitude': '0.05', 'object_multilayer_0_films_0_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_thickness_magnitude': '1500', 'object_multilayer_0_films_0_thickness_units': 'Å', 'object_multilayer_0_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_name_text': 'Pd', 'object_substrate_text': 'GaAs', 'object_multilayer_3_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_3_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_2_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_elements_0_rate_magnitude': '0.01', 'object_multilayer_2_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_1_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_units': 'cm**3/s', 'object_created_datetime': '2017-02-24 11:56:00', 'object_multilayer_2_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_1_films_0_name_text': 'Buffer Layer', 'object_multilayer_2_repetitions_magnitude': '10', 'object_multilayer_2_films_1_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_3_films_0_thickness_magnitude': '150', 'object_multilayer_2_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_repetitions_magnitude': '1', 'object_name_text': 'OMBE-100', 'object_multilayer_2_films_1_substrate_temperature_units': 'degC', 'object_multilayer_2_films_1_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_thickness_magnitude': '150', 'object_multilayer_0_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_2_films_0_name_text': 'Pd', 'object_multilayer_1_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_1_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_1_thickness_magnitude': '10', 'object_multilayer_3_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_0_repetitions_magnitude': '2', 'object_multilayer_1_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_3_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_1_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_0_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_thickness_units': 'Å', 'object_multilayer_0_films_0_name_text': 'Seed Layer', 'object_multilayer_1_films_0_thickness_units': 'Å', 'object_multilayer_3_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_name_text': 'Pd Layer', 'object_multilayer_2_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_0_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_3_repetitions_magnitude': '1', 'object_dropdown_text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 400


def test_edit_object_previous_actions_invalid_action(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json')))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data=object_data,
        schema=action.schema,
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
    assert 'object_multilayer_2_films_0_elements_1' not in r.content.decode('utf-8')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'previous_actions': previous_actions, 'action_object_multilayer_2_films_0_elements_?_add': 'action_object_multilayer_2_films_0_elements_?_add', 'object_multilayer_2_films_0_elements_0_name_text': 'Pd', 'object_multilayer_3_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_1_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_0_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_checkbox_hidden': 'checkbox exists', 'object_multilayer_2_films_1_substrate_temperature_magnitude': '130', 'object_multilayer_1_films_0_elements_0_rate_magnitude': '1', 'object_multilayer_0_films_0_thickness_magnitude': '5', 'object_multilayer_1_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_elements_0_name_text': 'Ag', 'object_multilayer_2_films_1_elements_0_rate_magnitude': '0.05', 'object_multilayer_0_films_0_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_thickness_magnitude': '1500', 'object_multilayer_0_films_0_thickness_units': 'Å', 'object_multilayer_0_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_name_text': 'Pd', 'object_substrate_text': 'GaAs', 'object_multilayer_3_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_3_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_2_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_elements_0_rate_magnitude': '0.01', 'object_multilayer_2_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_1_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_units': 'cm**3/s', 'object_created_datetime': '2017-02-24 11:56:00', 'object_multilayer_2_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_1_films_0_name_text': 'Buffer Layer', 'object_multilayer_2_repetitions_magnitude': '10', 'object_multilayer_2_films_1_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_3_films_0_thickness_magnitude': '150', 'object_multilayer_2_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_repetitions_magnitude': '1', 'object_name_text': 'OMBE-100', 'object_multilayer_2_films_1_substrate_temperature_units': 'degC', 'object_multilayer_2_films_1_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_thickness_magnitude': '150', 'object_multilayer_0_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_2_films_0_name_text': 'Pd', 'object_multilayer_1_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_1_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_1_thickness_magnitude': '10', 'object_multilayer_3_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_0_repetitions_magnitude': '2', 'object_multilayer_1_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_3_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_1_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_0_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_thickness_units': 'Å', 'object_multilayer_0_films_0_name_text': 'Seed Layer', 'object_multilayer_1_films_0_thickness_units': 'Å', 'object_multilayer_3_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_name_text': 'Pd Layer', 'object_multilayer_2_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_0_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_3_repetitions_magnitude': '1', 'object_dropdown_text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 400


def test_edit_object_action_delete(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json')))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    object = sampledb.models.Objects.create_object(
        data=object_data,
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}?mode=edit'.format(object.object_id))
    assert r.status_code == 200
    assert 'object_multilayer_2_films_0_elements_0' in r.content.decode('utf-8')
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    # Try violating minItems first
    form_data = {'csrf_token': csrf_token, 'action_object_multilayer_2_films_0_elements_0_delete': 'action_object_multilayer_2_films_0_elements_0_delete', 'object_multilayer_2_films_0_elements_0_name_text': 'Pd', 'object_multilayer_3_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_1_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_0_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_checkbox_hidden': 'checkbox exists', 'object_multilayer_2_films_1_substrate_temperature_magnitude': '130', 'object_multilayer_1_films_0_elements_0_rate_magnitude': '1', 'object_multilayer_0_films_0_thickness_magnitude': '5', 'object_multilayer_1_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_elements_0_name_text': 'Ag', 'object_multilayer_2_films_1_elements_0_rate_magnitude': '0.05', 'object_multilayer_0_films_0_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_thickness_magnitude': '1500', 'object_multilayer_0_films_0_thickness_units': 'Å', 'object_multilayer_0_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_name_text': 'Pd', 'object_substrate_text': 'GaAs', 'object_multilayer_3_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_3_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_2_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_elements_0_rate_magnitude': '0.01', 'object_multilayer_2_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_1_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_units': 'cm**3/s', 'object_created_datetime': '2017-02-24 11:56:00', 'object_multilayer_2_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_1_films_0_name_text': 'Buffer Layer', 'object_multilayer_2_repetitions_magnitude': '10', 'object_multilayer_2_films_1_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_3_films_0_thickness_magnitude': '150', 'object_multilayer_2_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_repetitions_magnitude': '1', 'object_name_text': 'OMBE-100', 'object_multilayer_2_films_1_substrate_temperature_units': 'degC', 'object_multilayer_2_films_1_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_thickness_magnitude': '150', 'object_multilayer_0_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_2_films_0_name_text': 'Pd', 'object_multilayer_1_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_1_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_1_thickness_magnitude': '10', 'object_multilayer_3_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_0_repetitions_magnitude': '2', 'object_multilayer_1_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_3_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_1_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_0_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_thickness_units': 'Å', 'object_multilayer_0_films_0_name_text': 'Seed Layer', 'object_multilayer_1_films_0_thickness_units': 'Å', 'object_multilayer_3_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_name_text': 'Pd Layer', 'object_multilayer_2_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_0_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_3_repetitions_magnitude': '1', 'object_dropdown_text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    assert 'object_multilayer_2_films_0_elements_0' in r.content.decode('utf-8')
    # Delete something that may actually be deleted
    assert 'object_multilayer_3' in r.content.decode('utf-8')
    form_data = {'csrf_token': csrf_token, 'action_object_multilayer_3_delete': 'action_object_multilayer_3_delete', 'object_multilayer_2_films_0_elements_0_name_text': 'Pd', 'object_multilayer_3_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_1_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_0_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_checkbox_hidden': 'checkbox exists', 'object_multilayer_2_films_1_substrate_temperature_magnitude': '130', 'object_multilayer_1_films_0_elements_0_rate_magnitude': '1', 'object_multilayer_0_films_0_thickness_magnitude': '5', 'object_multilayer_1_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_elements_0_name_text': 'Ag', 'object_multilayer_2_films_1_elements_0_rate_magnitude': '0.05', 'object_multilayer_0_films_0_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_thickness_magnitude': '1500', 'object_multilayer_0_films_0_thickness_units': 'Å', 'object_multilayer_0_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_name_text': 'Pd', 'object_substrate_text': 'GaAs', 'object_multilayer_3_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_3_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_2_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_elements_0_rate_magnitude': '0.01', 'object_multilayer_2_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_1_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_units': 'cm**3/s', 'object_created_datetime': '2017-02-24 11:56:00', 'object_multilayer_2_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_1_films_0_name_text': 'Buffer Layer', 'object_multilayer_2_repetitions_magnitude': '10', 'object_multilayer_2_films_1_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_3_films_0_thickness_magnitude': '150', 'object_multilayer_2_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_repetitions_magnitude': '1', 'object_name_text': 'OMBE-100', 'object_multilayer_2_films_1_substrate_temperature_units': 'degC', 'object_multilayer_2_films_1_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_thickness_magnitude': '150', 'object_multilayer_0_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_2_films_0_name_text': 'Pd', 'object_multilayer_1_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_1_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_1_thickness_magnitude': '10', 'object_multilayer_3_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_0_repetitions_magnitude': '2', 'object_multilayer_1_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_3_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_1_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_0_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_thickness_units': 'Å', 'object_multilayer_0_films_0_name_text': 'Seed Layer', 'object_multilayer_1_films_0_thickness_units': 'Å', 'object_multilayer_3_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_name_text': 'Pd Layer', 'object_multilayer_2_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_0_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_3_repetitions_magnitude': '1', 'object_dropdown_text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    assert 'object_multilayer_3' not in r.content.decode('utf-8')


def test_new_object(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe_measurement.sampledb.json')))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe-1.sampledb.json')))
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/new', params={'action_id': action.id})
    assert r.status_code == 200
    assert len(sampledb.models.Objects.get_current_objects()) == 0
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    form_data = {'csrf_token': csrf_token, 'action_submit': 'action_submit', 'object_multilayer_2_films_0_elements_0_name_text': 'Pd', 'object_multilayer_3_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_1_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_0_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_checkbox_hidden': 'checkbox exists', 'object_multilayer_2_films_1_substrate_temperature_magnitude': '130', 'object_multilayer_1_films_0_elements_0_rate_magnitude': '1', 'object_multilayer_0_films_0_thickness_magnitude': '5', 'object_multilayer_1_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_elements_0_name_text': 'Ag', 'object_multilayer_2_films_1_elements_0_rate_magnitude': '0.05', 'object_multilayer_0_films_0_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_thickness_magnitude': '1500', 'object_multilayer_0_films_0_thickness_units': 'Å', 'object_multilayer_0_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_name_text': 'Pd', 'object_substrate_text': 'GaAs', 'object_multilayer_3_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_3_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_2_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_elements_0_rate_magnitude': '0.01', 'object_multilayer_2_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_1_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_units': 'cm**3/s', 'object_created_datetime': '2017-02-24 11:56:00', 'object_multilayer_2_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_1_films_0_name_text': 'Buffer Layer', 'object_multilayer_2_repetitions_magnitude': '10', 'object_multilayer_2_films_1_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_3_films_0_thickness_magnitude': '150', 'object_multilayer_2_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_repetitions_magnitude': '1', 'object_name_text': 'OMBE-100', 'object_multilayer_2_films_1_substrate_temperature_units': 'degC', 'object_multilayer_2_films_1_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_thickness_magnitude': '150', 'object_multilayer_0_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_2_films_0_name_text': 'Pd', 'object_multilayer_1_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_1_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_1_thickness_magnitude': '10', 'object_multilayer_3_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_0_repetitions_magnitude': '2', 'object_multilayer_1_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_3_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_1_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_0_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_thickness_units': 'Å', 'object_multilayer_0_films_0_name_text': 'Seed Layer', 'object_multilayer_1_films_0_thickness_units': 'Å', 'object_multilayer_3_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_name_text': 'Pd Layer', 'object_multilayer_2_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_0_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_3_repetitions_magnitude': '1', 'object_dropdown_text': 'Option A'}
    r = session.post(flask_server.base_url + 'objects/new', params={'action_id': action.id}, data=form_data)
    assert r.status_code == 200
    assert len(sampledb.models.Objects.get_current_objects()) == 1
    object = sampledb.models.Objects.get_current_objects()[0]
    assert len(object.data['multilayer']) == 4


def test_restore_object_version(flask_server, user):
    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        }
    }
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    data = {'name': {'_type': 'text', 'text': 'object_version_0'}}
    object = sampledb.models.Objects.create_object(
        data=data,
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    assert sampledb.models.Objects.get_current_object(object_id=object.object_id).data['name']['text'] == 'object_version_0'
    data['name']['text'] = 'object_version_1'
    sampledb.models.Objects.update_object(object.object_id, data=data, schema=schema, user_id=user.id)
    assert sampledb.models.Objects.get_current_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 0))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    r = session.post(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 0), data={'csrf_token': csrf_token})
    assert r.status_code == 200

    assert sampledb.models.Objects.get_current_object(object_id=object.object_id).data['name']['text'] == 'object_version_0'


def test_restore_object_version_invalid_data(flask_server, user):
    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        }
    }
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', schema)
    data = {'name': {'_type': 'text', 'text': 'object_version_0'}}
    object = sampledb.models.Objects.create_object(
        data=data,
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    assert sampledb.models.Objects.get_current_object(object_id=object.object_id).data['name']['text'] == 'object_version_0'
    data['name']['text'] = 'object_version_1'
    sampledb.models.Objects.update_object(object.object_id, data=data, schema=schema, user_id=user.id)
    assert sampledb.models.Objects.get_current_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(42, 0))
    assert r.status_code == 404
    assert sampledb.models.Objects.get_current_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    r = session.get(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 2))
    assert r.status_code == 404
    assert sampledb.models.Objects.get_current_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    r = session.get(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 0))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']

    r = session.post(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(42, 0), data={'csrf_token': csrf_token})
    assert r.status_code == 404
    assert sampledb.models.Objects.get_current_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    r = session.post(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 2), data={'csrf_token': csrf_token})
    assert r.status_code == 404
    assert sampledb.models.Objects.get_current_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'

    r = session.post(flask_server.base_url + 'objects/{}/versions/{}/restore'.format(object.object_id, 1), data={'csrf_token': csrf_token})
    assert r.status_code == 404
    assert sampledb.models.Objects.get_current_object(object_id=object.object_id).data['name']['text'] == 'object_version_1'


def test_update_object_permissions(flask_server, user):
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        }
    })
    data = {'name': {'_type': 'text', 'text': 'object_version_0'}}
    object = sampledb.models.Objects.create_object(
        data=data,
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    current_permissions = sampledb.logic.permissions.get_object_permissions(object.object_id)
    assert current_permissions == {
        None: sampledb.logic.permissions.Permissions.NONE,
        user.id: sampledb.logic.permissions.Permissions.GRANT
    }
    assert not sampledb.logic.permissions.object_is_public(object.object_id)

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
    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    current_permissions = sampledb.logic.permissions.get_object_permissions(object.object_id)
    assert current_permissions == {
        None: sampledb.logic.permissions.Permissions.READ,
        user.id: sampledb.logic.permissions.Permissions.GRANT
    }
    assert sampledb.logic.permissions.object_is_public(object.object_id)

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
    current_permissions = sampledb.logic.permissions.get_object_permissions(object.object_id)
    assert current_permissions == {
        None: sampledb.logic.permissions.Permissions.NONE,
        user.id: sampledb.logic.permissions.Permissions.GRANT
    }
    assert not sampledb.logic.permissions.object_is_public(object.object_id)

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
    current_permissions = sampledb.logic.permissions.get_object_permissions(object.object_id)
    assert current_permissions == {
        None: sampledb.logic.permissions.Permissions.NONE,
        user.id: sampledb.logic.permissions.Permissions.READ
    }
    assert not sampledb.logic.permissions.object_is_public(object.object_id)

    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 403


def test_object_permissions_add_user(flask_server, user):
    action = sampledb.logic.instruments.create_action(sampledb.models.ActionType.SAMPLE_CREATION, 'Example Action', '', {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        }
    })
    data = {'name': {'_type': 'text', 'text': 'object_version_0'}}
    object = sampledb.models.Objects.create_object(
        data=data,
        schema=action.schema,
        user_id=user.id,
        action_id=action.id
    )
    current_permissions = sampledb.logic.permissions.get_object_permissions(object.object_id)
    assert current_permissions == {
        None: sampledb.logic.permissions.Permissions.NONE,
        user.id: sampledb.logic.permissions.Permissions.GRANT
    }
    assert not sampledb.logic.permissions.object_is_public(object.object_id)

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

    form_data = {
        'add_user_permissions': 'add_user_permissions',
        'csrf_token': csrf_token,
        'user_id': str(user2.id),
        'permissions': 'write',
    }
    r = session.post(flask_server.base_url + 'objects/{}/permissions'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    current_permissions = sampledb.logic.permissions.get_object_permissions(object.object_id)
    assert current_permissions == {
        None: sampledb.logic.permissions.Permissions.NONE,
        user.id: sampledb.logic.permissions.Permissions.GRANT,
        user2.id: sampledb.logic.permissions.Permissions.WRITE
    }
    assert not sampledb.logic.permissions.object_is_public(object.object_id)

