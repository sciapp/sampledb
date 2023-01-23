# coding: utf-8
"""

"""

import pytest
import sampledb
from sampledb.logic.components import add_component
from sampledb.models import User, UserType
from sampledb.logic import instruments, errors

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'


@pytest.fixture
def component():
    component = add_component(address=None, uuid=UUID_1, name='Example component', description='')
    return component


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
    instrument = instruments.get_instrument(instrument_id=instrument.id)
    assert len(instrument.responsible_users) == 1
    with pytest.raises(errors.UserAlreadyResponsibleForInstrumentError):
        instruments.add_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id)
    instruments.remove_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id)
    instrument = instruments.get_instrument(instrument_id=instrument.id)
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
    user1 = sampledb.logic.users.create_user(name="Testuser", email="example@example.com", type=UserType.PERSON)
    user2 = sampledb.logic.users.create_user(name="Testuser", email="example@example.com", type=UserType.PERSON)
    instrument = instruments.create_instrument()
    assert len(instrument.responsible_users) == 0
    instruments.set_instrument_responsible_users(instrument.id, [user1.id])
    instrument = instruments.get_instrument(instrument_id=instrument.id)
    assert len(instrument.responsible_users) == 1
    assert user1 in instrument.responsible_users
    instruments.set_instrument_responsible_users(instrument.id, [user2.id])
    instrument = instruments.get_instrument(instrument_id=instrument.id)
    assert len(instrument.responsible_users) == 1
    assert user2 in instrument.responsible_users
    instruments.set_instrument_responsible_users(instrument.id, [user1.id, user2.id])
    instrument = instruments.get_instrument(instrument_id=instrument.id)
    assert len(instrument.responsible_users) == 2
    assert user1 in instrument.responsible_users
    assert user2 in instrument.responsible_users
    instruments.set_instrument_responsible_users(instrument.id, [])
    instrument = instruments.get_instrument(instrument_id=instrument.id)
    assert len(instrument.responsible_users) == 0


def test_create_instrument_fed(component):
    assert len(instruments.get_instruments()) == 0
    instrument = instruments.create_instrument(fed_id=1, component_id=component.id)
    assert len(instruments.get_instruments()) == 1
    assert instrument == instruments.get_instrument(instrument_id=instrument.id)
    assert len(instrument.responsible_users) == 0
    assert instrument.fed_id == 1
    assert instrument.component_id == component.id


def test_create_instrument_fed_exceptions(component):
    assert len(instruments.get_instruments()) == 0
    with pytest.raises(errors.ComponentDoesNotExistError):
        instruments.create_instrument(fed_id=1, component_id=component.id + 1)
    with pytest.raises(TypeError):
        instruments.create_instrument(component_id=component.id)
    with pytest.raises(TypeError):
        instruments.create_instrument(fed_id=1)
    assert len(instruments.get_instruments()) == 0


def test_get_instrument_fed(component):
    created_instrument = instruments.create_instrument(fed_id=1, component_id=component.id)
    instrument = instruments.get_instrument(1, component.id)
    assert created_instrument == instrument


def test_get_instrument_fed_exceptions(component):
    with pytest.raises(errors.InstrumentDoesNotExistError):
        instruments.get_instrument(1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        instruments.get_instrument(1, component.id + 1)


def test_check_instrument_exists():
    instrument = instruments.create_instrument()
    instruments.check_instrument_exists(instrument.id)
    with pytest.raises(errors.InstrumentDoesNotExistError):
        instruments.check_instrument_exists(instrument.id + 1)
