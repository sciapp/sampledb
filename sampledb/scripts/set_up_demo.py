# coding: utf-8
"""
Script for setting up demo data in a previously unused SampleDB installation.

Usage: python -m sampledb set_up_demo
"""
import datetime
import json
import os
import sys
import typing


import sampledb
from .. import create_app
from sampledb.models import UserType, ActionType, Language
from sampledb.logic.instruments import create_instrument, add_instrument_responsible_user
from sampledb.logic.instrument_translations import set_instrument_translation
from sampledb.logic.action_translations import set_action_translation
from sampledb.logic.actions import create_action
from ..logic import groups, object_permissions, projects, comments, files


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 0:
        print(__doc__)
        exit(1)
    app = create_app(include_dashboard=False)
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

        # enable german for input
        german = sampledb.logic.languages.get_language(sampledb.models.Language.GERMAN)
        sampledb.logic.languages.update_language(
            language_id=german.id,
            names=german.names,
            lang_code=german.lang_code,
            datetime_format_datetime=german.datetime_format_datetime,
            datetime_format_moment=german.datetime_format_moment,
            datetime_format_moment_output=german.datetime_format_moment_output,
            enabled_for_input=True,
            enabled_for_user_interface=True
        )

        group_id = groups.create_group({"en": "Example Group", "de": "Beispielgruppe"},
                                       {"en": "This is an example group for testing purposes.", "de": "Dies ist eine Beispielgruppe für Testzwecke"},
                                       instrument_responsible_user.id).id

        project_id = projects.create_project({"en": "Example Project", "de": "Beispielprojekt"},
                                             {"en": "This is an example project",
                                              "de": "Dies ist ein Beispielprojekt"}, instrument_responsible_user.id).id

        project_id2 = projects.create_project({"en": "Example Project 2", "de": "Beispielprojekt 2"}, {"en": "This is another example project", "de": "Dies ist ein weiteres Beispielprojekt"},
                                              instrument_responsible_user.id).id
        projects.create_subproject_relationship(parent_project_id=project_id, child_project_id=project_id2,
                                                child_can_add_users_to_parent=True)

        projects.create_project({"en": "A-Example", "de": "A-Beispiel"}, {"en": "", "de": ""}, instrument_responsible_user.id).id
        projects.create_project({"en": "C-Example", "de": "C-Beispiel"}, {"en": "", "de": ""}, instrument_responsible_user.id).id
        project_id5 = projects.create_project({"en": "B-Example", "de": "B-Beispiel"}, {"en": "", "de": ""}, instrument_responsible_user.id).id
        project_id6 = projects.create_project({"en": "2-B-Example", "de": "2-B-Beispiel"}, {"en": "", "de": ""}, instrument_responsible_user.id).id
        project_id7 = projects.create_project({"en": "1-B-Example", "de": "1-B-Beispiel"}, {"en": "", "de": ""}, instrument_responsible_user.id).id
        projects.create_subproject_relationship(parent_project_id=project_id5, child_project_id=project_id6)
        projects.create_subproject_relationship(parent_project_id=project_id5, child_project_id=project_id7)

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
            users_can_create_log_entries=True,
            notes_is_markdown=True
        )
        set_instrument_translation(
            language_id=sampledb.models.Language.ENGLISH,
            instrument_id=instrument.id,
            name="OMBE I",
            description="This is an example instrument",
            short_description="This is the short description",
            notes=markdown_notes,
        )
        set_instrument_translation(
            language_id=sampledb.models.Language.GERMAN,
            instrument_id=instrument.id,
            name="OMBE I",
            description="Dies ist ein Beispiel Instrument",
            short_description="Dies ist die kurze Beschreibung",
            notes=markdown_notes,
        )
        add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
        log_category_error = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument.id,
            title='Error',
            theme=sampledb.models.instrument_log_entries.InstrumentLogCategoryTheme.RED
        )
        log_category_warning = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument.id,
            title='Warning',
            theme=sampledb.models.instrument_log_entries.InstrumentLogCategoryTheme.YELLOW
        )
        log_category_success = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument.id,
            title='Success',
            theme=sampledb.models.instrument_log_entries.InstrumentLogCategoryTheme.GREEN
        )
        log_category_other = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument.id,
            title='Other',
            theme=sampledb.models.instrument_log_entries.InstrumentLogCategoryTheme.BLUE
        )
        log_category_normal = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument.id,
            title='Normal',
            theme=sampledb.models.instrument_log_entries.InstrumentLogCategoryTheme.GRAY
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
            content=open(os.path.join(os.path.dirname(sampledb.__file__), 'static/sampledb/img/ghs01.png'), 'rb').read()
        )
        sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
            instrument_log_entry_id=log_entry.id,
            file_name="ghs02.png",
            content=open(os.path.join(os.path.dirname(sampledb.__file__), 'static/sampledb/img/ghs02.png'), 'rb').read()
        )
        sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
            instrument_log_entry_id=log_entry.id,
            file_name="test.txt",
            content="This is a test".encode('utf-8')
        )

        with open(os.path.join(schema_directory, 'ombe_measurement.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        instrument_action = create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema=schema,
            instrument_id=instrument.id
        )

        set_action_translation(Language.ENGLISH, instrument_action.id, "Sample Creation", "This is an example action")

        sampledb.logic.action_permissions.set_action_permissions_for_all_users(instrument_action.id, sampledb.models.Permissions.READ)
        independent_action = create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema=schema
        )
        set_action_translation(Language.ENGLISH, independent_action.id, "Alternative Process", "This is an example action")

        sampledb.logic.action_permissions.set_action_permissions_for_all_users(independent_action.id, sampledb.models.Permissions.READ)
        with open(os.path.join(schema_directory, 'ombe_measurement_batch.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            batch_schema = json.load(schema_file)
        action = create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema=batch_schema,
            instrument_id=instrument.id
        )
        set_action_translation(Language.ENGLISH, action.id, "Sample Creation (Batch)", "This is an example action")

        sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
        sampledb.db.session.commit()

        with open(os.path.join(objects_directory, 'ombe-1.sampledb.json'), 'r', encoding='utf-8') as data_file:
            data = json.load(data_file)
        instrument_object = sampledb.logic.objects.create_object(data=data, schema=schema, user_id=instrument_responsible_user.id, action_id=instrument_action.id)
        independent_object = sampledb.logic.objects.create_object(data=data, schema=schema, user_id=instrument_responsible_user.id, action_id=independent_action.id)
        comments.create_comment(instrument_object.id, instrument_responsible_user.id, 'This comment is very long. ' * 20 + '\n' + 'This comment has three paragraphs. ' * 20 + '\n' + '\n' + 'This comment has three paragraphs. ' * 20)
        comments.create_comment(instrument_object.id, instrument_responsible_user.id, 'This is another, shorter comment')
        files.create_database_file(instrument_object.id, instrument_responsible_user.id, 'example.txt', lambda stream: typing.cast(None, stream.write("Dies ist ein Test".encode('utf-8'))))
        files.create_database_file(instrument_object.id, instrument_responsible_user.id, 'demo.png', lambda stream: typing.cast(None, stream.write(open(os.path.join(os.path.dirname(sampledb.__file__), 'static/sampledb/img/ghs01.png'), 'rb').read())))
        files.update_file_information(instrument_object.id, 1, instrument_responsible_user.id, 'Example File', 'This is a file description.')
        files.create_url_file(instrument_object.id, instrument_responsible_user.id, 'http://iffsamples.fz-juelich.de/')
        sampledb.logic.publications.link_publication_to_object(instrument_responsible_user.id, instrument_object.id, '10.5281/zenodo.4012175', 'sciapp/sampledb', 'Example')

        projects.link_project_and_object(project_id, instrument_object.object_id, instrument_responsible_user.id)

        object_permissions.set_object_permissions_for_anonymous_users(instrument_object.id, sampledb.models.Permissions.READ)

        with open(os.path.join(schema_directory, 'ombe_measurement_updated.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        sampledb.logic.actions.update_action(
            action_id=instrument_action.id,
            schema=schema
        )
        sampledb.logic.action_translations.set_action_translation(Language.ENGLISH, instrument_action.id, "Updated Sample Creation", "", "")

        object_permissions.set_group_object_permissions(independent_object.object_id, group_id, sampledb.models.Permissions.READ)

        instrument = create_instrument()
        set_instrument_translation(Language.ENGLISH, instrument.id, name="XRR", description="X-Ray Reflectometry")

        add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
        with open(os.path.join(schema_directory, 'xrr_measurement.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        instrument_action = create_action(
            action_type_id=ActionType.MEASUREMENT,
            schema=schema,
            instrument_id=instrument.id
        )
        set_action_translation(Language.ENGLISH, instrument_action.id, "XRR Measurement", "", )

        sampledb.logic.action_permissions.set_action_permissions_for_all_users(instrument_action.id, sampledb.models.Permissions.READ)
        with open(os.path.join(schema_directory, 'searchable_quantity.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        action = create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema=schema
        )
        set_action_translation(Language.ENGLISH, action.id, "Searchable Object", "")

        sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
        independent_object = sampledb.logic.objects.create_object(data={
            "name": {
                "_type": "text",
                "text": {"en": "TEST-1", "de": "TEST-1"}
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
        }, schema=schema, user_id=instrument_responsible_user.id, action_id=action.id)
        object_permissions.set_group_object_permissions(independent_object.object_id, group_id, sampledb.models.Permissions.READ)
        object_permissions.set_user_object_permissions(independent_object.object_id, api_user.id, sampledb.models.Permissions.WRITE)
        independent_object = sampledb.logic.objects.create_object(data={
            "name": {
                "_type": "text",
                "text": {'en': "TEST-2"}
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
        }, schema=schema, user_id=instrument_responsible_user.id, action_id=action.id)
        object_permissions.set_group_object_permissions(independent_object.object_id, group_id, sampledb.models.Permissions.READ)
        sampledb.db.session.commit()

        instrument = create_instrument()
        set_instrument_translation(Language.ENGLISH, instrument.id, name="MPMS SQUID", description="MPMS SQUID Magnetometer JCNS-2")

        add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
        with open(os.path.join(schema_directory, 'squid_measurement.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        instrument_action = create_action(
            action_type_id=ActionType.MEASUREMENT,
            schema=schema,
            instrument_id=instrument.id
        )
        set_action_translation(Language.ENGLISH, instrument_action.id, "Perform Measurement", "")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(instrument_action.id, sampledb.models.Permissions.READ)
        sampledb.db.session.commit()

        instrument = create_instrument()
        set_instrument_translation(Language.ENGLISH, instrument.id, name="Powder Diffractometer", description="Huber Imaging Plate Guinier Camera G670 at JCNS-2")
        add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
        with open(os.path.join(schema_directory, 'powder_diffractometer_measurement.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        instrument_action = create_action(
            action_type_id=ActionType.MEASUREMENT,
            schema=schema,
            instrument_id=instrument.id
        )
        set_action_translation(Language.ENGLISH, instrument_action.id, "Perform Measurement", "")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(instrument_action.id, sampledb.models.Permissions.READ)
        sampledb.db.session.commit()

        instrument = create_instrument()
        set_instrument_translation(Language.ENGLISH, instrument.id, name="GALAXI", description="Gallium Anode Low-Angle X-ray Instrument")
        add_instrument_responsible_user(instrument.id, instrument_responsible_user.id)
        with open(os.path.join(schema_directory, 'galaxi_measurement.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        instrument_action = create_action(
            action_type_id=ActionType.MEASUREMENT,
            schema=schema,
            instrument_id=instrument.id
        )
        set_action_translation(Language.ENGLISH, instrument_action.id, "Perform Measurement", "")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(instrument_action.id, sampledb.models.Permissions.READ)
        sampledb.db.session.commit()

        with open(os.path.join(schema_directory, 'other_sample.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        action = create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema=schema
        )
        set_action_translation(Language.ENGLISH, action.id, "Other Sample", "", )
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
        sampledb.db.session.commit()

        sample_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema={
                'title': 'Example Object',
                'type': 'object',
                'properties': {
                    'name': {
                        'title': {'en': 'Object Name', 'de': 'Objektname'},
                        'type': 'text',
                        'languages': 'all'
                    },
                    'sample': {
                        'title': {'en': 'Sample', 'de': 'Probe'},
                        'type': 'sample'
                    }
                },
                'required': ['name']
            }
        )
        set_action_translation(Language.ENGLISH, sample_action.id, name="sample_action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(sample_action.id, sampledb.models.Permissions.READ)
        measurement_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.MEASUREMENT,
            schema={
                'title': 'Example Object',
                'type': 'object',
                'properties': {
                    'name': {
                        'title': 'Object Name',
                        'type': 'text',
                        'languages': ['en', 'de']
                    },
                    'sample': {
                        'title': 'Sample',
                        'type': 'sample'
                    },
                    'comment': {
                        'title': {'en': 'Comment', 'de': 'Kommentar'},
                        'type': 'text',
                        'markdown': True,
                        'languages': "all"
                    }
                },
                'required': ['name']
            }
        )
        set_action_translation(Language.ENGLISH, measurement_action.id, name="measurement_action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(measurement_action.id, sampledb.models.Permissions.READ)
        data = {
            'name': {
                '_type': 'text',
                'text': {'en': 'Object 1', 'de': 'Objekt 1'}
            }
        }
        object = sampledb.logic.objects.create_object(sample_action.id, data, basic_user.id)
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(object.id, sampledb.models.Permissions.READ)
        data = {
            'name': {
                '_type': 'text',
                'text': {'en': 'Object 2', 'de': 'Objekt 2'}
            },
            'sample': {
                '_type': 'sample',
                'object_id': object.id
            }
        }
        sample = sampledb.logic.objects.create_object(sample_action.id, data, basic_user.id)
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(sample.id, sampledb.models.Permissions.READ)
        data = {
            'name': {
                '_type': 'text',
                'text': {'en': 'Object 1', 'de': 'Objekt 1'}
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
                'text': {"en": 'Measurement', 'de': 'Messung'}
            },
            'sample': {
                '_type': 'sample',
                'object_id': object.id
            },
            'comment': {
                '_type': 'text',
                'text': {'en': 'This is a test.\nThis **is** a *second* line.\n\nThis line follows an empty line.'},
                'is_markdown': True
            }
        }
        measurement = sampledb.logic.objects.create_object(measurement_action.id, data, basic_user.id)
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(measurement.id, sampledb.models.Permissions.READ)
        data = {
            'name': {
                '_type': 'text',
                'text': {'en': 'Measurement 2', 'de': 'Messung 2'}
            },
            'sample': {
                '_type': 'sample',
                'object_id': sample.id
            },
            'comment': {
                '_type': 'text',
                'text': {'en': 'This is a test.\nThis is a second line.\n\nThis line follows an empty line.'}
            }
        }
        measurement = sampledb.logic.objects.create_object(measurement_action.id, data, instrument_responsible_user.id)
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(measurement.id, sampledb.models.Permissions.READ)

        with open(os.path.join(schema_directory, 'plotly.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        plotly_action = create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema=schema,
            instrument_id=instrument.id
        )
        set_action_translation(Language.ENGLISH, plotly_action.id, name="Plotly Example Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(plotly_action.id, sampledb.models.Permissions.READ)

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
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(plotly_object.id, sampledb.models.Permissions.READ)

        with open(os.path.join(schema_directory, 'plotly_array.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        plotly_array_action = create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema=schema
        )
        set_action_translation(Language.ENGLISH, plotly_array_action.id, name="Plotly Array Example Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(plotly_array_action.id, sampledb.models.Permissions.READ)

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
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(plotly_object.id, sampledb.models.Permissions.READ)
        sampledb.db.session.commit()

        campus = sampledb.logic.locations.create_location({"en": "Campus"}, {"en": "Max Mustermann Campus"}, None, instrument_responsible_user.id, type_id=sampledb.models.LocationType.LOCATION)
        building_a = sampledb.logic.locations.create_location({"en": "Building A", "de": "Gebäude A"}, {"en": "Building A on Max Mustermann Campus", "de": "Gebäude A auf dem Max Mustermann Campus"}, campus.id, instrument_responsible_user.id, type_id=sampledb.models.LocationType.LOCATION)
        room_42a = sampledb.logic.locations.create_location({"en": "Room 42a", "de": "Raum 42a"}, {"en": "Building A, Room 42a", "de": "Gebäude A, Raum 42a"}, building_a.id, instrument_responsible_user.id, type_id=sampledb.models.LocationType.LOCATION)
        room_42b = sampledb.logic.locations.create_location({"en": "Room 42b", "de": "Raum 42b"}, {"en": "Building A, Room 42b", "de": "Gebäude A, Raum 42b"}, building_a.id, instrument_responsible_user.id, type_id=sampledb.models.LocationType.LOCATION)
        sampledb.logic.locations.assign_location_to_object(measurement.id, room_42a.id, None, instrument_responsible_user.id, {"en": "Temporarily stored on table\n\nSome other text", "de": "Temporär auf einem Tisch gelagert \n\n Irgendein anderer Text"})
        sampledb.logic.locations.assign_location_to_object(measurement.id, room_42b.id, instrument_responsible_user.id, basic_user.id, {"en": "Stored in shelf K", "de": "In Regal K gelagert"})
        sampledb.logic.notifications.create_other_notification(instrument_responsible_user.id, "This is a demo.")
        sampledb.logic.object_permissions.set_user_object_permissions(independent_object.id, instrument_responsible_user.id, sampledb.models.Permissions.GRANT)
        sampledb.logic.notifications.create_notification_for_having_received_an_objects_permissions_request(instrument_responsible_user.id, independent_object.id, admin.id)
        sampledb.logic.location_permissions.set_location_permissions_for_all_users(campus.id, sampledb.models.Permissions.WRITE)
        sampledb.logic.location_permissions.set_location_permissions_for_all_users(building_a.id, sampledb.models.Permissions.WRITE)
        sampledb.logic.location_permissions.set_location_permissions_for_all_users(room_42a.id, sampledb.models.Permissions.WRITE)
        sampledb.logic.location_permissions.set_location_permissions_for_all_users(room_42b.id, sampledb.models.Permissions.WRITE)
        sampledb.logic.instruments.set_instrument_location(instrument.id, room_42a.id)

        container_type = sampledb.logic.locations.create_location_type(
            name={"en": "Container"},
            location_name_singular={"en": "Container"},
            location_name_plural={"en": "Containers"},
            admin_only=True,
            enable_parent_location=True,
            enable_sub_locations=False,
            enable_object_assignments=True,
            enable_responsible_users=True,
            enable_instruments=False,
            show_location_log=True,
        )
        container = sampledb.logic.locations.create_location(
            name={"en": "Box 1"},
            description={"en": "An example container"},
            parent_location_id=room_42b.id,
            user_id=instrument_responsible_user.id,
            type_id=container_type.id
        )
        sampledb.logic.location_permissions.set_location_permissions_for_all_users(container.id, sampledb.models.Permissions.WRITE)
        sampledb.logic.locations.set_location_responsible_users(container.id, [instrument_responsible_user.id, admin.id])

        for object in sampledb.logic.objects.get_objects():
            sampledb.logic.instrument_log_entries.create_instrument_log_object_attachment(
                instrument_log_entry_id=log_entry.id,
                object_id=object.id
            )
        action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema={
                'title': 'Example Object',
                'type': 'object',
                'properties': {
                    'name': {
                        'title': 'Object Name',
                        'type': 'text',
                        'languages': ['en', 'de']
                    },
                    'dropdown': {
                        'title': {'en': 'English Title', 'de': 'Deutscher Titel'},
                        'type': 'text',
                        'choices': [
                            {'en': 'en 1', 'de': 'de 1'},
                            {'en': 'en 2', 'de': 'de 2'},
                            {'en': 'en 3'}
                        ],
                        'default': {'en': 'en 2', 'de': 'de 2'},
                        'note': 'Select option 1.'
                    },
                    'user': {
                        'title': {'en': 'User', 'de': 'Nutzer'},
                        'type': 'user',
                        'note': 'Do not select a user.'
                    },
                    'checkbox': {
                        'title': {'en': 'Checkbox', 'de': 'Checkbox'},
                        'type': 'bool',
                        'note': 'Check this checkbox.'
                    },
                    'object': {
                        'title': {'en': 'Object', 'de': 'Objekt'},
                        'type': 'object_reference',
                        'note': 'Select object #1.',
                        'action_type_id': [-99, -98],
                        'action_id': [1, 3]
                    },
                    'conditional_text': {
                        'title': 'Conditional Name',
                        'type': 'text',
                        'markdown': True,
                        'conditions': [
                            {
                                'type': 'choice_equals',
                                'property_name': 'dropdown',
                                'choice': {'en': 'en 1', 'de': 'de 1'}
                            },
                            {
                                'type': 'user_equals',
                                'property_name': 'user',
                                'user_id': None
                            },
                            {
                                'type': 'bool_equals',
                                'property_name': 'checkbox',
                                'value': True
                            },
                            {
                                'type': 'object_equals',
                                'property_name': 'object',
                                'object_id': 1
                            }
                        ]
                    }
                },
                'required': ['name']
            }
        )
        set_action_translation(Language.ENGLISH, action.id, name="Conditions Demo Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)

        UUID = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
        component = sampledb.logic.components.add_component(UUID, 'Example SampleDB', None, 'Example component database for demonstration purposes. Do not expect it to function.')
        sampledb.logic.federation.locations.parse_import_location({
            'location_id': 1,
            'component_uuid': UUID,
            'name': {'en': 'Collaborating Institute', 'de': 'Partnerinstitut'},
            'description': {'en': 'A collaborating partner’s site.',
                            'de': 'Gelände eines Kooperationspartners.'},
        }, component)
        sampledb.logic.federation.locations.parse_import_location({
            'location_id': 2,
            'component_uuid': UUID,
            'name': {'en': 'Room 123', 'de': 'Raum 123'},
            'description': {'en': 'Room 123 on a collaborating partner’s site.',
                            'de': 'Raum 123 auf dem Gelände eines Kooperationspartners'},
            'parent_location': {'location_id': 1, 'component_uuid': UUID}
        }, component)
        sampledb.logic.federation.users.parse_import_user({
            'user_id': 1,
            'component_uuid': UUID,
            'name': 'Partnering User',
            'email': 'partner@example.com',
            'affiliation': 'Collaborating Partner LLC',
        }, component)
        sampledb.logic.federation.users.parse_import_user({
            'user_id': 2,
            'component_uuid': UUID,
            'name': None,
            'email': None,
            'affiliation': 'Collaborating Partner LLC',
        }, component)
        sampledb.logic.federation.instruments.parse_import_instrument({
            'instrument_id': 1,
            'component_uuid': UUID,
            'description_is_markdown': False,
            'short_description_is_markdown': False,
            'notes_is_markdown': False,
            'is_hidden': False,
            'translations': {'en': {'name': 'Collaborating Partner’s Measurement Instrument',
                                    'description': '',
                                    'short_description': '',
                                    'notes': ''},
                             'de': {'name': 'Messinstrument des Kooperationspartner',
                                    'description': '',
                                    'short_description': '',
                                    'notes': ''}}
        }, component)
        sampledb.logic.federation.action_types.parse_import_action_type({
            'action_type_id': ActionType.SAMPLE_CREATION,
            'component_uuid': UUID,
            'admin_only': False,
            'enable_labels': True,
            'enable_files': True,
            'enable_locations': True,
            'enable_publications': True,
            'enable_comments': True,
            'enable_activity_log': True,
            'enable_related_objects': True,
            'enable_project_link': True,
            'translations': {'en': {'name': 'Sample Creation',
                                    'description': 'These Actions represent processes which create a sample.',
                                    'object_name': 'Sample',
                                    'object_name_plural': 'Samples',
                                    'view_text': 'View Samples',
                                    'perform_text': 'Create Sample'},
                             'de': {'name': 'Probenerstellung',
                                    'description': 'Diese Aktionen repräsentieren Prozesse, die Proben erstellen.',
                                    'object_name': 'Probe',
                                    'object_name_plural': 'Proben',
                                    'view_text': 'Proben anzeigen',
                                    'perform_text': 'Probe erstellen'}}
        }, component)
        sampledb.logic.federation.actions.parse_import_action({
            'action_id': 1,
            'component_uuid': UUID,
            'action_type': {'action_type_id': ActionType.SAMPLE_CREATION, 'component_uuid': UUID},
            'description_is_markdown': False,
            'short_description_is_markdown': False,
            'instrument': None,
            'schema': {'title': 'Sampling', 'type': 'object', 'properties': {'name': {'title': 'Additional Note', 'type': 'text'}}, 'required': ['name']},
            'translations': {'en': {'name': 'Sampling',
                                    'description': 'Sample creation.',
                                    'short_description': 'Sample creation.'},
                             'de': {'name': 'Probenentnahme',
                                    'description': 'Probenentnahmeverfahren.',
                                    'short_description': 'Probenentnahmeverfahren.'}}
        }, component)
        sampledb.logic.federation.actions.parse_import_action({
            'action_id': 2,
            'component_uuid': UUID,
            'action_type': {'action_type_id': ActionType.MEASUREMENT, 'component_uuid': UUID},
            'description_is_markdown': False,
            'short_description_is_markdown': False,
            'instrument': {'instrument_id': 1, 'component_uuid': UUID},
            'schema': {'title': 'Special Measurement', 'type': 'object', 'properties': {'name': {'title': 'Additional Note', 'type': 'text'}, 'sample1': {'title': 'Sample 1', 'type': 'sample'}, 'sample2': {'title': 'Sample 2', 'type': 'sample'}}, 'required': ['name']},
            'translations': {'en': {'name': 'Special Measurement',
                                    'description': 'A special measurement only performed at the collaborating partner.',
                                    'short_description': 'A special measurement only performed at the collaborating partner.'},
                             'de': {'name': 'Spezielle Messung',
                                    'description': 'Eine spezielle Messung, die nur beim Kooperationspartner ausgeführt werden kann.',
                                    'short_description': 'Eine spezielle Messung, die nur beim Kooperationspartner ausgeführt werden kann.'}}
        }, component)
        sampledb.logic.federation.objects.parse_import_object({
            'object_id': 1,
            'versions': [{
                'version_id': 0,
                'data': {'name': {'_type': 'text', 'text': 'Shared Sample'}},
                'schema': {'title': 'Sampling', 'type': 'object', 'properties': {'name': {'title': 'Additional Note', 'type': 'text'}}, 'required': ['name']},
                'user': {'user_id': 2, 'component_uuid': UUID},
                'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
            }],
            'action': {'action_id': 1, 'component_uuid': UUID},
            'policy': {
                'access': {'data': True, 'files': True, 'action': True, 'comments': True, 'user_ids': True, 'user_data': True, 'object_location_assignments': True},
                'permissions': {'users': {basic_user.id: 'read'}, 'groups': {group_id: 'read'}, 'projects': {project_id: 'read'}}
            }
        }, component)
        sampledb.logic.federation.objects.parse_import_object({
            'object_id': 2,
            'versions': [{
                'version_id': 0,
                'data': {'name': {'_type': 'text', 'text': 'Shared Measurement'}, 'sample1': {'_type': 'sample', 'object_id': 1, 'component_uuid': UUID}, 'sample2': {'_type': 'sample', 'object_id': 3, 'component_uuid': UUID, 'export_edit_note': 'This internal sample was not exported.'}},
                'schema': {'title': 'Special Measurement', 'type': 'object', 'properties': {'name': {'title': 'Additional Note', 'type': 'text'}, 'sample1': {'title': 'Sample 1', 'type': 'sample'}, 'sample2': {'title': 'Sample 2', 'type': 'sample'}}, 'required': ['name']},
                'user': {'user_id': 1, 'component_uuid': UUID},
                'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
            }],
            'action': {'action_id': 1, 'component_uuid': UUID},
            'policy': {
                'access': {'data': True, 'files': True, 'action': True, 'comments': True, 'user_ids': True, 'user_data': True, 'object_location_assignments': True},
                'permissions': {'users': {basic_user.id: 'read'}, 'groups': {group_id: 'read'}, 'projects': {project_id: 'read'}}
            },
            'sharing_user': {
                'user_id': 1,
                'component_uuid': UUID
            },
            'comments': [
                {
                    'comment_id': 1,
                    'component_uuid': UUID,
                    'user': {'user_id': 1, 'component_uuid': UUID},
                    'content': 'I want to comment here.',
                    'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                },
                {
                    'comment_id': 2,
                    'component_uuid': UUID,
                    'user': None,
                    'content': 'Another important comment by an anonymous user.',
                    'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                },
                {
                    'comment_id': 3,
                    'component_uuid': UUID,
                    'user': {'user_id': 4, 'component_uuid': UUID},
                    'content': 'You might be interested in my specific comment regarding this object.',
                    'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                }
            ],
            'object_location_assignments': [
                {
                    'id': 1,
                    'component_uuid': UUID,
                    'user': {'user_id': 1, 'component_uuid': UUID},
                    'responsible_user': {'user_id': 1, 'component_uuid': UUID},
                    'location': {'location_id': 1, 'component_uuid': UUID},
                    'description': {'en': ''},
                    'confirmed': True,
                    'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                },
                {
                    'id': 2,
                    'component_uuid': UUID,
                    'user': {'user_id': 1, 'component_uuid': UUID},
                    'responsible_user': {'user_id': 3, 'component_uuid': UUID},
                    'location': {'location_id': 2, 'component_uuid': UUID},
                    'description': {'en': ''},
                    'confirmed': False,
                    'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                }
            ],
            'files': [
                {
                    'file_id': 1,
                    'component_uuid': UUID,
                    'user': {'user_id': 3, 'component_uuid': UUID},
                    'data': {"storage": "url", "url": "https://example.com/file"},
                    'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
                }
            ]
        }, component)
        sampledb.logic.federation.objects.parse_import_object({
            'object_id': 3,
            'versions': [{
                'version_id': 0,
                'data': {'name': {'_type': 'text', 'text': 'Shared Object Without Shared Action'}},
                'schema': {'title': 'Sampling', 'type': 'object',
                           'properties': {'name': {'title': 'Additional Note', 'type': 'text'}}, 'required': ['name']},
                'user': {'user_id': 2, 'component_uuid': UUID},
                'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
            }],
            'action': {'action_id': 3, 'component_uuid': UUID},
            'policy': {
                'access': {'data': True, 'files': True, 'action': True, 'comments': True, 'user_ids': True,
                           'user_data': True, 'object_location_assignments': True},
                'permissions': {'users': {basic_user.id: 'read'}, 'groups': {group_id: 'read'},
                                'projects': {project_id: 'read'}}
            }
        }, component)

        institute_category = sampledb.logic.group_categories.create_group_category(
            name={
                'de': 'Demo-Institut',
                'en': 'Demo Institute'
            }
        )

        lab_category = sampledb.logic.group_categories.create_group_category(
            name={
                'de': 'Demo-Labor',
                'en': 'Demo Laboratory'
            },
            parent_category_id=institute_category.id
        )
        sampledb.logic.group_categories.set_project_group_categories(project_id, [institute_category.id, lab_category.id])
        sampledb.logic.group_categories.set_project_group_categories(project_id2, [lab_category.id])
        sampledb.logic.group_categories.set_basic_group_categories(group_id, [institute_category.id])

        multi_measurement_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.MEASUREMENT,
            schema={
                'title': 'Example Object',
                'type': 'object',
                'properties': {
                    'name': {
                        'title': 'Object Name',
                        'type': 'text',
                        'languages': ['en', 'de']
                    },
                    'samples': {
                        'title': 'Samples',
                        'type': 'array',
                        'style': 'list',
                        'items': {
                            'title': 'Sample',
                            'type': 'sample'
                        }
                    },
                    'comment': {
                        'title': {'en': 'Comment', 'de': 'Kommentar'},
                        'type': 'text',
                        'markdown': True,
                        'languages': "all"
                    }
                },
                'required': ['name']
            }
        )
        set_action_translation(Language.ENGLISH, multi_measurement_action.id, name="multi measurement_action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(multi_measurement_action.id, sampledb.models.Permissions.READ)

        sampledb.logic.shares.add_object_share(
            object_id=measurement.id,
            component_id=component.id,
            policy={
                'access': {},
                'permissions': {
                    'users': {}
                }
            },
            user_id=basic_user.id
        )
        sampledb.logic.shares.update_object_share(
            object_id=measurement.id,
            component_id=component.id,
            policy={
                'access': {},
                'permissions': {
                    'users': {1: 'read'},
                    'groups': {2: 'write'},
                    'projects': {3: 'grant'}
                }
            },
            user_id=instrument_responsible_user.id
        )
        sampledb.logic.shares.set_object_share_import_status(
            object_id=measurement.id,
            component_id=component.id,
            import_status={
                'success': False,
                'notes': ['Demo import error'],
                'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'object_id': None
            }
        )
        sampledb.logic.shares.set_object_share_import_status(
            object_id=measurement.id,
            component_id=component.id,
            import_status={
                'success': True,
                'notes': ['Demo import note'],
                'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'object_id': 14
            }
        )
        sampledb.logic.shares.set_object_share_import_status(
            object_id=measurement.id,
            component_id=component.id,
            import_status={
                'success': True,
                'notes': [],
                'utc_datetime': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'object_id': 14
            }
        )

    print("Success: set up demo data", flush=True)
