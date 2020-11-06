# coding: utf-8
"""

"""

import pytest
import sampledb
from sampledb.logic import instruments, instrument_log_entries, errors


@pytest.fixture
def instrument(flask_server):
    with flask_server.app.app_context():
        instrument = instruments.create_instrument(name="Example Instrument", description="")
        # force attribute refresh
        assert instrument.id is not None
    return instrument


@pytest.fixture
def users(flask_server):
    with flask_server.app.app_context():
        users = [
            sampledb.models.User(name=name, email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
            for name in ("Other User", "Instrument Scientist")
        ]
        for user in users:
            sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        for user in users:
            assert user.id is not None
    return users


@pytest.fixture
def other_user(users):
    return users[0]


@pytest.fixture
def instrument_responsible_user(users, instrument):
    sampledb.logic.instruments.add_instrument_responsible_user(instrument.id, users[1].id)
    return users[1]


def test_create_log_entry(instrument, instrument_responsible_user, other_user):

    assert len(instrument_log_entries.get_instrument_log_entries(instrument.id)) == 0
    instrument_log_entries.create_instrument_log_entry(instrument.id, instrument_responsible_user.id, "test")
    assert len(instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1
    instrument_log_entries.create_instrument_log_entry(instrument.id, other_user.id, "test2")
    assert len(instrument_log_entries.get_instrument_log_entries(instrument.id)) == 2
    log_entries = instrument_log_entries.get_instrument_log_entries(instrument.id)
    assert log_entries[0].author == instrument_responsible_user
    assert log_entries[0].versions[-1].content == "test"
    assert log_entries[1].author == other_user
    assert log_entries[1].versions[-1].content == "test2"
    for i in range(2):
        assert log_entries[i].instrument_id == instrument.id
        assert instrument_log_entries.get_instrument_log_entry(log_entries[i].id) == log_entries[i]

    with pytest.raises(errors.InstrumentDoesNotExistError):
        instrument_log_entries.create_instrument_log_entry(instrument.id + 1, instrument_responsible_user.id, "test")

    with pytest.raises(errors.InstrumentLogEntryDoesNotExistError):
        assert instrument_log_entries.get_instrument_log_entry(4)

def test_log_entry_categories(instrument, instrument_responsible_user):
    category_a = instrument_log_entries.create_instrument_log_category(
        instrument_id=instrument.id,
        title="Category A",
        theme=instrument_log_entries.InstrumentLogCategoryTheme.GRAY
    )
    category_b = instrument_log_entries.create_instrument_log_category(
        instrument_id=instrument.id,
        title="Category B",
        theme=instrument_log_entries.InstrumentLogCategoryTheme.RED
    )
    assert set(instrument_log_entries.get_instrument_log_categories(instrument.id)) == {category_a, category_b}

    log_entry = instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=instrument_responsible_user.id,
        content="test",
        category_ids=[
            category_a.id,
            category_b.id
        ]
    )
    assert set(log_entry.versions[-1].categories) == {category_a, category_b}
    instrument_log_entries.update_instrument_log_category(
        category_id=category_a.id,
        title="Category A+",
        theme=instrument_log_entries.InstrumentLogCategoryTheme.GREEN
    )
    instrument_log_entries.delete_instrument_log_category(category_b.id)
    assert category_b not in set(instrument_log_entries.get_instrument_log_categories(instrument.id))

    log_entry = instrument_log_entries.get_instrument_log_entry(log_entry.id)
    assert len(log_entry.versions[-1].categories) == 1
    assert log_entry.versions[-1].categories[0].title == "Category A+"
    assert log_entry.versions[-1].categories[0].theme.name.lower() == 'green'

    log_entry = instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=instrument_responsible_user.id,
        content="test"
    )
    assert len(log_entry.versions[-1].categories) == 0

    with pytest.raises(errors.InstrumentLogCategoryDoesNotExistError):
        instrument_log_entries.create_instrument_log_entry(
            instrument_id=instrument.id,
            user_id=instrument_responsible_user.id,
            content="test",
            category_ids=[category_b.id]
        )
