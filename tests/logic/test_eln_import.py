import copy
import datetime
import itertools
import os.path
import string
import sys

import pytest

import sampledb
from sampledb.logic import errors, export, files
from sampledb import logic, db

from .test_export import set_up_state


@pytest.fixture
def user(flask_server):
    return logic.users.create_user(
        name="Basic User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )


@pytest.fixture
def eln_zip_bytes(user, app):
    set_up_state(user)

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        zip_bytes = export.get_eln_archive(user.id)
    app.config['SERVER_NAME'] = server_name
    return zip_bytes


@pytest.fixture
def sampledb_eln_import_id(user, eln_zip_bytes):
    return logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.eln',
        zip_bytes=eln_zip_bytes
    ).id


@pytest.fixture
def eln_import_id(user):
    eln_import = sampledb.models.ELNImport(
        user_id=user.id,
        file_name='test.eln',
        binary_data=b'test',
        upload_utc_datetime=datetime.datetime.now(datetime.timezone.utc),
        import_utc_datetime=None
    )
    db.session.add(eln_import)
    db.session.commit()
    return eln_import.id


def test_create_eln_import(user, eln_zip_bytes):
    eln_import = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.zip',
        zip_bytes=eln_zip_bytes
    )
    assert eln_import.user_id == user.id
    assert eln_import.file_name == 'test.zip'
    assert eln_import.imported is False
    assert eln_import.upload_utc_datetime < datetime.datetime.now(datetime.timezone.utc)
    assert eln_import.upload_utc_datetime > datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)


def test_get_eln_import(user, sampledb_eln_import_id):
    eln_import = logic.eln_import.get_eln_import(sampledb_eln_import_id)
    assert eln_import.id == sampledb_eln_import_id

    with pytest.raises(errors.ELNImportDoesNotExistError):
        logic.eln_import.get_eln_import(sampledb_eln_import_id + 1)


def test_remove_expired_eln_imports(user):
    eln_import = sampledb.models.ELNImport(
        user_id=user.id,
        file_name='test.zip',
        binary_data=b'test',
        upload_utc_datetime=datetime.datetime.now(datetime.timezone.utc),
        import_utc_datetime=None
    )
    db.session.add(eln_import)
    db.session.commit()
    eln_import_id = eln_import.id
    assert sampledb.models.ELNImport.query.filter_by(id=eln_import_id).first() is not None

    logic.eln_import.remove_expired_eln_imports()
    assert sampledb.models.ELNImport.query.filter_by(id=eln_import_id).first() is not None

    eln_import = sampledb.models.ELNImport.query.filter_by(id=eln_import_id).first()
    eln_import.import_utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    db.session.add(eln_import)
    db.session.commit()
    logic.eln_import.remove_expired_eln_imports()
    assert sampledb.models.ELNImport.query.filter_by(id=eln_import_id).first() is not None

    eln_import.upload_utc_datetime = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
    logic.eln_import.remove_expired_eln_imports()
    assert sampledb.models.ELNImport.query.filter_by(id=eln_import_id).first() is not None

    eln_import = sampledb.models.ELNImport.query.filter_by(id=eln_import_id).first()
    eln_import.import_utc_datetime = None
    db.session.add(eln_import)
    db.session.commit()
    logic.eln_import.remove_expired_eln_imports()
    assert sampledb.models.ELNImport.query.filter_by(id=eln_import_id).first() is None


def test_delete_eln_import(eln_import_id):
    eln_import = sampledb.models.ELNImport.query.filter_by(id=eln_import_id).first()
    assert eln_import is not None

    logic.eln_import.delete_eln_import(eln_import_id)

    eln_import = sampledb.models.ELNImport.query.filter_by(id=eln_import_id).first()
    assert eln_import is None

    with pytest.raises(logic.errors.ELNImportDoesNotExistError):
        logic.eln_import.delete_eln_import(eln_import_id)


def test_mark_eln_import_invalid(eln_import_id):
    eln_import = logic.eln_import.get_eln_import(eln_import_id)
    assert eln_import.is_valid
    assert eln_import.invalid_reason is None

    logic.eln_import.mark_eln_import_invalid(eln_import_id, "test")

    eln_import = logic.eln_import.get_eln_import(eln_import_id)
    assert not eln_import.is_valid
    assert eln_import.invalid_reason == "test"

    logic.eln_import.delete_eln_import(eln_import_id)
    with pytest.raises(logic.errors.ELNImportDoesNotExistError):
        logic.eln_import.mark_eln_import_invalid(eln_import_id, "test")


