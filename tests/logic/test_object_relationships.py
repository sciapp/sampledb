# coding: utf-8
"""

"""
import uuid

import pytest

import sampledb
import sampledb.logic
import sampledb.models
from sampledb.logic.object_relationships import WorkflowElement
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
        object_ref=sampledb.logic.object_relationships.ObjectRef(
            object_id=object.id,
            component_uuid=None,
            eln_source_url=None,
            eln_object_url=None,
        ),
        object=object,
        path=[sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
        referenced_objects=[],
        referencing_objects=[]
    )
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user2.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_ref=sampledb.logic.object_relationships.ObjectRef(
            object_id=object.id,
            component_uuid=None,
            eln_source_url=None,
            eln_object_url=None,
        ),
        object=None,
        path=[sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
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
        object_ref=sampledb.logic.object_relationships.ObjectRef(
            object_id=object.id,
            component_uuid=None,
            eln_source_url=None,
            eln_object_url=None,
        ),
        object=object,
        path=[sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
        referenced_objects=[],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_ref=sampledb.logic.object_relationships.ObjectRef(
                    object_id=measurement.id,
                    component_uuid=None,
                    eln_source_url=None,
                    eln_object_url=None,
                ),
                object=measurement,
                path=[sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -2, sampledb.logic.object_relationships.ObjectRef(object_id=measurement.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
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
        object_ref=sampledb.logic.object_relationships.ObjectRef(
            object_id=object.id,
            component_uuid=None,
            eln_source_url=None,
            eln_object_url=None,
        ),
        object=object,
        path=[sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
        referenced_objects=[],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_ref=sampledb.logic.object_relationships.ObjectRef(
                    object_id=sample.id,
                    component_uuid=None,
                    eln_source_url=None,
                    eln_object_url=None,
                ),
                object=sample,
                path=[sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -2, sampledb.logic.object_relationships.ObjectRef(object_id=sample.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
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
        object_ref=sampledb.logic.object_relationships.ObjectRef(
            object_id=object.id,
            component_uuid=None,
            eln_source_url=None,
            eln_object_url=None,
        ),
        object=object,
        path=[sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_ref=sampledb.logic.object_relationships.ObjectRef(
                    object_id=sample.id,
                    component_uuid=None,
                    eln_source_url=None,
                    eln_object_url=None,
                ),
                object=sample,
                path=[sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=sample.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
                referenced_objects=[],
                referencing_objects=[]
            )
        ],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_ref=sampledb.logic.object_relationships.ObjectRef(
                    object_id=sample.id,
                    component_uuid=None,
                    eln_source_url=None,
                    eln_object_url=None,
                ),
                object=sample,
                path=[sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=sample.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
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
        object_ref=sampledb.logic.object_relationships.ObjectRef(
            object_id=sample.id,
            component_uuid=None,
            eln_source_url=None,
            eln_object_url=None,
        ),
        object=sample,
        path=[sampledb.logic.object_relationships.ObjectRef(object_id=sample.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_ref=sampledb.logic.object_relationships.ObjectRef(
                    object_id=object.id,
                    component_uuid=None,
                    eln_source_url=None,
                    eln_object_url=None,
                ),
                object=object,
                path=[sampledb.logic.object_relationships.ObjectRef(object_id=sample.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
                referenced_objects=[
                    sampledb.logic.object_relationships.RelatedObjectsTree(
                        object_ref=sampledb.logic.object_relationships.ObjectRef(
                            object_id=object.id,
                            component_uuid='91402d3c-b1a7-4c7e-8a68-15bfd21ceace',
                            eln_source_url=None,
                            eln_object_url=None,
                        ),
                        object=None,
                        path=[sampledb.logic.object_relationships.ObjectRef(object_id=sample.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=1, component_uuid='91402d3c-b1a7-4c7e-8a68-15bfd21ceace', eln_source_url=None, eln_object_url=None)],
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
        object_ref=sampledb.logic.object_relationships.ObjectRef(
            object_id=sample.id,
            component_uuid=None,
            eln_source_url=None,
            eln_object_url=None,
        ),
        object=sample,
        path=[sampledb.logic.object_relationships.ObjectRef(object_id=sample.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
        referencing_objects=[],
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_ref=sampledb.logic.object_relationships.ObjectRef(
                    object_id=object.id,
                    component_uuid=None,
                    eln_source_url=None,
                    eln_object_url=None,
                ),
                object=None,
                path=[sampledb.logic.object_relationships.ObjectRef(object_id=sample.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
                referenced_objects=None,
                referencing_objects=None
            )
        ]
    )
    sampledb.logic.object_permissions.set_user_object_permissions(user_id=user.id, object_id=object.id, permissions=sampledb.models.Permissions.READ)
    sampledb.logic.object_permissions.set_user_object_permissions(user_id=user.id, object_id=sample.id, permissions=sampledb.models.Permissions.NONE)
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_ref=sampledb.logic.object_relationships.ObjectRef(
            object_id=object.id,
            component_uuid=None,
            eln_source_url=None,
            eln_object_url=None,
        ),
        object=object,
        path=[sampledb.logic.object_relationships.ObjectRef(object_id=object.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
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
        object_ref=sampledb.logic.object_relationships.ObjectRef(
            object_id=object1.id,
            component_uuid=None,
            eln_source_url=None,
            eln_object_url=None,
        ),
        path=[sampledb.logic.object_relationships.ObjectRef(object_id=object1.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
        object=object1,
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_ref=sampledb.logic.object_relationships.ObjectRef(
                    object_id=object3.id,
                    component_uuid=None,
                    eln_source_url=None,
                    eln_object_url=None,
                ),
                path=[sampledb.logic.object_relationships.ObjectRef(object_id=object1.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=object3.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
                object=object3,
                referenced_objects=[
                    sampledb.logic.object_relationships.RelatedObjectsTree(
                        object_ref=sampledb.logic.object_relationships.ObjectRef(
                            object_id=object2.id,
                            component_uuid=None,
                            eln_source_url=None,
                            eln_object_url=None,
                        ),
                        path=[sampledb.logic.object_relationships.ObjectRef(object_id=object1.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=object3.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=object2.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
                        object=object2,
                        referenced_objects=[
                            sampledb.logic.object_relationships.RelatedObjectsTree(
                                object_ref=sampledb.logic.object_relationships.ObjectRef(
                                    object_id=object1.id,
                                    component_uuid=None,
                                    eln_source_url=None,
                                    eln_object_url=None,
                                ),
                                path=[sampledb.logic.object_relationships.ObjectRef(object_id=object1.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
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
                object_ref=sampledb.logic.object_relationships.ObjectRef(
                    object_id=object2.id,
                    component_uuid=None,
                    eln_source_url=None,
                    eln_object_url=None,
                ),
                path=[sampledb.logic.object_relationships.ObjectRef(object_id=object1.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=object3.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=object2.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
                object=object2,
                referenced_objects=None,
                referencing_objects=None
            )
        ]
    )
    sampledb.logic.object_permissions.set_user_object_permissions(user_id=user.id, object_id=object3.id, permissions=sampledb.models.Permissions.NONE)
    tree = sampledb.logic.object_relationships.build_related_objects_tree(object_id=object1.id, user_id=user.id)
    assert tree == sampledb.logic.object_relationships.RelatedObjectsTree(
        object_ref=sampledb.logic.object_relationships.ObjectRef(
            object_id=object1.id,
            component_uuid=None,
            eln_source_url=None,
            eln_object_url=None,
        ),
        path=[sampledb.logic.object_relationships.ObjectRef(object_id=object1.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
        object=object1,
        referenced_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_ref=sampledb.logic.object_relationships.ObjectRef(
                    object_id=object3.id,
                    component_uuid=None,
                    eln_source_url=None,
                    eln_object_url=None,
                ),
                path=[sampledb.logic.object_relationships.ObjectRef(object_id=object1.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -1, sampledb.logic.object_relationships.ObjectRef(object_id=object3.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
                object=None,
                referenced_objects=None,
                referencing_objects=None
            )
        ],
        referencing_objects=[
            sampledb.logic.object_relationships.RelatedObjectsTree(
                object_ref=sampledb.logic.object_relationships.ObjectRef(
                    object_id=object2.id,
                    component_uuid=None,
                    eln_source_url=None,
                    eln_object_url=None,
                ),
                path=[sampledb.logic.object_relationships.ObjectRef(object_id=object1.id, component_uuid=None, eln_source_url=None, eln_object_url=None), -2, sampledb.logic.object_relationships.ObjectRef(object_id=object2.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
                object=object2,
                referenced_objects=[
                    sampledb.logic.object_relationships.RelatedObjectsTree(
                        object_ref=sampledb.logic.object_relationships.ObjectRef(
                            object_id=object1.id,
                            component_uuid=None,
                            eln_source_url=None,
                            eln_object_url=None,
                        ),
                        path=[sampledb.logic.object_relationships.ObjectRef(object_id=object1.id, component_uuid=None, eln_source_url=None, eln_object_url=None)],
                        object=object1,
                        referenced_objects=None,
                        referencing_objects=None
                    )
                ],
                referencing_objects=[]
            )
        ]
    )


def test_get_referenced_object_ids(sample_action, user):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        }
    }
    object1 = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        }
    }
    object2 = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    multi_reference_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                },
                'samples': {
                    'title': 'Samples',
                    'type': 'array',
                    'items': {
                        'title': 'Sample',
                        'type': 'sample'
                    }
                }
            },
            'required': ['name']
        }
    )
    component_uuid = str(uuid.uuid4())
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'samples': [
            {
                '_type': 'sample',
                'object_id': object1.id
            },
            {
                '_type': 'sample',
                'object_id': object1.id
            },
            {
                '_type': 'sample',
                'object_id': object2.id
            },
            {
                '_type': 'sample',
                'object_id': 42,
                'component_uuid': component_uuid
            },
            {
                '_type': 'sample',
                'object_id': 42,
                'eln_source_url': 'https://example.org',
                'eln_object_url': 'https://example.org/objects/42'
            }
        ]
    }
    object3 = sampledb.logic.objects.create_object(multi_reference_action.id, data, user.id)
    assert set(sampledb.logic.object_relationships._get_referenced_object_ids({object3.id})[object3.id]) == {
        sampledb.logic.object_relationships.ObjectRef(object_id=object1.id, component_uuid=None, eln_source_url=None, eln_object_url=None),
        sampledb.logic.object_relationships.ObjectRef(object_id=object2.id, component_uuid=None, eln_source_url=None, eln_object_url=None),
        sampledb.logic.object_relationships.ObjectRef(object_id=42, component_uuid=component_uuid, eln_source_url=None, eln_object_url=None), sampledb.logic.object_relationships.ObjectRef(object_id=42, component_uuid=None, eln_source_url='https://example.org', eln_object_url='https://example.org/objects/42')
    }


def test_get_workflow_references(sample_action, measurement_action, user):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        }
    }
    sample = sampledb.logic.objects.create_object(sample_action.id, data, user.id)

    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 3'
        }
    }
    bidirectional_sample = sampledb.logic.objects.create_object(sample_action.id, data, user.id)

    component = sampledb.logic.components.add_component(address=None, uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example component', description='')#
    object_permissions_data = sampledb.logic.federation.objects.ObjectPermissionsData(
        users={user.id: sampledb.models.Permissions.READ},
        groups={}, projects={}, all_users=sampledb.models.Permissions.NONE
    )
    object_version_data = sampledb.logic.federation.objects.ObjectVersionData(
        fed_version_id=0, user=None, data=None, schema=None, utc_datetime=None, import_notes=[]
    )
    object_data = sampledb.logic.federation.objects.ObjectData(
        fed_object_id=1, component_id=component.id,
        action=None, versions=[object_version_data], comments=[], files=[], object_location_assignments=[],
        permissions=object_permissions_data, sharing_user=None
    )
    import_status = {}
    fed_no_data_sample = sampledb.logic.federation.objects.import_object(object_data, component, import_status=import_status)

    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        }
    }
    no_permission_sample = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    sampledb.logic.object_permissions.set_user_object_permissions(no_permission_sample.object_id, user.id, sampledb.models.Permissions.NONE)

    workflow_schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Object Name',
                'type': 'text'
            },
            'sample_1': {
                'title': 'Sample 1',
                'type': 'sample'
            },
            'sample_2': {
                'title': 'Sample 2',
                'type': 'sample'
            },
            'sample_3': {
                'title': 'Sample 3',
                'type': 'sample'
            },
            'sample_4': {
                'title': 'Sample 4',
                'type': 'object_reference'
            }
        },
        'required': ['name'],
        'workflow_view': {
            'referencing_action_type_id': sampledb.models.ActionType.MEASUREMENT,
            'referenced_action_id': sample_action.id
        }
    }
    workflow_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=workflow_schema
    )
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'sample_1': {
            '_type': 'sample',
            'object_id': sample.object_id
        },
        'sample_2': {
            '_type': 'sample',
            'object_id': bidirectional_sample.object_id
        },
        'sample_3': {
            '_type': 'sample',
            'object_id': no_permission_sample.object_id
        },
        'sample_4': {
            '_type': 'object_reference',
            'object_id': fed_no_data_sample.object_id
        }
    }
    workflow_object = sampledb.logic.objects.create_object(workflow_action.id, data, user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'sample': {
            '_type': 'sample',
            'object_id': workflow_object.object_id
        }
    }
    measurement = sampledb.logic.objects.create_object(measurement_action.id, data, user.id)

    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 3'
        },
        'sample': {
            '_type': 'sample',
            'object_id': workflow_object.object_id
        }
    }
    sampledb.logic.objects.update_object(bidirectional_sample.object_id, data, user.id)
    bidirectional_sample = sampledb.logic.objects.get_object(bidirectional_sample.object_id)
    file = sampledb.logic.files.create_database_file(sample.object_id, user.id, 'test.txt', lambda f: f.write(b'test'))
    sampledb.logic.files.create_database_file(no_permission_sample.object_id, user.id, 'test.txt', lambda f: f.write(b'test'))

    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert workflow == [
        WorkflowElement(sample.object_id, sample, sample_action, is_referenced=True, is_referencing=False, files=[file]),
        WorkflowElement(bidirectional_sample.object_id, bidirectional_sample, sample_action, is_referenced=True, is_referencing=True, files=[]),
        WorkflowElement(no_permission_sample.object_id, None, sample_action, is_referenced=True, is_referencing=False, files=[]),
        WorkflowElement(measurement.object_id, measurement, measurement_action, is_referenced=False, is_referencing=True, files=[])
    ]

    workflow_schema['workflow_view'] = {
            'referencing_action_type_id': sampledb.models.ActionType.MEASUREMENT,
            'referencing_action_id': [],
            'referenced_action_id': sample_action.id,
            'referenced_action_type_id': []
        }
    sampledb.logic.actions.update_action(action_id=workflow_action.id, schema=workflow_schema)
    sampledb.logic.objects.update_object(object_id=workflow_object.object_id, schema=workflow_schema, data=workflow_object.data, user_id=user.id)
    workflow_object = sampledb.logic.objects.get_object(workflow_object.object_id)
    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert len(workflow) == 0

    workflow_schema['workflow_view'] = {
        'referencing_action_type_id': [],
        'referencing_action_id': measurement_action.id,
        'referenced_action_id': [],
        'referenced_action_type_id': sampledb.models.ActionType.SAMPLE_CREATION
    }
    sampledb.logic.actions.update_action(action_id=workflow_action.id, schema=workflow_schema)
    sampledb.logic.objects.update_object(object_id=workflow_object.object_id, schema=workflow_schema, data=workflow_object.data, user_id=user.id)
    workflow_object = sampledb.logic.objects.get_object(workflow_object.object_id)
    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert len(workflow) == 0

    workflow_schema['workflow_view'] = {
        'referencing_action_id': measurement_action.id,
        'referenced_action_type_id': sampledb.models.ActionType.SAMPLE_CREATION
    }
    sampledb.logic.actions.update_action(action_id=workflow_action.id, schema=workflow_schema)
    sampledb.logic.objects.update_object(object_id=workflow_object.object_id, schema=workflow_schema, data=workflow_object.data, user_id=user.id)
    workflow_object = sampledb.logic.objects.get_object(workflow_object.object_id)
    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert workflow == [
        WorkflowElement(sample.object_id, sample, sample_action, is_referenced=True, is_referencing=False, files=[file]),
        WorkflowElement(bidirectional_sample.object_id, bidirectional_sample, sample_action, is_referenced=True, is_referencing=True, files=[]),
        WorkflowElement(no_permission_sample.object_id, None, sample_action, is_referenced=True, is_referencing=False, files=[]),
        WorkflowElement(measurement.object_id, measurement, measurement_action, is_referenced=False, is_referencing=True, files=[])
    ]

    workflow_schema['workflow_view'] = {
        'referencing_action_id': measurement_action.id,
        'referenced_action_id': []
    }
    sampledb.logic.actions.update_action(action_id=workflow_action.id, schema=workflow_schema)
    sampledb.logic.objects.update_object(object_id=workflow_object.object_id, schema=workflow_schema, data=workflow_object.data, user_id=user.id)
    workflow_object = sampledb.logic.objects.get_object(workflow_object.object_id)
    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert workflow == [
        WorkflowElement(measurement.object_id, measurement, measurement_action, is_referenced=False, is_referencing=True, files=[])
    ]

    workflow_schema['workflow_view'] = {
        'referencing_action_id': [measurement_action.id, sample_action.id],
        'referenced_action_id': []
    }
    sampledb.logic.actions.update_action(action_id=workflow_action.id, schema=workflow_schema)
    sampledb.logic.objects.update_object(object_id=workflow_object.object_id, schema=workflow_schema,
                                         data=workflow_object.data, user_id=user.id)
    workflow_object = sampledb.logic.objects.get_object(workflow_object.object_id)
    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert workflow == [
        WorkflowElement(bidirectional_sample.object_id, bidirectional_sample, sample_action, is_referenced=True, is_referencing=True, files=[]),
        WorkflowElement(measurement.object_id, measurement, measurement_action, is_referenced=False, is_referencing=True, files=[])
    ]

    workflow_schema['workflow_view'] = {
        'referenced_action_type_id': sampledb.models.ActionType.SAMPLE_CREATION,
        'referencing_action_id': []
    }
    sampledb.logic.actions.update_action(action_id=workflow_action.id, schema=workflow_schema)
    sampledb.logic.objects.update_object(object_id=workflow_object.object_id, schema=workflow_schema,
                                         data=workflow_object.data, user_id=user.id)
    workflow_object = sampledb.logic.objects.get_object(workflow_object.object_id)
    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert workflow == [
        WorkflowElement(sample.object_id, sample, sample_action, is_referenced=True, is_referencing=False, files=[file]),
        WorkflowElement(bidirectional_sample.object_id, bidirectional_sample, sample_action, is_referenced=True, is_referencing=True, files=[]),
        WorkflowElement(no_permission_sample.object_id, None, sample_action, is_referenced=True, is_referencing=False, files=[])
    ]

    workflow_schema['workflow_view'] = {
        'referencing_action_id': measurement_action.id
    }
    sampledb.logic.actions.update_action(action_id=workflow_action.id, schema=workflow_schema)
    sampledb.logic.objects.update_object(object_id=workflow_object.object_id, schema=workflow_schema, data=workflow_object.data, user_id=user.id)
    workflow_object = sampledb.logic.objects.get_object(workflow_object.object_id)
    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert workflow == [
        WorkflowElement(sample.object_id, sample, sample_action, is_referenced=True, is_referencing=False, files=[file]),
        WorkflowElement(bidirectional_sample.object_id, bidirectional_sample, sample_action, is_referenced=True, is_referencing=True, files=[]),
        WorkflowElement(no_permission_sample.object_id, None, sample_action, is_referenced=True, is_referencing=False, files=[]),
        WorkflowElement(measurement.object_id, measurement, measurement_action, is_referenced=False, is_referencing=True, files=[]),
        WorkflowElement(fed_no_data_sample.object_id, fed_no_data_sample, None, is_referenced=True, is_referencing=False, files=[])
    ]

    workflow_schema['workflow_view'] = {
        'referenced_action_type_id': sampledb.models.ActionType.SAMPLE_CREATION
    }
    sampledb.logic.actions.update_action(action_id=workflow_action.id, schema=workflow_schema)
    sampledb.logic.objects.update_object(object_id=workflow_object.object_id, schema=workflow_schema, data=workflow_object.data, user_id=user.id)
    workflow_object = sampledb.logic.objects.get_object(workflow_object.object_id)
    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert workflow == [
        WorkflowElement(sample.object_id, sample, sample_action, is_referenced=True, is_referencing=False, files=[file]),
        WorkflowElement(bidirectional_sample.object_id, bidirectional_sample, sample_action, is_referenced=True, is_referencing=True, files=[]),
        WorkflowElement(no_permission_sample.object_id, None, sample_action, is_referenced=True, is_referencing=False, files=[]),
        WorkflowElement(measurement.object_id, measurement, measurement_action, is_referenced=False, is_referencing=True, files=[])
    ]

    workflow_schema['workflow_view'] = {
        'referencing_action_type_id': sampledb.models.ActionType.SAMPLE_CREATION,
        'referenced_action_id': measurement_action.id
    }
    sampledb.logic.actions.update_action(action_id=workflow_action.id, schema=workflow_schema)
    sampledb.logic.objects.update_object(object_id=workflow_object.object_id, schema=workflow_schema, data=workflow_object.data, user_id=user.id)
    workflow_object = sampledb.logic.objects.get_object(workflow_object.object_id)
    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert workflow == [
        WorkflowElement(bidirectional_sample.object_id, bidirectional_sample, sample_action, is_referenced=True, is_referencing=True, files=[]),
    ]

    workflow_schema['workflow_view'] = {}
    sampledb.logic.actions.update_action(action_id=workflow_action.id, schema=workflow_schema)
    sampledb.logic.objects.update_object(object_id=workflow_object.object_id, schema=workflow_schema, data=workflow_object.data, user_id=user.id)
    workflow_object = sampledb.logic.objects.get_object(workflow_object.object_id)
    workflow = sampledb.logic.object_relationships.get_workflow_references(workflow_object, user.id)
    assert workflow == [
        WorkflowElement(sample.object_id, sample, sample_action, is_referenced=True, is_referencing=False, files=[file]),
        WorkflowElement(bidirectional_sample.object_id, bidirectional_sample, sample_action, is_referenced=True, is_referencing=True, files=[]),
        WorkflowElement(no_permission_sample.object_id, None, sample_action, is_referenced=True, is_referencing=False, files=[]),
        WorkflowElement(measurement.object_id, measurement, measurement_action, is_referenced=False, is_referencing=True, files=[]),
        WorkflowElement(fed_no_data_sample.object_id, fed_no_data_sample, None, is_referenced=True, is_referencing=False, files=[])
    ]
