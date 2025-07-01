# coding: utf-8
"""
Script for setting up demo data in a previously unused SampleDB installation.

Usage: sampledb set_up_demo
"""
import datetime
import io
import json
import os
import string
import sys
import random
import typing

from PIL import Image

import sampledb
from .. import create_app
from ..models import UserType, ActionType, Language
from ..logic.instruments import create_instrument, add_instrument_responsible_user
from ..logic.instrument_translations import set_instrument_translation
from ..logic.action_translations import set_action_translation
from ..logic.actions import create_action
from ..logic import groups, object_permissions, projects, comments, files


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 0:
        print(__doc__)
        sys.exit(1)
    app = create_app(include_dashboard=False)
    if not app.config.get("SERVER_NAME"):
        app.config["SERVER_NAME"] = "localhost:8000"
    with app.app_context():
        if sampledb.logic.actions.get_actions() or sampledb.logic.instruments.get_instruments() or len(sampledb.logic.users.get_users()) > 1:
            print("Error: database must be empty for demo", file=sys.stderr)
            sys.exit(1)

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
            date_format_moment_output=german.date_format_moment_output,
            enabled_for_input=True,
            enabled_for_user_interface=True
        )

        topic = sampledb.logic.topics.create_topic(
            name={
                "en": "Example Topic",
                "de": "Beispielthema"
            },
            description={
                "en": "This is an example topic.",
                "de": "Dies ist ein Beispielthema."
            },
            short_description={
                "en": "This is an example topic.",
                "de": "Dies ist ein Beispielthema."
            },
            show_on_frontpage=False,
            show_in_navbar=True,
            description_is_markdown=False,
            short_description_is_markdown=False
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

        projects.create_project({"en": "A-Example", "de": "A-Beispiel"}, {"en": "", "de": ""}, instrument_responsible_user.id)
        projects.create_project({"en": "C-Example", "de": "C-Beispiel"}, {"en": "", "de": ""}, instrument_responsible_user.id)
        project_id5 = projects.create_project({"en": "B-Example", "de": "B-Beispiel"}, {"en": "", "de": ""}, instrument_responsible_user.id).id
        project_id6 = projects.create_project({"en": "2-B-Example", "de": "2-B-Beispiel"}, {"en": "", "de": ""}, instrument_responsible_user.id).id
        project_id7 = projects.create_project({"en": "1-B-Example", "de": "1-B-Beispiel"}, {"en": "", "de": ""}, instrument_responsible_user.id).id
        projects.create_subproject_relationship(parent_project_id=project_id5, child_project_id=project_id6)
        projects.create_subproject_relationship(parent_project_id=project_id5, child_project_id=project_id7)
        projects.add_user_to_project(project_id5, admin.id, sampledb.models.Permissions.READ)

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
        sampledb.logic.topics.set_instrument_topics(instrument.id, [topic.id])
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
        with open(os.path.join(os.path.dirname(sampledb.__file__), 'static/sampledb/img/ghs01.png'), 'rb') as ghs01_file:
            ghs01_image = ghs01_file.read()
        sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
            instrument_log_entry_id=log_entry.id,
            file_name="ghs01.png",
            content=ghs01_image
        )
        with open(os.path.join(os.path.dirname(sampledb.__file__), 'static/sampledb/img/ghs02.png'), 'rb') as ghs02_file:
            ghs02_image = ghs02_file.read()
        sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
            instrument_log_entry_id=log_entry.id,
            file_name="ghs02.png",
            content=ghs02_image
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
        sampledb.logic.topics.set_action_topics(instrument_action.id, [topic.id])

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
        files.create_database_file(instrument_object.id, instrument_responsible_user.id, 'demo.png', lambda stream: typing.cast(None, stream.write(ghs01_image)))
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

        with open(os.path.join(schema_directory, 'calculation.sampledb.json'), 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        action = create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema=schema
        )
        set_action_translation(Language.ENGLISH, action.id, "Calculation Demo Action", "", )
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
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

        sample_schema: typing.Dict[str, typing.Any] = {
            'title': 'Sample Information',
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
        sample_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema=sample_schema
        )
        sample_schema['workflow_views'] = [
            {
                'title': {'en': 'Referencing Measurements (sorted by property "datetime")'},
                'referencing_action_type_id': -98,
                'referenced_action_id': [],
                'sorting_properties': ['datetime']
            },
            {
                'title': {'en': 'Referencing Measurements (recursion)'},
                'referencing_action_type_id': [ActionType.MEASUREMENT, ActionType.SAMPLE_CREATION],
                'referenced_action_id': [],
                'sorting_properties': ['datetime'],
                'recursion_filters': {
                    'referenced_action_id': sample_action.id,
                    'referenced_action_type_id': ActionType.MEASUREMENT,
                    'referenced_filter_operator': 'or',
                    'referencing_action_id': sample_action.id,
                    'referencing_action_type_id': ActionType.MEASUREMENT,
                    'referencing_filter_operator': 'and',
                    'max_depth': 2,
                }
            },
            {
                'title': {'en': f'Referenced Samples from Action #{sample_action.id}'},
                'referenced_action_id': sample_action.id,
                'referencing_action_id': [],
                'show_action_info': False,
            },
            {
                'title': {'en': 'All Related Objects'}
            }
        ]
        sampledb.logic.actions.update_action(action_id=sample_action.id, schema=sample_schema)
        set_action_translation(Language.ENGLISH, sample_action.id, name="sample_action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(sample_action.id, sampledb.models.Permissions.READ)
        measurement_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.MEASUREMENT,
            schema={
                'title': 'Measurement Information',
                'type': 'object',
                'properties': {
                    'name': {
                        'title': 'Object Name',
                        'type': 'text',
                        'languages': ['en', 'de']
                    },
                    'datetime': {
                        'title': 'Measurement Date/Time',
                        'type': 'datetime'
                    },
                    'sample': {
                        'title': 'Sample',
                        'type': 'sample',
                        'style': 'include'
                    },
                    'comment': {
                        'title': {'en': 'Comment', 'de': 'Kommentar'},
                        'type': 'text',
                        'markdown': True,
                        'languages': "all"
                    },
                    "tags": {
                        "title": {"en": "Tags", "de": "Tags"},
                        "type": "tags"
                    }
                },
                'required': ['name', 'tags'],
                'workflow_show_more': ['sample', 'comment']
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
            'datetime': {
                '_type': 'datetime',
                'utc_datetime': datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            },
            'sample': {
                '_type': 'sample',
                'object_id': instrument_object.id
            },
            'comment': {
                '_type': 'text',
                'text': {'en': 'This is a test.\nThis **is** a *second* line.\n\nThis line follows an empty line.'},
                'is_markdown': True
            },
            'tags': {
                '_type': 'tags',
                'tags': ['example_tag', 'other_tag', 'tag3']
            }
        }
        measurement = sampledb.logic.objects.create_object(measurement_action.id, data, basic_user.id)
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(measurement.id, sampledb.models.Permissions.READ)
        data = {
            'name': {
                '_type': 'text',
                'text': {'en': 'Measurement 2', 'de': 'Messung 2'}
            },
            'datetime': {
                '_type': 'datetime',
                'utc_datetime': datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            },
            'sample': {
                '_type': 'sample',
                'object_id': sample.id
            },
            'comment': {
                '_type': 'text',
                'text': {'en': 'This is a test.\nThis is a second line.\n\nThis line follows an empty line.'}
            },
            'tags': {
                '_type': 'tags',
                'tags': []
            }
        }
        measurement = sampledb.logic.objects.create_object(measurement_action.id, data, instrument_responsible_user.id)
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(measurement.id, sampledb.models.Permissions.READ)
        data = {
            'name': {
                '_type': 'text',
                'text': {'en': 'Measurement 3', 'de': 'Messung 3'}
            },
            'datetime': {
                '_type': 'datetime',
                'utc_datetime': (datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            },
            'sample': {
                '_type': 'sample',
                'object_id': sample.id
            },
            'comment': {
                '_type': 'text',
                'text': {'en': 'This is a test.\nThis is a second line.\n\nThis line follows an empty line.'}
            },
            'tags': {
                '_type': 'tags',
                'tags': []
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
        sampledb.logic.topics.set_location_topics(room_42a.id, [topic.id])

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
            enable_capacities=True,
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
        sampledb.logic.locations.set_location_capacity(container.id, sampledb.models.ActionType.SAMPLE_CREATION, 2)

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
        user_reference_object = sampledb.logic.objects.create_object(
            action_id=action.id,
            data={
                'name': {
                    '_type': 'text',
                    'text': 'Object with a User Reference'
                },
                'user': {
                    '_type': 'user',
                    'user_id': basic_user.id
                }
            },
            user_id=instrument_responsible_user.id
        )

        UUID = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
        component = sampledb.logic.components.add_component(UUID, 'Example SampleDB', None, 'Example component database for demonstration purposes. Do not expect it to function.')
        sampledb.logic.federation.components.parse_import_component_info({
            'uuid': 'e50671c5-2b31-4251-a24b-5b39bb6aa6e6',
            'source_uuid': UUID,
            'distance': 1,
            'name': None,
            'address': None,
            'discoverable': True
        }, component)
        sampledb.logic.federation.components.parse_import_component_info({
            'uuid': '9b9c5c43-4a7a-4a71-acc8-e75e706feaac',
            'source_uuid': UUID,
            'distance': 1,
            'name': 'Other SampleDB',
            'address': 'http://example.org',
            'discoverable': True
        }, component)
        sampledb.logic.federation.components.parse_import_component_info({
            'uuid': 'e50671c5-2b31-4251-a24b-5b39bb6aa6e6',
            'source_uuid': '9b9c5c43-4a7a-4a71-acc8-e75e706feaac',
            'distance': 2,
            'name': None,
            'address': None,
            'discoverable': True
        }, component)
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
            'enable_project_link': False,
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
                'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
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
                'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
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
                    'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
                },
                {
                    'comment_id': 2,
                    'component_uuid': UUID,
                    'user': None,
                    'content': 'Another important comment by an anonymous user.',
                    'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
                },
                {
                    'comment_id': 3,
                    'component_uuid': UUID,
                    'user': {'user_id': 4, 'component_uuid': UUID},
                    'content': 'You might be interested in my specific comment regarding this object.',
                    'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
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
                    'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
                },
                {
                    'id': 2,
                    'component_uuid': UUID,
                    'user': {'user_id': 1, 'component_uuid': UUID},
                    'responsible_user': {'user_id': 3, 'component_uuid': UUID},
                    'location': {'location_id': 2, 'component_uuid': UUID},
                    'description': {'en': ''},
                    'confirmed': False,
                    'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
                }
            ],
            'files': [
                {
                    'file_id': 1,
                    'component_uuid': UUID,
                    'user': {'user_id': 3, 'component_uuid': UUID},
                    'data': {"storage": "url", "url": "https://example.com/file"},
                    'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
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
                'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
            }],
            'action': {'action_id': 3, 'component_uuid': UUID},
            'policy': {
                'access': {'data': True, 'files': True, 'action': True, 'comments': True, 'user_ids': True,
                           'user_data': True, 'object_location_assignments': True},
                'permissions': {'users': {basic_user.id: 'read'}, 'groups': {group_id: 'read'},
                                'projects': {project_id: 'read'}}
            }
        }, component)
        sampledb.logic.federation.objects.parse_import_object({
            'object_id': 4,
            'versions': [{
                'version_id': 0,
                'data': {'name': {'_type': 'text', 'text': 'Shared Object with File References'}, 'file_a': {'_type': 'file', 'file_id': 1, 'component_uuid': component.uuid}, 'file_b': {'_type': 'file', 'file_id': 2, 'component_uuid': component.uuid}},
                'schema': {'title': 'Object Information', 'type': 'object', 'properties': {'name': {'title': 'Name', 'type': 'text'}, 'file_a': {'title': 'File A', 'type': 'file'}, 'file_b': {'title': 'File B', 'type': 'file'}}, 'required': ['name']},
                'user': {'user_id': 1, 'component_uuid': UUID},
                'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
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
            'comments': [],
            'object_location_assignments': [],
            'files': [
                {
                    'file_id': 1,
                    'component_uuid': UUID,
                    'user': {'user_id': 1, 'component_uuid': UUID},
                    'data': {"storage": "federation", "original_file_name": "example.txt"},
                    'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
                }
            ]
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
                'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                'object_id': None
            }
        )
        sampledb.logic.shares.set_object_share_import_status(
            object_id=measurement.id,
            component_id=component.id,
            import_status={
                'success': True,
                'notes': ['Demo import note'],
                'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                'object_id': 14
            }
        )
        sampledb.logic.shares.set_object_share_import_status(
            object_id=measurement.id,
            component_id=component.id,
            import_status={
                'success': True,
                'notes': [],
                'utc_datetime': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                'object_id': 14
            }
        )
        timeseries_action = sampledb.logic.actions.create_action(
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
                    'temperature_series': {
                        'title': 'Temperature Series',
                        'type': 'timeseries',
                        'units': ['degC', 'K'], 'display_digits': 2
                    },
                    'pressure_series': {
                        'title': 'Pressure Series',
                        'type': 'timeseries',
                        'units': 'bar',
                        'display_digits': 2,
                        'statistics': ['first', 'last', 'count']
                    }
                },
                'required': ['name']
            }
        )
        set_action_translation(Language.ENGLISH, timeseries_action.id, name="Timeseries Demo Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(timeseries_action.id, sampledb.models.Permissions.READ)
        temperature_data: typing.List[typing.Tuple[str, float, float]] = []
        pressure_data: typing.List[typing.Tuple[str, float]] = []
        random.seed(0)
        for i in range(1000):
            utc_datetime_string = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(milliseconds=i * 30)).strftime('%Y-%m-%d %H:%M:%S.%f')
            if i == 0:
                temperature_magnitude = 20.0
            else:
                temperature_magnitude = temperature_data[-1][1] + random.uniform(-1, 1)
            temperature_magnitude_in_base_units = temperature_magnitude + 273.15
            temperature_data.append((
                utc_datetime_string,
                temperature_magnitude,
                temperature_magnitude_in_base_units
            ))
            if i == 0:
                pressure_magnitude = 2.0
            else:
                pressure_magnitude = pressure_data[-1][1] + random.uniform(-0.1, 0.1)
            pressure_data.append((
                utc_datetime_string,
                pressure_magnitude
            ))
        data = {
            'name': {
                '_type': 'text',
                'text': {'en': 'Timeseries Demo 1', 'de': 'Timeseries Demo 1'}
            },
            'temperature_series': {
                '_type': 'timeseries',
                'units': 'degC',
                'data': temperature_data
            },
            'pressure_series': {
                '_type': 'timeseries',
                'units': 'bar',
                'data': pressure_data
            }
        }
        sampledb.logic.objects.create_object(timeseries_action.id, data, instrument_responsible_user.id)

        relative_temperature_data: typing.List[typing.Tuple[float, float, float]] = [(i * 0.03, data[1], data[2]) for i, data in enumerate(temperature_data)]
        relative_pressure_data: typing.List[typing.Tuple[float, float]] = [(i * 0.03, data[1]) for i, data in enumerate(pressure_data)]
        data = {
            'name': {
                '_type': 'text',
                'text': {'en': 'Relative Timeseries Demo', 'de': 'Relative Timeseries Demo'}
            },
            'temperature_series': {
                '_type': 'timeseries',
                'units': 'degC',
                'data': relative_temperature_data
            },
            'pressure_series': {
                '_type': 'timeseries',
                'units': 'bar',
                'data': relative_pressure_data
            }
        }
        sampledb.logic.objects.create_object(timeseries_action.id, data, instrument_responsible_user.id)

        combined_conditions_action = sampledb.logic.actions.create_action(
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
                    'choice': {
                        'title': 'Choice',
                        'type': 'text',
                        'choices': ['A', 'B']
                    },
                    'checkbox_a': {
                        'title': 'Checkbox A',
                        'type': 'bool',
                        'conditions': [
                            {
                                'type': 'choice_equals',
                                'property_name': 'choice',
                                'choice': 'A'
                            }
                        ]
                    },
                    'checkbox_b': {
                        'title': 'Checkbox B',
                        'type': 'bool',
                        'conditions': [
                            {
                                'type': 'choice_equals',
                                'property_name': 'choice',
                                'choice': 'B'
                            }
                        ]
                    },
                    'text_a': {
                        'title': 'Text A',
                        'type': 'text',
                        'conditions': [
                            {
                                'type': 'bool_equals',
                                'property_name': 'checkbox_a',
                                'value': True
                            }
                        ]
                    },
                    'text_b': {
                        'title': 'Text B',
                        'type': 'text',
                        'conditions': [
                            {
                                'type': 'bool_equals',
                                'property_name': 'checkbox_b',
                                'value': True
                            }
                        ]
                    }
                },
                'required': ['name']
            }
        )
        set_action_translation(Language.ENGLISH, combined_conditions_action.id, name="Combined Conditions Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(combined_conditions_action.id, sampledb.models.Permissions.READ)

        file_action = sampledb.logic.actions.create_action(
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
                    'file': {
                        'title': 'Example File',
                        'type': 'file',
                        'extensions': ['.txt', '.png'],
                        'preview': True
                    },
                    'list': {
                        'title': 'File List',
                        'type': 'array',
                        'style': 'list',
                        'items': {
                            'title': 'Example File',
                            'type': 'file',
                            'extensions': ['.txt', '.png']
                        }
                    },
                    'table': {
                        'title': 'File Table',
                        'type': 'array',
                        'style': 'table',
                        'items': {
                            'title': 'Example Object',
                            'type': 'object',
                            'properties': {
                                'file': {
                                    'title': 'Example File',
                                    'type': 'file',
                                    'extensions': ['.txt', '.png'],
                                    'preview': True
                                }
                            },
                            'required': ['file']
                        }
                    }
                },
                'required': ['name'],
                'propertyOrder': ['name', 'file', 'list', 'table'],
                'displayProperties': ['file']
            }
        )
        set_action_translation(Language.ENGLISH, file_action.id, name="File Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(file_action.id, sampledb.models.Permissions.READ)

        file_object = sampledb.logic.objects.create_object(
            action_id=file_action.id,
            data={
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'File Demo Object',
                        'de': 'Datei-Demo-Objekt',
                    }
                },
                'list': [],
                'table': []
            },
            user_id=basic_user.id
        )
        file = sampledb.logic.files.create_database_file(
            object_id=file_object.id,
            user_id=basic_user.id,
            file_name='example.png',
            save_content=lambda f: typing.cast(None, f.write(ghs01_image))
        )
        preview_image: Image.Image = Image.open(io.BytesIO(ghs01_image), formats=['PNG'])
        preview_image = preview_image.resize((10, 10), Image.Resampling.LANCZOS).resize((100, 100), Image.Resampling.NEAREST)
        preview_image_file = io.BytesIO()
        preview_image.save(preview_image_file, format='PNG')
        preview_image_file.seek(0)
        preview_image_binary_data = preview_image_file.read()
        sampledb.logic.files.create_database_file(
            object_id=file_object.id,
            user_id=basic_user.id,
            file_name='example.txt',
            save_content=lambda f: typing.cast(None, f.write(b'Dies ist ein Test')),
            preview_image_binary_data=preview_image_binary_data,
            preview_image_mime_type='image/png'
        )
        sampledb.logic.objects.update_object(
            object_id=file_object.id,
            data={
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'File Demo Object',
                        'de': 'Datei-Demo-Objekt',
                    }
                },
                'file': {
                    '_type': 'file',
                    'file_id': file.id
                },
                'list': [],
                'table': []
            },
            user_id=basic_user.id
        )
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(file_object.id, sampledb.models.Permissions.READ)

        sampledb.logic.comments.create_comment(
            object_id=independent_object.id,
            user_id=basic_user.id,
            content='This is a test comment',
            utc_datetime=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2),
        )
        sampledb.logic.files.create_url_file(
            object_id=independent_object.id,
            user_id=basic_user.id,
            url='http://example.org/test_url'
        )
        sampledb.logic.files.create_database_file(
            object_id=independent_object.id,
            user_id=basic_user.id,
            file_name='test_database.txt',
            save_content=lambda f: typing.cast(None, f.write(b"Test"))
        )
        eln_file_data = sampledb.logic.export.get_eln_archive(
            user_id=instrument_responsible_user.id,
            object_ids=[independent_object.id, file_object.id, measurement.id, user_reference_object.id]
        )
        eln_import_id = sampledb.logic.eln_import.create_eln_import(
            user_id=instrument_responsible_user.id,
            file_name='sampledb_demo_file.eln',
            zip_bytes=eln_file_data
        ).id
        sampledb.logic.eln_import.import_eln_file(eln_import_id)

        data = {
            'name': {
                '_type': 'text',
                'text': {
                    'en': 'Imported Object Reference Demo'
                }
            },
            'samples': [
                {
                    '_type': 'sample',
                    'object_id': 10001,
                    'component_uuid': 'ee36dd7f-72b0-44b6-afa8-752e920fbb32'
                },
                {
                    '_type': 'sample',
                    'object_id': 10001,
                    'eln_source_url': 'http://localhost:5000/',
                    'eln_object_url': 'http://localhost:5000/objects/10001'
                }
            ]
        }
        object = sampledb.logic.objects.create_object(multi_measurement_action.id, data, instrument_responsible_user.id)
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(object.id, sampledb.models.Permissions.READ)

        choice_array_action = sampledb.logic.actions.create_action(
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
                    'choice_array': {
                        'title': 'Choice Array',
                        'type': 'array',
                        'style': 'choice',
                        'items': {
                            'title': 'Choice Item',
                            'type': 'text',
                            'choices': [{'en': 'A'}, {'en': 'B'}, {'en': 'C'}, {'en': 'D (en)', 'de': 'D (de)'}]
                        }
                    }
                },
                'required': ['name'],
                'propertyOrder': ['name', 'choice_array']
            }
        )
        set_action_translation(Language.ENGLISH, choice_array_action.id, name="Choice Array Demo Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(choice_array_action.id, sampledb.models.Permissions.READ)

        timeline_array_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema={
                "title": "Example Object",
                "type": "object",
                "properties": {
                    "name": {
                        "title": "Object Name",
                        "type": "text"
                    },
                    "timeline_array": {
                        "title": "Timeline Array",
                        "type": "array",
                        "style": "timeline",
                        "items": {
                            "title": "Event",
                            "type": "object",
                            "properties": {
                                "datetime": {
                                    "type": "datetime",
                                    "title": "Datetime"
                                },
                                "label": {
                                    "type": "text",
                                    "title": "Label", "languages": "all"
                                }
                            },
                            "required": ["datetime"]
                        }
                    }
                },
                "required": ["name"],
                "propertyOrder": ["name", "timeline_array"]
            }
        )
        set_action_translation(Language.ENGLISH, timeline_array_action.id, name="Timeline Array Demo Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(timeline_array_action.id, sampledb.models.Permissions.READ)
        sampledb.logic.objects.create_object(
            action_id=timeline_array_action.id,
            data={
                "name": {
                    "_type": "text",
                    "text": {"en": "Timeline Array Demo Object"}
                },
                "timeline_array": [
                    {
                        "datetime": {
                            "_type": "datetime",
                            "utc_datetime": "2024-01-02 03:04:05"
                        }
                    },
                    {
                        "datetime": {
                            "_type": "datetime",
                            "utc_datetime": "2024-01-02 03:04:06"
                        },
                        "label": {
                            "_type": "text",
                            "text": "Very " * 5 + "Long Text"
                        }
                    },
                    {
                        "datetime": {
                            "_type": "datetime",
                            "utc_datetime": "2024-01-02 03:04:07"
                        },
                        "label": {
                            "_type": "text",
                            "text": {"en": "Translated Text EN", "de": "Translated Text DE"}
                        }
                    },
                    {
                        "datetime": {
                            "_type": "datetime",
                            "utc_datetime": "2024-01-02 03:04:04"
                        },
                        "label": {
                            "_type": "text",
                            "text": "HTML tags will be escaped<br />"
                        }
                    }
                ] + [
                    {
                        "datetime": {
                            "_type": "datetime",
                            "utc_datetime": "2024-01-02 03:04:05"
                        },
                        "label": {
                            "_type": "text",
                            "text": f"Event {i}"
                        }
                    }
                    for i in range(5)
                ]
            },
            user_id=instrument_responsible_user.id
        )
        large_table_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema={
                "title": {
                    "en": "Object Information"
                },
                "type": "object",
                "properties": {
                    "name": {
                        "title": {
                            "en": "Name"
                        },
                        "type": "text"
                    },
                    "table": {
                        "type": "array",
                        "title": {
                            "en": "Large Table"
                        },
                        "items": {
                            "type": "object",
                            "title": {
                                "en": "Row"
                            },
                            "properties": {
                                letter: {
                                    "title": {
                                        "en": f"Column {letter.upper()}"
                                    },
                                    "type": "text"
                                }
                                for letter in string.ascii_lowercase
                            }
                        },
                        "defaultItems": 1,
                        "style": {
                            "view": "full_width_table"
                        }
                    }
                },
                "required": [
                    "name"
                ],
                "propertyOrder": [
                    "name", "table"
                ]
            }
        )
        set_action_translation(Language.ENGLISH, large_table_action.id, name="Full Width Table Demo Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(large_table_action.id, sampledb.models.Permissions.READ)

        collapsible_object_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema={
                "title": {
                    "en": "Object Information"
                },
                "type": "object",
                "properties": {
                    "name": {
                        "title": {
                            "en": "Name"
                        },
                        "type": "text"
                    },
                    "collapsible_object": {
                        "title": {
                            "en": "Collapsible Object"
                        },
                        "type": "object",
                        "style": "collapsible",
                        "note": "This object has the 'collapsible' style. It has a button to collapse it.",
                        "properties": {
                            "text_in_object": {
                                "title": {
                                    "en": "Text in Object"
                                },
                                "type": "text"
                            }
                        },
                        "propertyOrder": [
                            "text_in_object"
                        ]
                    },
                    "expandable_object": {
                        "title": {
                            "en": "Expandable Object"
                        },
                        "type": "object",
                        "style": "expandable",
                        "note": "This object has the 'expandable' style. It starts out collapsed with a button to expand it.",
                        "properties": {
                            "text_in_object": {
                                "title": {
                                    "en": "Text in Object"
                                },
                                "type": "text"
                            }
                        },
                        "propertyOrder": [
                            "text_in_object"
                        ]
                    }
                },
                "required": [
                    "name",
                    "collapsible_object",
                    "expandable_object"
                ],
                "propertyOrder": [
                    "name",
                    "collapsible_object",
                    "expandable_object"
                ]
            }
        )
        set_action_translation(Language.ENGLISH, collapsible_object_action.id, name="Collapsible/Expandable Object Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(collapsible_object_action.id, sampledb.models.Permissions.READ)

        horizontal_object_action = sampledb.logic.actions.create_action(
            action_type_id=ActionType.SAMPLE_CREATION,
            schema={
                "title": {
                    "en": "Object Information"
                },
                "type": "object",
                "properties": {
                    "name": {
                        "title": {
                            "en": "Name"
                        },
                        "type": "text"
                    },
                    "quantity_object": {
                        "title": {
                            "en": "Quantity Object"
                        },
                        "type": "object",
                        "style": "horizontal",
                        "properties": {
                            "value": {
                                "title": {
                                    "en": "Value"
                                },
                                "type": "quantity",
                                "units": "kg"
                            },
                            "uncertainty": {
                                "title": {
                                    "en": "Uncertainty"
                                },
                                "type": "quantity",
                                "units": "kg"
                            }
                        },
                        "required": [
                            "value", "uncertainty"
                        ],
                        "propertyOrder": [
                            "value", "uncertainty",
                        ]
                    },
                    "large_object": {
                        "title": {
                            "en": "Large Object"
                        },
                        "type": "object",
                        "style": "horizontal",
                        "properties": {
                            property_name: {
                                "title": {
                                    "en": f"Property {property_title}"
                                },
                                "type": "text",
                                "languages": "all",
                                "note": f"This is a note for property {property_title}"
                            }
                            for property_name, property_title in zip(string.ascii_lowercase, string.ascii_uppercase)
                        }
                    }
                },
                "required": [
                    "name"
                ],
                "propertyOrder": [
                    "name", "quantity_object", "large_object"
                ]
            }
        )
        set_action_translation(Language.ENGLISH, horizontal_object_action.id, name="Horizontal Object Demo Action", description="")
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(horizontal_object_action.id, sampledb.models.Permissions.READ)
        sampledb.logic.objects.create_object(
            action_id=horizontal_object_action.id,
            data={
                "name": {
                    "_type": "text",
                    "text": {"en": "Horizontal Object Demo Object"}
                },
                "quantity_object": {
                    "value": {
                        "_type": "quantity",
                        "units": "kg",
                        "magnitude": 1
                    },
                    "uncertainty": {
                        "_type": "quantity",
                        "units": "kg",
                        "magnitude": 0.2
                    }
                },
                "large_object": {
                    property_name: {
                        "_type": "text",
                        "text": {"en": "Value for " + property_name}
                    }
                    for property_name in string.ascii_lowercase
                }
            },
            user_id=instrument_responsible_user.id
        )

    print("Success: set up demo data", flush=True)