def test_parse_sampledb_eln_file(sampledb_eln_import_id):
    parsed_eln_import = logic.eln_import.parse_eln_file(sampledb_eln_import_id)
    assert all(len(import_notes) == 0 for import_notes in parsed_eln_import.import_notes.values())


def test_import_sampledb_eln_file(sampledb_eln_import_id):
    exported_object = sampledb.logic.objects.get_objects()[0]
    object_ids, users_by_id, errors = logic.eln_import.import_eln_file(sampledb_eln_import_id)
    assert not errors
    assert len(object_ids) == 1
    imported_object = sampledb.logic.objects.get_object(object_ids[0])
    assert exported_object.data == imported_object.data
    assert exported_object.schema == imported_object.schema
    assert len(users_by_id) == 1
    assert './users/1' in users_by_id
    assert users_by_id['./users/1'].eln_object_id == './users/1'


def test_import_elabftw_eln_file(user):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_data', 'eln_exports', 'elabftw-export.eln'), 'rb') as eln_export_file:
        eln_zip_bytes = eln_export_file.read()
    eln_import_id = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.eln',
        zip_bytes=eln_zip_bytes
    ).id
    parsed_eln_import = logic.eln_import.parse_eln_file(eln_import_id)
    assert parsed_eln_import.import_notes == {
        './RD - Testing-relationship-between-acceleration-and-gravity - 5adb0eb3/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Demo - Synthesis-of-Aspirin - 6bc46aec/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Project-CRYPTO-COOL - Testing-the-eLabFTW-lab-notebook - 8ebcfca1/': [],
        './Project-CRYPTO-COOL - Gold-master-experiment - df81f900/': [],
        './Tests - Numquam-delectus-sint-quis-sint-cupiditate-non-voluptatem - 10df895d/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Generated - Architecto-est-recusandae-tempora-facilis-nemo - 67d460ac/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Generated - Minus-qui-dolorem-praesentium-quos-aliquam-quia-ea - 18fd5717/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Project-CRYPTO-COOL - Effect-of-temperature-on-enzyme-activity - d938ab84/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Project-CRYPTO-COOL - フルーツフライの食性に関する研究 - f44d2c0b/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Project-CRYPTO-COOL - Synthesis-and-Characterization-of-a-Novel-Organic-Compound-with-Antimicrobial- - 412e346f/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Project-CRYPTO-COOL - Transfection-of-p103Δ12-22-into-RPE-1-Actin-RFP - 4b08c8b1/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Project-CRYPTO-COOL - An-example-experiment - 4ae900b8/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Project-CRYPTO-COOL - Test-the-grouped-extra-fields - 4220974c/': [],
        './Production - Omnis-non-est-unde-excepturi-maxime - f04d5cb3/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Support-ticket - Nisi-voluptatem-placeat-repudiandae-et-provident - a58088c7/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Tests - Et-ea-sapiente-officiis-hic-libero - a6c65a6d/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Discussions - Numquam-alias-repellendus-corporis - 2c266830/': ['The .eln file did not contain any valid flexible metadata for this object.'],
        './Demo - Officiis-consequatur-vel-ut-nihil-sit-ut - 350a45f5/': ['The .eln file did not contain any valid flexible metadata for this object.']
    }
    object_ids, users_by_id, errors = logic.eln_import.import_eln_file(eln_import_id)
    assert not errors
    assert len(object_ids) == 18
    for object_id in object_ids:
        imported_object = sampledb.logic.objects.get_object(object_id)
        if imported_object.eln_object_id == './RD - Testing-relationship-between-acceleration-and-gravity - 5adb0eb3/':
            assert imported_object.data == {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Testing relationship between acceleration and gravity'
                    }
                },
                'import_note': {
                    '_type': 'text',
                    'text': {
                        'en': 'The .eln file did not contain any valid flexible metadata for this object.',
                        'de': 'Die .eln-Datei enthielt keine gültigen flexiblen Metadaten für dieses Objekt.'
                    }
                },
                'tags': {
                    '_type': 'tags',
                    'tags': [
                        'has-mathjax',
                        'physics'
                    ]
                }
            }
        elif imported_object.eln_object_id == './Project-CRYPTO-COOL - Testing-the-eLabFTW-lab-notebook - 8ebcfca1/':
            assert imported_object.data == {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Testing the eLabFTW lab notebook'
                    }
                },
                'tags': {
                    '_type': 'tags',
                    'tags': [
                        'demo',
                        'test'
                    ]
                },
                'omerodataseturl': {
                    '_type': 'text',
                    'text': {
                        'en': 'https://omero.uni.example.edu/viewer?team=39&project=194'
                    }
                },
                'annieareyouokay': {
                    '_type': 'text',
                    'text': {
                        'en': ''
                    }
                },
                'thisisacustomlistinput': {
                    '_type': 'text',
                    'text': {
                        'en': 'Some choice'
                    }
                }
            }
    assert len(users_by_id) == 4


