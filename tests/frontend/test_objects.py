# coding: utf-8
"""

"""

import os
import json
import requests
import pytest

import sampledb
import sampledb.models
import sampledb.logic
from sampledb.rest_api.objects import SCHEMA_DIR


from tests.test_utils import flask_server, app


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def test_get_object(flask_server, user):
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'minimal.json')))
    action = sampledb.logic.instruments.create_action('Example Action', '', schema)
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
    action = sampledb.logic.instruments.create_action('Example Action', '', schema)
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
    action = sampledb.logic.instruments.create_action('Example Action', '', schema)
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
    action = sampledb.logic.instruments.create_action('Example Action', '', schema)
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
    action = sampledb.logic.instruments.create_action('Example Action', '', schema)
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
    action = sampledb.logic.instruments.create_action('Example Action', '', schema)
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
    action = sampledb.logic.instruments.create_action('Example Action', '', schema)
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
    schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe.custom.json')))
    object_data = json.load(open(os.path.join(os.path.dirname(sampledb.__file__), '..', 'example_data', 'ombe.json')))
    action = sampledb.logic.instruments.create_action('Example Action', '', schema)
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
    form_data = {'object_multilayer_2_films_0_elements_0_name_text': 'Pd', 'object_multilayer_3_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_1_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_0_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_checkbox_hidden': 'checkbox exists', 'object_multilayer_2_films_1_substrate_temperature_magnitude': '130', 'object_multilayer_1_films_0_elements_0_rate_magnitude': '1', 'object_multilayer_0_films_0_thickness_magnitude': '5', 'object_multilayer_1_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_elements_0_name_text': 'Ag', 'object_multilayer_2_films_1_elements_0_rate_magnitude': '0.05', 'object_multilayer_0_films_0_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_thickness_magnitude': '1500', 'object_multilayer_0_films_0_thickness_units': 'Å', 'object_multilayer_0_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_name_text': 'Pd', 'object_substrate_text': 'GaAs', 'object_multilayer_3_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_3_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_2_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_elements_0_rate_magnitude': '0.01', 'object_multilayer_2_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_2_films_1_name_text': 'Fe', 'object_multilayer_2_films_1_oxygen_flow_units': 'cm**3/s', 'object_created_datetime': '2017-02-24 11:56:00', 'object_multilayer_2_films_0_substrate_temperature_magnitude': '100', 'object_multilayer_1_films_0_name_text': 'Buffer Layer', 'object_multilayer_2_repetitions_magnitude': '10', 'object_multilayer_2_films_1_elements_0_name_text': 'Fe', 'object_multilayer_2_films_1_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_substrate_temperature_units': 'degC', 'object_multilayer_0_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_3_films_0_thickness_magnitude': '150', 'object_multilayer_2_films_0_elements_0_frequency_change_magnitude': '', 'object_multilayer_1_repetitions_magnitude': '1', 'object_name_text': 'Example', 'object_multilayer_2_films_1_substrate_temperature_units': 'degC', 'object_multilayer_2_films_1_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_0_thickness_magnitude': '150', 'object_multilayer_0_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_2_films_0_name_text': 'Pd', 'object_multilayer_1_films_0_elements_0_frequency_change_units': 'Hz / s', 'object_multilayer_2_films_1_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_1_thickness_magnitude': '10', 'object_multilayer_3_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_0_repetitions_magnitude': '2', 'object_multilayer_1_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_0_oxygen_flow_units': 'cm**3/s', 'object_multilayer_3_films_0_elements_0_rate_magnitude': '0.1', 'object_multilayer_1_films_0_substrate_temperature_magnitude': '130', 'object_multilayer_0_films_0_elements_0_fraction_magnitude': '', 'object_multilayer_2_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_2_films_1_thickness_units': 'Å', 'object_multilayer_0_films_0_name_text': 'Seed Layer', 'object_multilayer_1_films_0_thickness_units': 'Å', 'object_multilayer_3_films_0_oxygen_flow_magnitude': '0', 'object_multilayer_3_films_0_name_text': 'Pd Layer', 'object_multilayer_2_films_0_thickness_units': 'Å', 'object_multilayer_1_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_0_films_0_elements_0_rate_units': 'Å/s', 'object_multilayer_3_films_0_substrate_temperature_magnitude': '100', 'object_dropdown_text': 'option 2', 'object_multilayer_3_repetitions_magnitude': '1'}
    r = session.post(flask_server.base_url + 'objects/{}'.format(object.object_id), data=form_data)
    assert r.status_code == 200
    object = sampledb.models.Objects.get_object_version(object_id=object.object_id, version_id=1)
    assert object.data['name']['text'] == 'Example'
