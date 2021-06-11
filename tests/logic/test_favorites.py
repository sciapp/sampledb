# coding: utf-8
"""

"""

import pytest

import sampledb
import sampledb.logic
from sampledb.logic import favorites, action_translations, languages, instrument_translations
from sampledb.models import Action, Instrument, User, UserType


@pytest.fixture
def users():
    names = ['User 1', 'User 2']
    users = [User(name=name, email="example@example.com", type=UserType.PERSON) for name in names]
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
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {}
        },
        instrument_id=None
    )
    sampledb.db.session.add(action)
    sampledb.db.session.commit()
    action_translations.set_action_translation(
        language_id=languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description='',
    )
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def instrument():
    instrument = Instrument()
    sampledb.db.session.add(instrument)
    sampledb.db.session.commit()
    instrument_translations.set_instrument_translation(
        language_id=languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name='Example Instrument',
        description=''
    )
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