def test_import_pasta_eln_file(user):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_data', 'eln_exports', 'PASTA.eln'), 'rb') as eln_export_file:
        eln_zip_bytes = eln_export_file.read()
    eln_import_id = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.eln',
        zip_bytes=eln_zip_bytes
    ).id
    parsed_eln_import = logic.eln_import.parse_eln_file(eln_import_id)
    assert all(len(import_notes) <= 1 for import_notes in parsed_eln_import.import_notes.values())
    object_ids, users_by_id, errors = logic.eln_import.import_eln_file(eln_import_id)
    assert not errors
    assert len(object_ids) == 16
    assert len(users_by_id) == 1
    assert 'author_Steffen_Brinckmann' in users_by_id
    assert users_by_id['author_Steffen_Brinckmann'].eln_object_id == 'author_Steffen_Brinckmann'


def test_import_kadi4mat_eln_file(user):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_data', 'eln_exports', 'kadi4mat-records-example.eln'), 'rb') as eln_export_file:
        eln_zip_bytes = eln_export_file.read()
    eln_import_id = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.eln',
        zip_bytes=eln_zip_bytes
    ).id
    parsed_eln_import = logic.eln_import.parse_eln_file(eln_import_id)
    assert all(len(import_notes) == 1 for import_notes in parsed_eln_import.import_notes.values())
    object_ids, users_by_id, errors = logic.eln_import.import_eln_file(eln_import_id)
    assert not errors
    assert len(object_ids) == 1
    imported_object = sampledb.logic.objects.get_object(object_ids[0])
    assert imported_object.data == {
        'name': {
            '_type': 'text',
            'text': {
                'en': 'Sample Record'
            }
        },
        'import_note': {
            '_type': 'text',
            'text': {
                'en': 'The .eln file did not contain any valid flexible metadata for this object.',
                'de': 'Die .eln-Datei enthielt keine gültigen flexiblen Metadaten für dieses Objekt.'
            }
        },
        'tags': {
            '_type': 'tags',
            'tags': ['characterization', 'experiment']
        }
    }
    assert len(users_by_id) == 1
    assert 'http://localhost:5000/users/34' in users_by_id
    assert users_by_id['http://localhost:5000/users/34'].eln_object_id == 'http://localhost:5000/users/34'


def test_eln_federated_identity(user, sampledb_eln_import_id):
    eln_dummy = logic.users.create_user('ELN Dummy', 'eln-dummy@example.com', logic.users.UserType.ELN_IMPORT_USER)
    assert logic.users.FederatedIdentity.query.filter_by(user_id=user.id, local_fed_id=eln_dummy.id).first() is None
    federated_identity = logic.users.create_eln_federated_identity(user.id, eln_dummy.id)
    assert federated_identity is not None
    assert logic.users.FederatedIdentity.query.filter_by(user_id=user.id, local_fed_id=eln_dummy.id).first() is not None


def test_edit_eln_federated_identity(user, sampledb_eln_import_id):
    eln_dummy = logic.users.create_user('ELN Dummy', 'eln-dummy@example.com', logic.users.UserType.ELN_IMPORT_USER)
    assert logic.users.FederatedIdentity.query.filter_by(user_id=user.id, local_fed_id=eln_dummy.id).first() is None
    federated_identity = logic.users.create_eln_federated_identity(user.id, eln_dummy.id)
    assert federated_identity is not None
    assert logic.users.FederatedIdentity.query.filter_by(user_id=user.id, local_fed_id=eln_dummy.id).first() is not None
    assert federated_identity.active
    logic.users.revoke_user_link(user.id, federated_identity.local_fed_id)
    assert not federated_identity.active
    logic.users.enable_user_link(user.id, federated_identity.local_fed_id)
    assert federated_identity.active
    logic.users.delete_user_link(user.id, federated_identity.local_fed_id)
    assert logic.users.FederatedIdentity.query.filter_by(user_id=user.id, local_fed_id=eln_dummy.id).first() is None


