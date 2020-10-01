# coding: utf-8
"""

"""

import pytest

import sampledb
import sampledb.logic
from sampledb.logic import favorites
from sampledb.models import Action, Instrument, User, UserType


@pytest.fixture
def users():
    names = ['User 1', 'User 2']
    users = [User(name=name, email="example@fz-juelich.de", type=UserType.PERSON) for name in names]
    for user in users:
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return users


@pytest.fixture
def independent_action():
    action = Action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Example Action',
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {}
        },
        description='',
        instrument_id=None
    )
    sampledb.db.session.add(action)
    sampledb.db.session.commit()
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def instrument():
    instrument = Instrument('Instrument')
    sampledb.db.session.add(instrument)
    sampledb.db.session.commit()
    # force attribute refresh
    assert instrument.id is not None
    return instrument


def test_favorite_action(independent_action, users):
    assert favorites.get_user_favorite_action_ids(user_id=users[0].id) == []
    assert favorites.get_user_favorite_action_ids(user_id=users[1].id) == []

    favorites.add_favorite_action(action_id=independent_action.id, user_id=users[0].id)

    assert favorites.get_user_favorite_action_ids(user_id=users[0].id) == [independent_action.id]
    assert favorites.get_user_favorite_action_ids(user_id=users[1].id) == []

    favorites.add_favorite_action(action_id=independent_action.id, user_id=users[1].id)

    assert favorites.get_user_favorite_action_ids(user_id=users[0].id) == [independent_action.id]
    assert favorites.get_user_favorite_action_ids(user_id=users[1].id) == [independent_action.id]

    favorites.remove_favorite_action(action_id=independent_action.id, user_id=users[0].id)

    assert favorites.get_user_favorite_action_ids(user_id=users[0].id) == []
    assert favorites.get_user_favorite_action_ids(user_id=users[1].id) == [independent_action.id]


def test_favorite_instrument(instrument, users):
    assert favorites.get_user_favorite_instrument_ids(user_id=users[0].id) == []
    assert favorites.get_user_favorite_instrument_ids(user_id=users[1].id) == []

    favorites.add_favorite_instrument(instrument_id=instrument.id, user_id=users[0].id)

    assert favorites.get_user_favorite_instrument_ids(user_id=users[0].id) == [instrument.id]
    assert favorites.get_user_favorite_instrument_ids(user_id=users[1].id) == []

    favorites.add_favorite_instrument(instrument_id=instrument.id, user_id=users[1].id)

    assert favorites.get_user_favorite_instrument_ids(user_id=users[0].id) == [instrument.id]
    assert favorites.get_user_favorite_instrument_ids(user_id=users[1].id) == [instrument.id]

    favorites.remove_favorite_instrument(instrument_id=instrument.id, user_id=users[0].id)

    assert favorites.get_user_favorite_instrument_ids(user_id=users[0].id) == []
    assert favorites.get_user_favorite_instrument_ids(user_id=users[1].id) == [instrument.id]
