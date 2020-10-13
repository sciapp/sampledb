# coding: utf-8
"""

"""

import pytest

from sampledb import db
import sampledb.logic
from sampledb.logic import object_sorting
import sampledb.models
from sampledb.models import Action, User


@pytest.fixture
def user() -> User:
    user = sampledb.models.User(
        name="User",
        email="example@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def action() -> Action:
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name="",
        description="",
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
        }
    )
    return action


def test_limit_objects(user: User, action: Action) -> None:
    for i in range(10):
        sampledb.logic.objects.create_object(action_id=action.id, data={
            'name': {
                '_type': 'text',
                'text': str(i)
            }
        }, user_id=user.id)

    num_objects_found = []

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.object_id()), num_objects_found=num_objects_found)
    assert len(objects) == 10
    assert num_objects_found[0] == 10
    for i, object in enumerate(objects):
        assert object.data['name']['text'] == str(i)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.object_id()), limit=4, num_objects_found=num_objects_found)
    assert len(objects) == 4
    assert num_objects_found[0] == 10
    for i, object in enumerate(objects):
        assert object.data['name']['text'] == str(i)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.object_id()), limit=20, num_objects_found=num_objects_found)
    assert len(objects) == 10
    assert num_objects_found[0] == 10
    for i, object in enumerate(objects):
        assert object.data['name']['text'] == str(i)


def test_offset_objects(user: User, action: Action) -> None:
    for i in range(10):
        sampledb.logic.objects.create_object(action_id=action.id, data={
            'name': {
                '_type': 'text',
                'text': str(i)
            }
        }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.object_id()))
    assert len(objects) == 10
    for i, object in enumerate(objects, start=0):
        assert object.data['name']['text'] == str(i)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.object_id()), offset=6)
    assert len(objects) == 4
    for i, object in enumerate(objects, start=6):
        assert object.data['name']['text'] == str(i)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.object_id()), limit=3, offset=6)
    assert len(objects) == 3
    for i, object in enumerate(objects, start=6):
        assert object.data['name']['text'] == str(i)
