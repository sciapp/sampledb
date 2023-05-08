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
    object = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object.id], name_only=True)[0]
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        object=object,
        path=[(object.id, None)],
        referenced_objects=[],
        referencing_objects=[]
    )
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user2.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        object=None,
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
    object = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object.id], name_only=True)[0]
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
    measurement = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[measurement.id], name_only=True)[0]
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        object=object,
        path=[(object.id, None)],
        referenced_objects=[],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=measurement.id,
                component_uuid=None,
                object=measurement,
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
    object = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object.id], name_only=True)[0]
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
    sample = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[sample.id], name_only=True)[0]
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        object=object,
        path=[(object.id, None)],
        referenced_objects=[],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=sample.id,
                component_uuid=None,
                object=sample,
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
    object = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object.id], name_only=True)[0]
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
    sample = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[sample.id], name_only=True)[0]
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
    object = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object.id], name_only=True)[0]
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        object=object,
        path=[(object.id, None)],
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=sample.id,
                component_uuid=None,
                object=sample,
                path=[(object.id, None), -1, (sample.id, None)],
                referenced_objects=[],
                referencing_objects=[]
            )
        ],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=sample.id,
                component_uuid=None,
                object=sample,
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
    object = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object.id], name_only=True)[0]
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
    sample = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[sample.id], name_only=True)[0]
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=sample.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=sample.id,
        component_uuid=None,
        object=sample,
        path=[(sample.id, None)],
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=object.id,
                component_uuid=None,
                object=object,
                path=[(sample.id, None), -1, (object.id, None)],
                referenced_objects=[
                    sampledb.logic.object_relationships.RelatedObjectsTree(
                        object_id=object.id,
                        component_uuid='91402d3c-b1a7-4c7e-8a68-15bfd21ceace',
                        object=None,
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


def test_object_with_sample_without_permissions(sample_action, user):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        }
    }
    object = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    object = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object.id], name_only=True)[0]
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
    sample = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[sample.id], name_only=True)[0]
    sampledb.logic.object_permissions.set_user_object_permissions(user_id=user.id, object_id=object.id, permissions=sampledb.models.Permissions.NONE)
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=sample.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=sample.id,
        component_uuid=None,
        object=sample,
        path=[(sample.id, None)],
        referencing_objects=[],
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=object.id,
                component_uuid=None,
                object=None,
                path=[(sample.id, None), -1, (object.id, None)],
                referenced_objects=None,
                referencing_objects=None
            )
        ]
    )
    sampledb.logic.object_permissions.set_user_object_permissions(user_id=user.id, object_id=object.id, permissions=sampledb.models.Permissions.READ)
    sampledb.logic.object_permissions.set_user_object_permissions(user_id=user.id, object_id=sample.id, permissions=sampledb.models.Permissions.NONE)
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object.id,
        component_uuid=None,
        object=object,
        path=[(object.id, None)],
        referenced_objects=[],
        referencing_objects=[]
    )


def test_object_chain_without_permissions(sample_action, user):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        }
    }
    object1 = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    object1 = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object1.id], name_only=True)[0]
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'sample': {
            '_type': 'sample',
            'object_id': object1.id
        }
    }
    object2 = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    object2 = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object2.id], name_only=True)[0]
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'sample': {
            '_type': 'sample',
            'object_id': object2.id
        }
    }
    object3 = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    object3 = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object3.id], name_only=True)[0]
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'sample': {
            '_type': 'sample',
            'object_id': object3.id
        }
    }
    sampledb.logic.objects.update_object(object1.id, data, user.id)
    object1 = sampledb.logic.object_permissions.get_objects_with_permissions(user_id=user.id, permissions=sampledb.models.Permissions.READ, object_ids=[object1.id], name_only=True)[0]
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object1.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object1.id,
        component_uuid=None,
        path=[(object1.id, None)],
        object=object1,
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=object3.id,
                component_uuid=None,
                path=[(object1.id, None), -1, (object3.id, None)],
                object=object3,
                referenced_objects=[
                    sampledb.logic.object_relationships.RelatedObjectsTree(
                        object_id=object2.id,
                        component_uuid=None,
                        path=[(object1.id, None), -1, (object3.id, None), -1, (object2.id, None)],
                        object=object2,
                        referenced_objects=[
                            sampledb.logic.object_relationships.RelatedObjectsTree(
                                object_id=object1.id,
                                component_uuid=None,
                                path=[(object1.id, None)],
                                object=object1,
                                referenced_objects=None,
                                referencing_objects=None
                            )
                        ],
                        referencing_objects=[]
                    )
                ],
                referencing_objects=[]
            )
        ],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=object2.id,
                component_uuid=None,
                path=[(object1.id, None), -1, (object3.id, None), -1, (object2.id, None)],
                object=object2,
                referenced_objects=None,
                referencing_objects=None
            )
        ]
    )
    sampledb.logic.object_permissions.set_user_object_permissions(user_id=user.id, object_id=object3.id, permissions=sampledb.models.Permissions.NONE)
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object1.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_id=object1.id,
        component_uuid=None,
        path=[(object1.id, None)],
        object=object1,
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=object3.id,
                component_uuid=None,
                path=[(object1.id, None), -1, (object3.id, None)],
                object=None,
                referenced_objects=None,
                referencing_objects=None
            )
        ],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_id=object2.id,
                component_uuid=None,
                path=[(object1.id, None), -2, (object2.id, None)],
                object=object2,
                referenced_objects=[
                    sampledb.logic.object_relationships.RelatedObjectsTree(
                        object_id=object1.id,
                        component_uuid=None,
                        path=[(object1.id, None)],
                        object=object1,
                        referenced_objects=None,
                        referencing_objects=None
                    )
                ],
                referencing_objects=[]
            )
        ]
    )
