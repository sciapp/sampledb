# coding: utf-8
"""
Example data for testing sampledb
"""

import json
import flask
import flask_login
import sqlalchemy
import sampledb
from sampledb.models import Objects, User, UserType, ActionType, AuthenticationType
from sampledb.logic.instruments import create_instrument, add_instrument_responsible_user
from sampledb.logic.actions import create_action
from sampledb.logic.object_log import create_object
from sampledb.logic import groups, permissions, projects, comments, files

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def setup_data(app):
    # TODO: replace using user management logic
    admin = User(name="Administrator", email="example@fz-juelich.de", type=UserType.PERSON)
    admin.is_admin = True
    instrument_responsible_user = User(name="Instrument Responsible User", email="example@fz-juelich.de", type=UserType.PERSON)
    basic_user = User(name="Basic User", email="example@fz-juelich.de", type=UserType.PERSON)
    for user in (admin, instrument_responsible_user, basic_user):
        sampledb.db.session.add(user)
    sampledb.db.session.commit()

    api_user = User(name="API User", email="example@fz-juelich.de", type=UserType.OTHER)
    sampledb.logic.authentication.insert_user_and_authentication_method_to_db(api_user, 'password', 'api', AuthenticationType.OTHER)

    group_id = groups.create_group("Example Group", "This is an example group for testing purposes.", instrument_responsible_user.id).id

    project_id = projects.create_project("Example Project", "This is an example project", instrument_responsible_user.id).id
    project_id2 = projects.create_project("Example Project 2", "This is another example project", instrument_responsible_user.id).id
    projects.create_subproject_relationship(parent_project_id=project_id, child_project_id=project_id2, child_can_add_users_to_parent=True)

    # Setup autologin for testing
    @app.route('/users/me/autologin')
    @app.route('/users/<int:user_id>/autologin')
    def autologin(user_id=instrument_responsible_user.id):
        user = User.query.get(user_id)
        assert user is not None
        flask_login.login_user(user)
        return flask.redirect(flask.url_for('frontend.object', object_id=5))

    sampledb.login_manager.login_view = 'autologin'

    instrument = create_instrument(name="OMBE I", description="This is an example instrument.")
    add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
    with open('sampledb/schemas/ombe_measurement.sampledb.json', 'r') as schema_file:
        schema = json.load(schema_file)
    instrument_action = create_action(ActionType.SAMPLE_CREATION, "Sample Creation", "This is an example action", schema, instrument.id)
    independent_action = create_action(ActionType.SAMPLE_CREATION, "Alternative Process", "This is an example action", schema)
    with open('sampledb/schemas/ombe_measurement_batch.sampledb.json', 'r') as schema_file:
        batch_schema = json.load(schema_file)
    create_action(ActionType.SAMPLE_CREATION, "Sample Creation (Batch)", "This is an example action", batch_schema, instrument.id)
    sampledb.db.session.commit()

    with open('example_data/ombe-1.sampledb.json', 'r') as data_file:
        data = json.load(data_file)
    instrument_object = Objects.create_object(data=data, schema=schema, user_id=instrument_responsible_user.id, action_id=instrument_action.id, connection=sampledb.db.engine)
    create_object(object_id=instrument_object.object_id, user_id=instrument_responsible_user.id)
    data['multilayer'][0]['repetitions']['magnitude_in_base_units'] = 20000
    data['multilayer'][1]['films'][0]['thickness']['magnitude_in_base_units'] = 1
    independent_object = Objects.create_object(data=data, schema=schema, user_id=instrument_responsible_user.id, action_id=independent_action.id, connection=sampledb.db.engine)
    create_object(object_id=independent_object.object_id, user_id=instrument_responsible_user.id)
    comments.create_comment(instrument_object.id, instrument_responsible_user.id, 'This comment is very long. ' * 20 + '\n' + 'This comment has three paragraphs. ' * 20 + '\n' + '\n' + 'This comment has three paragraphs. ' * 20)
    comments.create_comment(instrument_object.id, instrument_responsible_user.id, 'This is another, shorter comment')
    files.create_file(instrument_object.id, instrument_responsible_user.id, 'example.txt', lambda stream: stream.write("Dies ist ein Test".encode('utf-8')))
    files.create_file(instrument_object.id, instrument_responsible_user.id, 'demo.png', lambda stream: stream.write(open('sampledb/static/img/ghs01.png', 'rb').read()))
    files.update_file_information(instrument_object.id, 1, instrument_responsible_user.id, 'Example File', 'This is a file description.')

    with open('server_schemas/ombe_measurement.sampledb.json', 'r') as schema_file:
        schema = json.load(schema_file)
    sampledb.logic.actions.update_action(instrument_action.id, "Updated Sample Creation", "", schema)

    permissions.set_group_object_permissions(independent_object.object_id, group_id, permissions.Permissions.READ)

    instrument = create_instrument(name="XRR", description="X-Ray Reflectometry")
    add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
    with open('sampledb/schemas/xrr_measurement.sampledb.json', 'r') as schema_file:
        schema = json.load(schema_file)
    instrument_action = create_action(ActionType.MEASUREMENT, "XRR Measurement", "", schema, instrument.id)
    with open('sampledb/schemas/searchable_quantity.json', 'r') as schema_file:
        schema = json.load(schema_file)
    action = create_action(ActionType.SAMPLE_CREATION, "Searchable Object", "", schema, None)
    independent_object = Objects.create_object(data={
        "name": {
            "_type": "text",
            "text": "TEST-1"
        },
        "tags": {
            "_type": "tags",
            "tags": ["tag1", "tag2"]
        },
        "mass": {
            "_type": "quantity",
            "dimensionality": "[mass]",
            "magnitude_in_base_units": 0.00001,
            "units": "mg"
        }
    }, schema=schema, user_id=instrument_responsible_user.id, action_id=action.id, connection=sampledb.db.engine)
    create_object(object_id=independent_object.object_id, user_id=instrument_responsible_user.id)
    permissions.set_group_object_permissions(independent_object.object_id, group_id, permissions.Permissions.READ)
    permissions.set_user_object_permissions(independent_object.object_id, api_user.id, permissions.Permissions.WRITE)
    independent_object = Objects.create_object(data={
        "name": {
            "_type": "text",
            "text": "TEST-2"
        },
        "tags": {
            "_type": "tags",
            "tags": ["tag2", "tag3"]
        },
        "mass": {
            "_type": "quantity",
            "dimensionality": "[mass]",
            "magnitude_in_base_units": 0.000005,
            "units": "mg"
        }
    }, schema=schema, user_id=instrument_responsible_user.id, action_id=action.id, connection=sampledb.db.engine)
    create_object(object_id=independent_object.object_id, user_id=instrument_responsible_user.id)
    permissions.set_group_object_permissions(independent_object.object_id, group_id, permissions.Permissions.READ)
    sampledb.db.session.commit()

    instrument = create_instrument(name="MPMS SQUID", description="MPMS SQUID Magnetometer JCNS-2")
    add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
    with open('server_schemas/squid_measurement.sampledb.json', 'r') as schema_file:
        schema = json.load(schema_file)
    instrument_action = create_action(ActionType.MEASUREMENT, "Perform Measurement", "", schema, instrument.id)
    sampledb.db.session.commit()

    instrument = create_instrument(name="Powder Diffractometer", description="Huber Imaging Plate Guinier Camera G670 at JCNS-2")
    add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
    with open('server_schemas/powder_diffractometer_measurement.sampledb.json', 'r') as schema_file:
        schema = json.load(schema_file)
    instrument_action = create_action(ActionType.MEASUREMENT, "Perform Measurement", "", schema, instrument.id)
    sampledb.db.session.commit()

    instrument = create_instrument(name="GALAXI", description="Gallium Anode Low-Angle X-ray Instrument")
    add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
    with open('server_schemas/galaxi_measurement.sampledb.json', 'r') as schema_file:
        schema = json.load(schema_file)
    instrument_action = create_action(ActionType.MEASUREMENT, "Perform Measurement", "", schema, instrument.id)
    sampledb.db.session.commit()

    with open('server_schemas/other_sample.sampledb.json', 'r') as schema_file:
        schema = json.load(schema_file)
    create_action(ActionType.SAMPLE_CREATION, "Other Sample", "", schema, None)
    sampledb.db.session.commit()

    sample_action = sampledb.logic.actions.create_action(
        action_type=ActionType.SAMPLE_CREATION,
        name="sample_action",
        description="",
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                },
                'sample': {
                    'title': 'Sample',
                    'type': 'sample'
                }
            },
            'required': ['name']
        }
    )
    measurement_action = sampledb.logic.actions.create_action(
        action_type=ActionType.MEASUREMENT,
        name="measurement_action",
        description="",
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                },
                'sample': {
                    'title': 'Sample',
                    'type': 'sample'
                }
            },
            'required': ['name']
        }
    )
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        }
    }
    object = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    sampledb.logic.permissions.set_object_public(object.id, True)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 2'
        },
        'sample': {
            '_type': 'sample',
            'object_id': object.id
        }
    }
    sample = sampledb.logic.objects.create_object(sample_action.id, data, user.id)
    sampledb.logic.permissions.set_object_public(sample.id, True)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Object 1'
        },
        'sample': {
            '_type': 'sample',
            'object_id': sample.id
        }
    }
    sampledb.logic.objects.update_object(object.id, data, user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Measurement'
        },
        'sample': {
            '_type': 'sample',
            'object_id': object.id
        }
    }
    measurement = sampledb.logic.objects.create_object(measurement_action.id, data, user.id)
    sampledb.logic.permissions.set_object_public(measurement.id, True)
