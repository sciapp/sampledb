# coding: utf-8
"""

"""

import pytest

import sampledb
import sampledb.logic
import sampledb.models
from sampledb.models import User, UserType, ActionType

from ..test_utils import flask_server, app, app_context


@pytest.fixture
def sample_action():
    action = sampledb.logic.actions.create_action(
        action_type=ActionType.SAMPLE_CREATION,
        name="",
        description="",
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                },
                'sample': {
                    'title': 'Sample',
                    'type': 'sample'
                }
            },
            'required': ['name']
        }
    )
    return action


@pytest.fixture
def measurement_action():
    action = sampledb.logic.actions.create_action(
        action_type=ActionType.MEASUREMENT,
        name="",
        description="",
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                },
                'sample': {
                    'title': 'Sample',
                    'type': 'sample'
                }
            },
            'required': ['name']
        }
    )
    return action


@pytest.fixture
def user():
    user = User(name="User", email="example@fz-juelich.de", type=UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert user.id is not None
    return user


def test_single_object(sample_action, user):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object Name'
        }
    }
    object = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == {
        'object_id': object.id,
        'path': [object.id],
        'previous_objects': [],
        'samples': [],
        'measurements': []
    }


def test_object_with_measurement(sample_action, measurement_action, user):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        }
    }
    object = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'sample': {
            '_type': 'sample',
            'object_id': object.id
        }
    }
    measurement = sampledb.logic.objects.create_object(measurement_action.id, data, user.id)
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == {
        'object_id': object.id,
        'path': [object.id],
        'measurements': [
            {
                'object_id': measurement.id,
                'path': [object.id, -1, measurement.id],
                'measurements': [],
                'samples': [],
                'previous_objects': []
            }
        ],
        'samples': [],
        'previous_objects': []
    }


def test_object_with_sample(sample_action, user):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        }
    }
    object = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'sample': {
            '_type': 'sample',
            'object_id': object.id
        }
    }
    sample = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == {
        'object_id': object.id,
        'path': [object.id],
        'measurements': [],
        'samples': [
            {
                'object_id': sample.id,
                'path': [object.id, -3, sample.id],
                'measurements': [],
                'samples': [],
                'previous_objects': []
            }
        ],
        'previous_objects': []
    }


def test_object_with_cyclic_sample(sample_action, user):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        }
    }
    object = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'sample': {
            '_type': 'sample',
            'object_id': object.id
        }
    }
    sample = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'sample': {
            '_type': 'sample',
            'object_id': sample.id
        }
    }
    sampledb.logic.objects.update_object(object.id, data, user.id)
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == {
        'object_id': object.id,
        'path': [object.id],
        'measurements': [],
        'samples': [
            {
                'object_id': sample.id,
                'path': [object.id, -2, sample.id]
            }
        ],
        'previous_objects': [
            {
                'object_id': sample.id,
                'path': [object.id, -2, sample.id],
                'measurements': [],
                'samples': [],
                'previous_objects': []
            }
        ]
    }
