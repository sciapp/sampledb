# coding: utf-8
"""

"""

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

import pytest
from sampledb import db
import sampledb.logic
import sampledb.models

from ..test_utils import flask_server, app, app_context


@pytest.fixture
def user():
    user = sampledb.models.User(
        name="User",
        email="example@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def action():
    action = sampledb.logic.actions.create_action(
        action_type=sampledb.logic.actions.ActionType.SAMPLE_CREATION,
        name="",
        description="",
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'tags': {
                    'title': 'Tags',
                    'type': 'tags'
                }
            },
            'required': []
        }
    )
    return action


def test_find_by_tag(user, action) -> None:
    data = {
        'tags': {
            '_type': 'tags',
            'tags': ['tag1', 'tag2', 'tag3']
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'tags': {
            '_type': 'tags',
            'tags': ['tag2', 'tag3']
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    filter_func = sampledb.logic.object_search.generate_filter_func('#tag1', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert 'tag1' in object.data['tags']['tags']


def test_find_by_unknown_tag(user, action) -> None:
    data = {
        'tags': {
            '_type': 'tags',
            'tags': ['tag1', 'tag2', 'tag3']
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'tags': {
            '_type': 'tags',
            'tags': ['tag2', 'tag3']
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    filter_func = sampledb.logic.object_search.generate_filter_func('#tag4', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0
