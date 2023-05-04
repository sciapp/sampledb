# coding: utf-8
"""

"""

import pytest

import sampledb
import sampledb.logic
import sampledb.models
from sampledb.models import User, UserType


@pytest.fixture
def sample_action():
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
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
        action_type_id=sampledb.models.ActionType.MEASUREMENT,
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
    user = User(name="User", email="example@example.com", type=UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert user.id is not None
    return user


@pytest.fixture
def user2():
    user = User(name="User2", email="example@example.com", type=UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert user.id is not None
    return user


def test_single_object(sample_action, user, user2):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object Name'
        }
    }
    object = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        permissions='grant',
        path=[(object.id, None)],
        referenced_objects=[],
        referencing_objects=[]
    )
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user2.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        permissions='none',
        path=[(object.id, None)],
        referenced_objects=None,
        referencing_objects=None
    )


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
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        permissions='grant',
        path=[(object.id, None)],
        referenced_objects=[],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=measurement.id,
                component_uuid=None,
                permissions='grant',
                path=[(object.id, None), -2, (measurement.id, None)],
                referenced_objects=[],
                referencing_objects=[]
            )
        ]
    )


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
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        permissions='grant',
        path=[(object.id, None)],
        referenced_objects=[],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=sample.id,
                component_uuid=None,
                permissions='grant',
                path=[(object.id, None), -2, (sample.id, None)],
                referenced_objects=[],
                referencing_objects=[]
            )
        ]
    )


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
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        permissions='grant',
        path=[(object.id, None)],
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=sample.id,
                component_uuid=None,
                permissions='grant',
                path=[(object.id, None), -1, (sample.id, None)],
                referenced_objects=[],
                referencing_objects=[]
            )
        ],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=sample.id,
                component_uuid=None,
                permissions='grant',
                path=[(object.id, None), -1, (sample.id, None)],
                referenced_objects=None,
                referencing_objects=None
            )
        ]
    )


def test_object_with_unknown_sample(sample_action, user):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        },
        'sample': {
            '_type': 'sample',
            'object_id': 1,
            'component_uuid': '91402d3c-b1a7-4c7e-8a68-15bfd21ceace'
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
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=sample.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=sample.id,
        component_uuid=None,
        permissions='grant',
        path=[(sample.id, None)],
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=object.id,
                component_uuid=None,
                permissions='grant',
                path=[(sample.id, None), -1, (object.id, None)],
                referenced_objects=[
                    sampledb.logic.object_relationships.RelatedObjectsTree(
                        object_id=1,
                        component_uuid='91402d3c-b1a7-4c7e-8a68-15bfd21ceace',
                        permissions='none',
                        path=[(sample.id, None), -1, (object.id, None), -1, (1, '91402d3c-b1a7-4c7e-8a68-15bfd21ceace')],
                        referenced_objects=None,
                        referencing_objects=None
                    )
                ],
                referencing_objects=[]
            )
        ],
        referencing_objects=[]
    )
