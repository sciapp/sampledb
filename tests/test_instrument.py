# coding: utf-8
"""

"""

import jsonschema
import pytest
import sampledb
from sampledb.authentication.models import User, UserType
from sampledb.instruments import logic, models


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
    assert len(logic.get_instruments()) == 0
    instrument = logic.create_instrument(name="Example Instrument", description="")
    assert len(logic.get_instruments()) == 1
    assert instrument == logic.get_instrument(instrument_id=instrument.id)
    assert len(instrument.responsible_users) == 0


def test_update_instrument():
    instrument = logic.create_instrument(name="Example Instrument", description="")
    logic.update_instrument(instrument_id=instrument.id, name="Test", description="desc")
    instrument = logic.get_instrument(instrument_id=instrument.id)
    assert instrument.name == "Test"
    assert instrument.description == "desc"
    assert len(instrument.responsible_users) == 0


def test_instrument_responsible_users():
    user = User(name="Testuser", email="example@fz-juelich.de", type=UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    instrument = logic.create_instrument(name="Example Instrument", description="")
    assert len(instrument.responsible_users) == 0
    logic.add_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id)
    assert len(instrument.responsible_users) == 1
    logic.remove_instrument_responsible_user(instrument_id=instrument.id, user_id=user.id)
    assert len(instrument.responsible_users) == 0


def test_create_action():
    schema = {
        'type': 'object',
        'properties': {
            'example': {
                'type': 'string'
            }
        }
    }
    assert len(logic.get_actions()) == 0
    action = logic.create_action(name="Example Action", description="", schema=schema)
    assert action.name == "Example Action"
    assert action.description == ""
    assert action.schema == schema
    assert len(logic.get_actions()) == 1
    assert action == logic.get_action(action_id=action.id)


def test_create_action_invalid_schema():
    schema = {
        'type': 'invalid'
    }
    with pytest.raises(jsonschema.SchemaError):
        logic.create_action(name="Example Action", description="", schema=schema)


def test_update_action():
    schema = {
        'type': 'object',
        'properties': {
            'example': {
                'type': 'string'
            }
        }
    }
    action = logic.create_action(name="Example Action", description="", schema=schema)
    logic.update_action(action_id=action.id, name="Test", description="desc", schema=schema)
    action = logic.get_action(action_id=action.id)
    assert action.name == "Test"
    assert action.description == "desc"
    assert action.schema == schema
