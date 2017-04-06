# coding: utf-8
"""

"""

import jsonschema
import pytest
import sampledb
from sampledb.models import User, UserType
from sampledb.logic import instruments
from sampledb.logic import schemas


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@pytest.fixture(autouse=True)
def app_context():
    app = sampledb.create_app()
    with app.app_context():
        # fully empty the database first
        sampledb.db.MetaData(reflect=True, bind=sampledb.db.engine).drop_all()
        # recreate the tables used by this application
        sampledb.db.metadata.create_all(bind=sampledb.db.engine)
        yield app


def test_create_instrument():
    assert len(instruments.get_instruments()) == 0
    instrument = instruments.create_instrument(name="Example Instrument", description="")
    assert len(instruments.get_instruments()) == 1
    assert instrument == instruments.get_instrument(instrument_id=instrument.id)
    assert len(instrument.responsible_users) == 0


def test_update_instrument():
    instrument = instruments.create_instrument(name="Example Instrument", description="")
    instruments.update_instrument(instrument_id=instrument.id, name="Test", description="desc")
    instrument = instruments.get_instrument(instrument_id=instrument.id)
    assert instrument.name == "Test"
    assert instrument.description == "desc"
    assert len(instrument.responsible_users) == 0


def test_instrument_responsible_users():
    user = User(name="Testuser", email="example@fz-juelich.de", type=UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    instrument = instruments.create_instrument(name="Example Instrument", description="")
    assert len(instrument.responsible_users) == 0
    instruments.add_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id)
    assert len(instrument.responsible_users) == 1
    instruments.remove_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id)
    assert len(instrument.responsible_users) == 0


def test_create_action():
    schema = {
        'title': 'Example Action',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example Attribute',
                'type': 'text'
            }
        }
    }
    assert len(instruments.get_actions()) == 0
    action = instruments.create_action(name="Example Action", description="", schema=schema)
    assert action.name == "Example Action"
    assert action.description == ""
    assert action.schema == schema
    assert len(instruments.get_actions()) == 1
    assert action == instruments.get_action(action_id=action.id)


def test_create_action_invalid_schema():
    schema = {
        'type': 'invalid'
    }
    with pytest.raises(schemas.ValidationError):
        instruments.create_action(name="Example Action", description="", schema=schema)


def test_update_action():
    schema = {
        'title': 'Example Action',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example Attribute',
                'type': 'text'
            }
        }
    }
    action = instruments.create_action(name="Example Action", description="", schema=schema)
    instruments.update_action(action_id=action.id, name="Test", description="desc", schema=schema)
    action = instruments.get_action(action_id=action.id)
    assert action.name == "Test"
    assert action.description == "desc"
    assert action.schema == schema
