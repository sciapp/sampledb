# coding: utf-8
"""

"""

import pytest

import sampledb.logic.users
from sampledb.logic import instruments
import sampledb.__main__ as scripts


@pytest.fixture
def instrument():
    instrument = instruments.create_instrument()
    assert instrument.id is not None
    return instrument


@pytest.fixture
def users():
    return [
        sampledb.logic.users.create_user(
            name=f'User {i}',
            email='user{i}@example.com',
            type=sampledb.models.UserType.PERSON
        )
        for i in range(1, 4)
    ]


def test_update_instrument_responsible_users(instrument, users, capsys):
    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0
    instruments.add_instrument_responsible_user(instrument.id, users[0].id)
    instruments.add_instrument_responsible_user(instrument.id, users[1].id)
    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 2
    assert instrument.responsible_users == [users[0], users[1]] or instrument.responsible_users == [users[1], users[0]]

    scripts.main([scripts.__file__, 'update_instrument_responsible_users', str(instrument.id), str(users[0].id), str(users[2].id)])
    assert "Success" in capsys.readouterr()[0]

    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 2
    assert instrument.responsible_users == [users[0], users[2]] or instrument.responsible_users == [users[2], users[0]]

    scripts.main([scripts.__file__, 'update_instrument_responsible_users', str(instrument.id)])
    assert "Success" in capsys.readouterr()[0]

    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0


def test_update_instrument_responsible_users_missing_user(instrument, capsys):
    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument_responsible_users', str(instrument.id), '42'])
    assert exc_info.value != 0
    assert "Error: no user with the id #42 exists" in capsys.readouterr()[1]

    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0


def test_update_instrument_responsible_users_invalid_user(instrument, capsys):
    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument_responsible_users', str(instrument.id), 'User 1'])
    assert exc_info.value != 0
    assert "Error: instrument_reponsible_user_ids must be integer" in capsys.readouterr()[1]

    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0


def test_update_instrument_responsible_users_missing_instrument(users, capsys):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument_responsible_users', '1', str(users[0].id)])
    assert exc_info.value != 0
    assert "Error: no instrument with this id exists" in capsys.readouterr()[1]


def test_update_instrument_responsible_users_invalid_instrument(instrument, users, capsys):
    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument_responsible_users', 'Example Instrument', str(users[0].id)])
    assert exc_info.value != 0
    assert "Error: instrument_id must be an integer" in capsys.readouterr()[1]

    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0


def test_update_instrument_responsible_users_missing_arguments(instrument, users, capsys):
    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument_responsible_users'])
    assert exc_info.value != 0
    assert "Usage" in capsys.readouterr()[0]

    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0