def test_convert_property_values_to_data_and_schema():
    assert sampledb.logic.eln_import._convert_property_values_to_data_and_schema(
        property_values=[
            {
                "@type": "PropertyValue",
                "propertyID": "name",
                "value": "Example Object"
            }
        ],
        name='Example Object',
        description='',
        description_is_markdown=False,
        tags=[]
    ) == (
        {
            "name": {
                "_type": "text",
                "text": {
                    "en": "Example Object"
                }
            }
        },
        {
            "title": {
                "en": "Object"
            },
            "type": "object",
            "properties": {
                "name": {
                    "title": {
                        "en": "name"
                    },
                    "type": "text"
                }
            },
            "required": ["name"],
            "propertyOrder": ["name"]
        }
    )
    assert sampledb.logic.eln_import._convert_property_values_to_data_and_schema(
        property_values=[
            {
                "@type": "PropertyValue",
                "propertyID": "name",
                "value": "Other Object"
            }
        ],
        name='Example Object',
        description='Example Description',
        description_is_markdown=True,
        tags=['test', 'tag']
    ) == (
        {
            "name": {
                "_type": "text",
                "text": {
                    "en": "Example Object"
                }
            },
            "property_name": {
                "_type": "text",
                "text": {
                    "en": "Other Object"
                }
            },
            "description": {
                "_type": "text",
                "text": {
                    "en": "Example Description"
                },
                "is_markdown": True
            },
            "tags": {
                "_type": "tags",
                "tags": ["test", "tag"]
            }
        },
        {
            "title": {
                "en": "Object"
            },
            "type": "object",
            "properties": {
                "name": {
                    "title": {
                        "en": "Name"
                    },
                    "type": "text"
                },
                "property_name": {
                    "title": {
                        "en": "name"
                    },
                    "type": "text"
                },
                "description": {
                    "title": {
                        "en": "Description"
                    },
                    "type": "text",
                    "markdown": True
                },
                "tags": {
                    "title": {
                        "en": "Tags"
                    },
                    "type": "tags"
                }
            },
            "required": ["name"],
            "propertyOrder": ["name", "description", "tags"]
        }
    )


def test_map_property_values_to_paths():
    assert sampledb.logic.eln_import._map_property_values_to_paths([
        {
            'propertyID': 'name',
            'value': 0
        },
        {
            'propertyID': 'samples',
            'value': 1
        },
        {
            'propertyID': 'samples',
            'value': 2
        },
        {
            'propertyID': 'samples.1',
            'value': 3
        },
        {
            'propertyID': 'samples.2',
            'value': 4
        },
        {
            'propertyID': 'samples.0',
            'value': 5
        },
        {
            'propertyID': 'other.property.id',
            'value': 6
        }
    ]) == {
        ('name',): {
            'propertyID': 'name',
            'value': 0
        },
        ('samples',): {
            'propertyID': 'samples',
            'value': 1
        },
        ('property_samples',): {
            'propertyID': 'samples',
            'value': 2
        },
        ('property2_samples', 0): {
            'propertyID': 'samples.0',
            'value': 5
        },
        ('property2_samples', 1): {
            'propertyID': 'samples.1',
            'value': 3
        },
        ('property2_samples', 2): {
            'propertyID': 'samples.2',
            'value': 4
        },
        ('other', 'property', 'id'): {
            'propertyID': 'other.property.id',
            'value': 6
        }
    }

    assert sampledb.logic.eln_import._map_property_values_to_paths([
        {
            'propertyID': '',
            'value': 0
        },
        {
            'propertyID': '_',
            'value': 1
        },
        {
            'propertyID': '__',
            'value': 2
        },
        {
            'propertyID': '___',
            'value': 3
        },
        {
            'propertyID': '.',
            'value': 4
        },
        {
            'propertyID': '..',
            'value': 5
        },
        {
            'propertyID': '.property.',
            'value': 6
        }
    ]) == {
        ('property',): {
            'propertyID': '',
            'value': 0
        },
        ('property3',): {
            'propertyID': '_',
            'value': 1
        },
        ('property4',): {
            'propertyID': '__',
            'value': 2
        },
        ('property5',): {
            'propertyID': '___',
            'value': 3
        },
        ('property2','property'): {
            'propertyID': '.',
            'value': 4
        },
        ('property2', 'property2', 'property'): {
            'propertyID': '..',
            'value': 5
        },
        ('property2', 'property_property', 'property'): {
            'propertyID': '.property.',
            'value': 6
        }
    }
