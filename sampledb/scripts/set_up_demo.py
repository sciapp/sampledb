# coding: utf-8
"""
Script for setting up demo data in a previously unused SampleDB installation.

Usage: python -m sampledb set_up_demo
"""

import json
import os
import sys


import sampledb
from .. import create_app
from sampledb.models import Objects, UserType, ActionType
from sampledb.logic.instruments import create_instrument, add_instrument_responsible_user
from sampledb.logic.actions import create_action
from sampledb.logic.object_log import create_object
from ..logic import groups, object_permissions, projects, comments, files


def main(arguments):
    if len(arguments) != 0:
        print(__doc__)
        exit(1)
    app = create_app()
    if not app.config.get("SERVER_NAME"):
        app.config["SERVER_NAME"] = "localhost:8000"
    with app.app_context():
        if sampledb.logic.actions.get_actions() or sampledb.logic.instruments.get_instruments() or len(sampledb.logic.users.get_users()) > 1:
            print("Error: database must be empty for demo", file=sys.stderr)
            exit(1)

        data_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'demo_data'))
        schema_directory = os.path.join(data_directory, 'schemas')
        objects_directory = os.path.join(data_directory, 'objects')

        if sampledb.logic.users.get_users():
            # admin might have been created from environment variables
            admin = sampledb.logic.users.get_users()[0]
        else:
            admin = sampledb.logic.users.create_user(name="Administrator", email="admin@example.com", type=UserType.PERSON)
            sampledb.logic.users.set_user_administrator(admin.id, True)

        instrument_responsible_user = sampledb.logic.users.create_user(name="Instrument Scientist", email="instrument@example.com", type=UserType.PERSON)
        basic_user = sampledb.logic.users.create_user(name="Basic User", email="basic@example.com", type=UserType.PERSON)
        api_user = sampledb.logic.users.create_user(name="API User", email="api@example.com", type=UserType.OTHER)
        sampledb.logic.authentication.add_other_authentication(api_user.id, 'api', 'password')

        group_id = groups.create_group("Example Group", "This is an example group for testing purposes.", instrument_responsible_user.id).id

        project_id = projects.create_project("Example Project", "This is an example project", instrument_responsible_user.id).id
        project_id2 = projects.create_project("Example Project 2", "This is another example project", instrument_responsible_user.id).id
        projects.create_subproject_relationship(parent_project_id=project_id, child_project_id=project_id2, child_can_add_users_to_parent=True)

        markdown_notes = """# Header
    This example shows how Markdown can be used for instrument Notes.

    ## Subheader

    *italics* **bold**


    | A | B | C |
    |--:|:-:|---|
    | Example | 100˚C | 5µm |
    | Data | 110˚C | 6µm |
            """
        instrument = create_instrument(
            name="OMBE I",
            description="This is an example instrument.",
            users_can_create_log_entries=True,
            notes=markdown_notes,
            notes_is_markdown=True
        )
        add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
        log_category_error = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument.id,
            title='Error',
            theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
        )
        log_category_warning = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument.id,
            title='Warning',
            theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.YELLOW
        )
        log_category_success = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument.id,
            title='Success',
            theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.GREEN
        )
        log_category_other = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument.id,
            title='Other',
            theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.BLUE
        )
        log_category_normal = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument.id,
            title='Normal',
            theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.GRAY
        )
        for category in sampledb.logic.instrument_log_entries.get_instrument_log_categories(instrument.id):
            sampledb.logic.instrument_log_entries.create_instrument_log_entry(
                instrument.id, basic_user.id, "This is an example instrument log entry",
                [category.id]
            )
        sampledb.logic.instrument_log_entries.create_instrument_log_entry(
            instrument.id, basic_user.id, "This is an example instrument log entry"
        )
        sampledb.logic.instrument_log_entries.create_instrument_log_entry(
            instrument.id, basic_user.id, "This is an example instrument log entry",
            [log_category_other.id]
        )
        log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
            instrument.id, basic_user.id, "This is an example instrument log entry",
            [log_category_error.id, log_category_warning.id, log_category_normal.id, log_category_success.id]
        )
        sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
            instrument_log_entry_id=log_entry.id,
            file_name="ghs01.png",
            content=open(os.path.join(os.path.dirname(sampledb.__file__), 'static/img/ghs01.png'), 'rb').read()
        )
        sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
            instrument_log_entry_id=log_entry.id,
            file_name="ghs02.png",
            content=open(os.path.join(os.path.dirname(sampledb.__file__), 'static/img/ghs02.png'), 'rb').read()
        )
        sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
            instrument_log_entry_id=log_entry.id,
            file_name="test.txt",
            content="This is a test".encode('utf-8')
        )

        with open(os.path.join(schema_directory, 'ombe_measurement.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        instrument_action = create_action(ActionType.SAMPLE_CREATION, "Sample Creation", "This is an example action", schema, instrument.id)
        sampledb.logic.action_permissions.set_action_public(instrument_action.id)
        independent_action = create_action(ActionType.SAMPLE_CREATION, "Alternative Process", "This is an example action", schema)
        sampledb.logic.action_permissions.set_action_public(independent_action.id)
        with open(os.path.join(schema_directory, 'ombe_measurement_batch.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            batch_schema = json.load(schema_file)
        action = create_action(ActionType.SAMPLE_CREATION, "Sample Creation (Batch)", "This is an example action", batch_schema, instrument.id)
        sampledb.logic.action_permissions.set_action_public(action.id)
        sampledb.db.session.commit()

        with open(os.path.join(objects_directory, 'ombe-1.sampledb.json'), 'r', encoding='utf-8') as data_file:
            data = json.load(data_file)
        instrument_object = Objects.create_object(data=data, schema=schema, user_id=instrument_responsible_user.id, action_id=instrument_action.id, connection=sampledb.db.engine)
        create_object(object_id=instrument_object.object_id, user_id=instrument_responsible_user.id)
        independent_object = Objects.create_object(data=data, schema=schema, user_id=instrument_responsible_user.id, action_id=independent_action.id, connection=sampledb.db.engine)
        create_object(object_id=independent_object.object_id, user_id=instrument_responsible_user.id)
        comments.create_comment(instrument_object.id, instrument_responsible_user.id, 'This comment is very long. ' * 20 + '\n' + 'This comment has three paragraphs. ' * 20 + '\n' + '\n' + 'This comment has three paragraphs. ' * 20)
        comments.create_comment(instrument_object.id, instrument_responsible_user.id, 'This is another, shorter comment')
        files.create_local_file(instrument_object.id, instrument_responsible_user.id, 'example.txt', lambda stream: stream.write("Dies ist ein Test".encode('utf-8')))
        files.create_local_file(instrument_object.id, instrument_responsible_user.id, 'demo.png', lambda stream: stream.write(open(os.path.join(os.path.dirname(sampledb.__file__), 'static/img/ghs01.png'), 'rb').read()))
        files.update_file_information(instrument_object.id, 1, instrument_responsible_user.id, 'Example File', 'This is a file description.')
        files.create_url_file(instrument_object.id, instrument_responsible_user.id, 'http://iffsamples.fz-juelich.de/')

        projects.link_project_and_object(project_id, instrument_object.object_id, instrument_responsible_user.id)

        with open(os.path.join(schema_directory, 'ombe_measurement_updated.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        sampledb.logic.actions.update_action(instrument_action.id, "Updated Sample Creation", "", schema)

        object_permissions.set_group_object_permissions(independent_object.object_id, group_id, object_permissions.Permissions.READ)

        instrument = create_instrument(name="XRR", description="X-Ray Reflectometry")
        add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
        with open(os.path.join(schema_directory, 'xrr_measurement.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        instrument_action = create_action(ActionType.MEASUREMENT, "XRR Measurement", "", schema, instrument.id)
        sampledb.logic.action_permissions.set_action_public(instrument_action.id)
        with open(os.path.join(schema_directory, 'searchable_quantity.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        action = create_action(ActionType.SAMPLE_CREATION, "Searchable Object", "", schema, None)
        sampledb.logic.action_permissions.set_action_public(action.id)
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
        object_permissions.set_group_object_permissions(independent_object.object_id, group_id, object_permissions.Permissions.READ)
        object_permissions.set_user_object_permissions(independent_object.object_id, api_user.id, object_permissions.Permissions.WRITE)
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
        object_permissions.set_group_object_permissions(independent_object.object_id, group_id, object_permissions.Permissions.READ)
        sampledb.db.session.commit()

        instrument = create_instrument(name="MPMS SQUID", description="MPMS SQUID Magnetometer JCNS-2")
        add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
        with open(os.path.join(schema_directory, 'squid_measurement.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        instrument_action = create_action(ActionType.MEASUREMENT, "Perform Measurement", "", schema, instrument.id)
        sampledb.logic.action_permissions.set_action_public(instrument_action.id)
        sampledb.db.session.commit()

        instrument = create_instrument(name="Powder Diffractometer", description="Huber Imaging Plate Guinier Camera G670 at JCNS-2")
        add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
        with open(os.path.join(schema_directory, 'powder_diffractometer_measurement.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        instrument_action = create_action(ActionType.MEASUREMENT, "Perform Measurement", "", schema, instrument.id)
        sampledb.logic.action_permissions.set_action_public(instrument_action.id)
        sampledb.db.session.commit()

        instrument = create_instrument(name="GALAXI", description="Gallium Anode Low-Angle X-ray Instrument")
        add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
        with open(os.path.join(schema_directory, 'galaxi_measurement.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        instrument_action = create_action(ActionType.MEASUREMENT, "Perform Measurement", "", schema, instrument.id)
        sampledb.logic.action_permissions.set_action_public(instrument_action.id)
        sampledb.db.session.commit()

        with open(os.path.join(schema_directory, 'other_sample.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        action = create_action(ActionType.SAMPLE_CREATION, "Other Sample", "", schema, None)
        sampledb.logic.action_permissions.set_action_public(action.id)
        sampledb.db.session.commit()

        sample_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
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
        sampledb.logic.action_permissions.set_action_public(sample_action.id)
        measurement_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.MEASUREMENT,
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
                    },
                    'comment': {
                        'title': 'Comment',
                        'type': 'text',
                        'markdown': True
                    }
                },
                'required': ['name']
            }
        )
        sampledb.logic.action_permissions.set_action_public(measurement_action.id)
        data = {
            'name': {
                '_type': 'text',
                'text': 'Object 1'
            }
        }
        object = sampledb.logic.objects.create_object(sample_action.id, data, basic_user.id)
        sampledb.logic.object_permissions.set_object_public(object.id, True)
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
        sample = sampledb.logic.objects.create_object(sample_action.id, data, basic_user.id)
        sampledb.logic.object_permissions.set_object_public(sample.id, True)
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
        sampledb.logic.objects.update_object(object.id, data, basic_user.id)
        data = {
            'name': {
                '_type': 'text',
                'text': 'Measurement'
            },
            'sample': {
                '_type': 'sample',
                'object_id': object.id
            },
            'comment': {
                '_type': 'text',
                'text': 'This is a test.\nThis **is** a *second* line.\n\nThis line follows an empty line.',
                'is_markdown': True
            }
        }
        measurement = sampledb.logic.objects.create_object(measurement_action.id, data, basic_user.id)
        sampledb.logic.object_permissions.set_object_public(measurement.id, True)
        data = {
            'name': {
                '_type': 'text',
                'text': 'Measurement 2'
            },
            'sample': {
                '_type': 'sample',
                'object_id': sample.id
            },
            'comment': {
                '_type': 'text',
                'text': 'This is a test.\nThis is a second line.\n\nThis line follows an empty line.'
            }
        }
        measurement = sampledb.logic.objects.create_object(measurement_action.id, data, instrument_responsible_user.id)
        sampledb.logic.object_permissions.set_object_public(measurement.id, True)

        with open(os.path.join(schema_directory, 'plotly.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        plotly_action = create_action(ActionType.SAMPLE_CREATION, "Plotly Example Action", "", schema, None)
        sampledb.logic.action_permissions.set_action_public(plotly_action.id)

        with open(os.path.join(objects_directory, 'plotly-example-data1.sampledb.json'), 'r', encoding='utf-8') as data_file:
            example_data = json.load(data_file)

        data = {
            "name": {
                "_type": "text",
                "text": "Plotly Example Data #1"
            },
            "plot1": {
                "_type": "plotly_chart",
                "plotly": example_data
            }
        }
        plotly_object = sampledb.logic.objects.create_object(plotly_action.id, data, basic_user.id)
        sampledb.logic.object_permissions.set_object_public(plotly_object.id, True)

        with open(os.path.join(schema_directory, 'plotly_array.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        plotly_array_action = create_action(ActionType.SAMPLE_CREATION, "Plotly Array Example Action", "", schema, None)
        sampledb.logic.action_permissions.set_action_public(plotly_array_action.id)

        with open(os.path.join(objects_directory, 'plotly-example-data2.sampledb.json'), 'r', encoding='utf-8') as data_file:
            example_data2 = json.load(data_file)
        with open(os.path.join(objects_directory, 'plotly-example-data3.sampledb.json'), 'r', encoding='utf-8') as data_file:
            example_data3 = json.load(data_file)

        data = {
            "name": {
                "_type": "text",
                "text": "Plotly Array Example"
            },
            "plotlist": [
                {
                    "_type": "plotly_chart",
                    "plotly": example_data
                },
                {
                    "_type": "plotly_chart",
                    "plotly": example_data2
                },
                {
                    "_type": "plotly_chart",
                    "plotly": example_data3
                }
            ]
        }
        plotly_object = sampledb.logic.objects.create_object(plotly_array_action.id, data, basic_user.id)
        sampledb.logic.object_permissions.set_object_public(plotly_object.id, True)
        sampledb.db.session.commit()

        campus = sampledb.logic.locations.create_location("Campus", "Max Mustermann Campus", None, instrument_responsible_user.id)
        building_a = sampledb.logic.locations.create_location("Building A", "Building A on Max Mustermann Campus", campus.id, instrument_responsible_user.id)
        room_42a = sampledb.logic.locations.create_location("Room 42a", "Building A, Room 42a", building_a.id, instrument_responsible_user.id)
        room_42b = sampledb.logic.locations.create_location("Room 42b", "Building A, Room 42b", building_a.id, instrument_responsible_user.id)
        sampledb.logic.locations.assign_location_to_object(measurement.id, room_42a.id, None, instrument_responsible_user.id, "Temporarily stored on table\n\nSome other text")
        sampledb.logic.locations.assign_location_to_object(measurement.id, room_42b.id, instrument_responsible_user.id, basic_user.id, "Stored in shelf K")
        sampledb.logic.notifications.create_other_notification(instrument_responsible_user.id, "This is a demo.")
        sampledb.logic.object_permissions.set_user_object_permissions(independent_object.id, instrument_responsible_user.id, sampledb.models.Permissions.GRANT)
        sampledb.logic.notifications.create_notification_for_having_received_an_objects_permissions_request(instrument_responsible_user.id, independent_object.id, admin.id)

        for object in sampledb.logic.objects.get_objects():
            sampledb.logic.instrument_log_entries.create_instrument_log_object_attachment(
                instrument_log_entry_id=log_entry.id,
                object_id=object.id
            )
    print("Success: set up demo data")
