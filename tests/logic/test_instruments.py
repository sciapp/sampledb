# coding: utf-8
"""

"""

import pytest
import sampledb
from sampledb.models import User, UserType
from sampledb.logic import instruments, errors


def test_create_instrument():
    assert len(instruments.get_instruments()) == 0
    instrument = instruments.create_instrument()
    assert len(instruments.get_instruments()) == 1
    assert instrument == instruments.get_instrument(instrument_id=instrument.id)
    assert len(instrument.responsible_users) == 0


def test_update_instrument():
    instrument = instruments.create_instrument(
        description_is_markdown=False,
        users_can_create_log_entries=False,
        users_can_view_log_entries=False,
        notes_is_markdown=False,
        create_log_entry_default=False,
        is_hidden=False,
        short_description_is_markdown=False
    )
    instruments.update_instrument(
        instrument_id=instrument.id,
        description_is_markdown=False,
        users_can_create_log_entries=True,
        users_can_view_log_entries=False,
        notes_is_markdown=False,
        create_log_entry_default=False,
        is_hidden=True,
        short_description_is_markdown=False
    )
    instrument = instruments.get_instrument(instrument_id=instrument.id)
    assert instrument.description_is_markdown is False
    assert instrument.users_can_create_log_entries is True
    assert instrument.users_can_view_log_entries is False
    assert instrument.notes_is_markdown is False
    assert instrument.create_log_entry_default is False
    assert instrument.is_hidden is True
    assert instrument.short_description_is_markdown is False
    assert len(instrument.responsible_users) == 0


def test_instrument_responsible_users():
    user = User(name="Testuser", email="example@example.com", type=UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    instrument = instruments.create_instrument()
    assert len(instrument.responsible_users) == 0
    instruments.add_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id)
    assert len(instrument.responsible_users) == 1
    with pytest.raises(errors.UserAlreadyResponsibleForInstrumentError):
        instruments.add_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id)
    instruments.remove_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id)
    assert len(instrument.responsible_users) == 0
    with pytest.raises(errors.UserNotResponsibleForInstrumentError):
        instruments.remove_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id)
    with pytest.raises(errors.InstrumentDoesNotExistError):
        instruments.add_instrument_responsible_user(instrument_id=instrument.id+1, user_id=user.id)
    with pytest.raises(errors.UserDoesNotExistError):
        instruments.add_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id+1)
    with pytest.raises(errors.InstrumentDoesNotExistError):
        instruments.remove_instrument_responsible_user(instrument_id=instrument.id+1, user_id=user.id)
    with pytest.raises(errors.UserDoesNotExistError):
        instruments.remove_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id+1)


def test_get_missing_instrument():
    instrument = instruments.create_instrument()
    with pytest.raises(errors.InstrumentDoesNotExistError):
        instruments.get_instrument(instrument_id=instrument.id+1)


def test_update_missing_instrument():
    instrument = instruments.create_instrument()
    with pytest.raises(errors.InstrumentDoesNotExistError):
        instruments.update_instrument(
            instrument_id=instrument.id+1
        )


def test_set_instrument_responsible_users():
    user1 = User(name="Testuser", email="example@example.com", type=UserType.PERSON)
    user2 = User(name="Testuser", email="example@example.com", type=UserType.PERSON)
    sampledb.db.session.add(user1)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()
    instrument = instruments.create_instrument()
    assert len(instrument.responsible_users) == 0
    instruments.set_instrument_responsible_users(instrument.id, [user1.id])
    assert len(instrument.responsible_users) == 1
    assert user1 in instrument.responsible_users
    instruments.set_instrument_responsible_users(instrument.id, [user2.id])
    assert len(instrument.responsible_users) == 1
    assert user2 in instrument.responsible_users
    instruments.set_instrument_responsible_users(instrument.id, [user1.id, user2.id])
    assert len(instrument.responsible_users) == 2
    assert user1 in instrument.responsible_users
    assert user2 in instrument.responsible_users
    instruments.set_instrument_responsible_users(instrument.id, [])
    assert len(instrument.responsible_users) == 0
