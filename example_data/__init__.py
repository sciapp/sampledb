# coding: utf-8
"""
Example data for testing sampledb
"""

import json
import flask
import flask_login
import sqlalchemy
import sampledb
from sampledb.models import Objects
from sampledb.models import User, UserType
from sampledb.logic.instruments import create_instrument, add_instrument_responsible_user, create_action

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def setup_data(app):

    # fully empty the database first
    sqlalchemy.MetaData(reflect=True, bind=sampledb.db.engine).drop_all()
    # recreate the tables used by this application
    sampledb.db.metadata.create_all(bind=sampledb.db.engine)

    # TODO: replace using user management logic
    admin = User(name="Administrator", email="example@fz-juelich.de", type=UserType.PERSON)
    admin.is_admin = True
    instrument_responsible_user = User(name="Instrument Responsible User", email="example@fz-juelich.de", type=UserType.PERSON)
    basic_user = User(name="Basic User", email="example@fz-juelich.de", type=UserType.PERSON)
    for user in (admin, instrument_responsible_user, basic_user):
        sampledb.db.session.add(user)
    sampledb.db.session.commit()

    # Setup autologin for testing
    @app.route('/users/me/autologin')
    @app.route('/users/<int:user_id>/autologin')
    def autologin(user_id=instrument_responsible_user.id):
        user = User.query.get(user_id)
        assert user is not None
        flask_login.login_user(user)
        return flask.redirect(flask.url_for('frontend.object', object_id=1))

    sampledb.login_manager.login_view = 'autologin'

    instrument = create_instrument(name="Example Instrument", description="This is an example instrument.")
    add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
    with open('sampledb/schemas/ombe.custom.json', 'r') as schema_file:
        schema = json.load(schema_file)
    instrument_action = create_action("Example action", "This is an example action", schema, instrument.id)
    independent_action = create_action("Example action", "This is an example action", schema)
    sampledb.db.session.commit()

    with open('example_data/ombe.json', 'r') as data_file:
        data = json.load(data_file)
    instrument_object = Objects.create_object(data=data, schema=schema, user_id=instrument_responsible_user.id, action_id=instrument_action.id, connection=sampledb.db.engine)
    independent_object = Objects.create_object(data=data, schema=schema, user_id=instrument_responsible_user.id, action_id=independent_action.id, connection=sampledb.db.engine)
