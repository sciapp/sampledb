# coding: utf-8
"""

"""
import json
import os
import requests
import pytest

import sampledb
import sampledb.models
import sampledb.logic


@pytest.fixture
def user_session(flask_server):
    user = sampledb.models.User(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    session.user_id = user.id
    return session


@pytest.fixture
def action(flask_server):
    action = sampledb.models.Action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'plotly_chart': {
                    'title': 'Plotly Chart',
                    'type': 'plotly_chart'
                }
            },
            'required': ['name']
        },
        instrument_id=None
    )
    sampledb.db.session.add(action)
    sampledb.db.session.commit()
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )
    # force attribute refresh
    assert action.id is not None
    return action


def test_generate_pdfexport(action, flask_server, user_session):
    object = sampledb.logic.objects.create_object(action.id, {
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_session.user_id)
    r = user_session.get(flask_server.base_url + 'objects/{}/export'.format(object.object_id))
    assert r.status_code == 200
    assert len(r.content) > 0
    assert r.headers["Content-Disposition"] == 'attachment; filename=sampledb_export.pdf'


def test_generate_pdfexport_for_object_ids(action, flask_server, user_session):
    object = sampledb.logic.objects.create_object(action.id, {
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_session.user_id)
    r = user_session.get(flask_server.base_url + 'objects/{0}/export?object_ids=[{0}]'.format(object.object_id))
    assert r.status_code == 200
    assert len(r.content) > 0
    assert r.headers["Content-Disposition"] == 'attachment; filename=sampledb_export.pdf'


def test_generate_pdfexport_for_empty_objects(action, flask_server, user_session):
    object = sampledb.logic.objects.create_object(action.id, {
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_session.user_id)
    r = user_session.get(flask_server.base_url + 'objects/{}/export?object_ids=[]'.format(object.object_id))
    assert r.status_code == 400


def test_generate_pdfexport_for_invalid_json(action, flask_server, user_session):
    object = sampledb.logic.objects.create_object(action.id, {
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_session.user_id)
    r = user_session.get(flask_server.base_url + 'objects/{}/export?object_ids=[7"'.format(object.object_id))
    assert r.status_code == 400


def test_generate_pdfexport_for_plotly_chart(action, flask_server, user_session):
    with open(os.path.join(os.path.dirname(sampledb.__file__), 'scripts', 'demo_data', 'objects', 'plotly-example-data1.sampledb.json'), 'r') as f:
        plotly_json = json.load(f)
    object = sampledb.logic.objects.create_object(action.id, {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'plotly_chart': {
            '_type': 'plotly_chart',
            'plotly': plotly_json
        }
    }, user_session.user_id)
    r = user_session.get(flask_server.base_url + 'objects/{0}/export?object_ids=[{0}]'.format(object.object_id))
    assert r.status_code == 200
    assert len(r.content) > 0
    assert r.headers["Content-Disposition"] == 'attachment; filename=sampledb_export.pdf'
