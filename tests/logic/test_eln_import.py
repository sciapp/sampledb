import copy
import datetime
import glob
import hashlib
import io
import itertools
import json
import os.path
import string
import sys
import uuid
import zipfile

import pytest
import requests
import requests_mock

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
def eln_zip_bytes(user, app, flask_server):
    set_up_state(user)

    object = logic.objects.get_objects()[0]
    logic.objects.update_object(
        object_id=object.object_id,
        data={**object.data, "name": {"_type": "text", "text": {"en": "Updated Object"}}},
        user_id=user.id,
    )

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = flask_server.base_url[7:-1]
    with app.test_request_context('/'):
        zip_bytes = export.get_eln_archive(user.id)
    app.config['SERVER_NAME'] = server_name
    return zip_bytes


@pytest.fixture
def eln_zip_bytes_unsigned(user, app):
    set_up_state(user)

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.test_request_context('/'):
        archive_files, infos = export.get_export_infos(
            user_id=user.id,
            object_ids=None,
            include_rdf_files=False,
            include_users=True,
            include_actions=False,
            include_instruments=False,
            include_locations=False,
        )
        binary_archive_files = logic.eln_export.generate_ro_crate_metadata(archive_files, infos, user.id, None)
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, 'w') as zip_file:
            for file_name, file_content in binary_archive_files.items():
                if file_name == 'sampledb_export/ro-crate-metadata.json.minisig':
                    continue
                zip_file.writestr(file_name, file_content)
    app.config['SERVER_NAME'] = server_name
    return zip_bytes.getvalue()


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

def test_get_eln_import_signed_by(flask_server, app, sampledb_eln_import_id):
    assert logic.eln_import.get_import_signed_by(sampledb_eln_import_id) is None
    assert logic.eln_import.get_import_signed_by(sampledb_eln_import_id + 1) is None

    allow_http = app.config["ELN_FILE_IMPORT_ALLOW_HTTP"]
    app.config["ELN_FILE_IMPORT_ALLOW_HTTP"] = True
    logic.eln_import.import_eln_file(sampledb_eln_import_id)
    app.config["ELN_FILE_IMPORT_ALLOW_HTTP"] = allow_http

    assert logic.eln_import.get_import_signed_by(sampledb_eln_import_id) == flask_server.base_url.rstrip('/')


def test_get_eln_import_users(sampledb_eln_import_id):
    assert not sampledb.logic.eln_import.get_eln_import_users(sampledb_eln_import_id)

    logic.eln_import.import_eln_file(sampledb_eln_import_id)

    assert {user.name for user in sampledb.logic.eln_import.get_eln_import_users(sampledb_eln_import_id)} == {'Basic User'}


def test_get_eln_import_objects(sampledb_eln_import_id):
    assert not sampledb.logic.eln_import.get_eln_import_objects(sampledb_eln_import_id)

    logic.eln_import.import_eln_file(sampledb_eln_import_id)

    assert {sampledb.logic.utils.get_translated_text(object.name, 'en') for object in sampledb.logic.eln_import.get_eln_import_objects(sampledb_eln_import_id)} == {'Updated Object'}


def test_get_eln_import_for_object(flask_server, sampledb_eln_import_id):
    assert logic.eln_import.get_eln_import_for_object(-1) is None
    expected_object_url = logic.eln_import.parse_eln_file(sampledb_eln_import_id).objects[0].url
    object_ids, _, _ = logic.eln_import.import_eln_file(sampledb_eln_import_id)
    assert logic.eln_import.get_eln_import_for_object(object_ids[0]) == (logic.eln_import.get_eln_import(sampledb_eln_import_id), expected_object_url)


def test_get_eln_import_object_url(sampledb_eln_import_id):
    assert logic.eln_import.get_eln_import_object_url(-1) is None
    expected_object_url = logic.eln_import.parse_eln_file(sampledb_eln_import_id).objects[0].url
    object_ids, _, _ = logic.eln_import.import_eln_file(sampledb_eln_import_id)
    assert logic.eln_import.get_eln_import_object_url(object_ids[0]) == expected_object_url


def test_get_pending_eln_imports(user, sampledb_eln_import_id):
    assert logic.eln_import.get_pending_eln_imports(user.id) == [logic.eln_import.get_eln_import(sampledb_eln_import_id)]
    logic.eln_import.import_eln_file(sampledb_eln_import_id)
    assert not logic.eln_import.get_pending_eln_imports(user.id)

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


def test_parse_sampledb_eln_file(app, flask_server, sampledb_eln_import_id):
    allow_http = app.config["ELN_FILE_IMPORT_ALLOW_HTTP"]
    app.config["ELN_FILE_IMPORT_ALLOW_HTTP"] = True
    parsed_eln_import = logic.eln_import.parse_eln_file(sampledb_eln_import_id)
    app.config["ELN_FILE_IMPORT_ALLOW_HTTP"] = allow_http

    assert all(len(import_notes) == 0 for import_notes in parsed_eln_import.import_notes.values())
    assert parsed_eln_import.signed_by == f"{flask_server.base_url}".rstrip('/')

    assert len(parsed_eln_import.objects[0].versions) == 2
    assert parsed_eln_import.objects[0].versions[0].version_id == 0 and parsed_eln_import.objects[0].versions[0].data['name']['text'] == 'Object'
    assert parsed_eln_import.objects[0].versions[1].version_id == 1 and parsed_eln_import.objects[0].versions[1].data['name']['text'] == {'en': 'Updated Object'}


def test_parse_sampledb_eln_file_unsigned(user, eln_zip_bytes_unsigned):
    with zipfile.ZipFile(io.BytesIO(eln_zip_bytes_unsigned)) as zip_file:
        assert zip_file.testzip() is None

        member_names = {
            os.path.normpath(member_name): member_name
            for member_name in zip_file.namelist()
        }
        assert 'sampledb_export/ro-crate-metadata.json.minisig' not in member_names

    eln_import = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.zip',
        zip_bytes=eln_zip_bytes_unsigned
    )

    parsed_eln_import = logic.eln_import.parse_eln_file(eln_import.id)
    assert all(len(import_notes) == 0 for import_notes in parsed_eln_import.import_notes.values())
    assert parsed_eln_import.signed_by is None



def test_parse_eln_file_without_objects(user, app, flask_server, eln_zip_bytes):
    eln_zip_bytes_modified = io.BytesIO()
    with zipfile.ZipFile(eln_zip_bytes_modified, 'w') as zip_file_modified:
        with zipfile.ZipFile(io.BytesIO(eln_zip_bytes)) as zip_file:
            for member_name in zip_file.namelist():
                with zip_file.open(member_name) as member_file:
                    member_content = member_file.read()
                normalized_member_name = os.path.normpath(member_name)
                if normalized_member_name == 'sampledb_export/ro-crate-metadata.json':
                    ro_crate_metadata = json.loads(member_content.decode())
                    nodes_by_id = {node['@id']: node for node in ro_crate_metadata['@graph']}
                    nodes_by_id['./']['hasPart'] = []
                    for node_id, node in nodes_by_id.items():
                        if node_id.startswith('./objects/'):
                            ro_crate_metadata['@graph'].remove(node)
                    member_content = json.dumps(ro_crate_metadata).encode()
                zip_file_modified.writestr(member_name, member_content)

    eln_import = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.zip',
        zip_bytes=eln_zip_bytes_modified.getvalue()
    )
    with pytest.raises(logic.errors.InvalidELNFileError) as exc_info:
        logic.eln_import.parse_eln_file(eln_import.id)
    assert str(exc_info.value) == ".eln file must contain at least one object"


def test_parse_eln_file_invalid_zip(user, app, flask_server, eln_zip_bytes):
    eln_import = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.zip',
        zip_bytes=eln_zip_bytes[:-10] + b'Invalid'
    )
    with pytest.raises(logic.errors.InvalidELNFileError) as exc_info:
        logic.eln_import.parse_eln_file(eln_import.id)
    assert str(exc_info.value) == ".eln file must be valid .zip file"


def test_parse_sampledb_eln_file_with_references(user, app, flask_server):
    set_up_state(user)

    object = logic.objects.get_objects()[0]
    schema = object.schema
    data = object.data
    schema["properties"]["local_user"] = {
        "type": "user",
        "title": "User Reference"
    }
    data["local_user"] = {
        "_type": "user",
        "user_id": user.id
    }
    schema["properties"]["eln_user"] = {
        "type": "user",
        "title": "User Reference"
    }
    data["eln_user"] = {
        "_type": "user",
        "user_id": user.id,
        "eln_source_url": "https://example.org",
        "eln_user_url": "https://example.org/users/1"
    }
    schema["properties"]["fed_user"] = {
        "type": "user",
        "title": "User Reference"
    }
    data["fed_user"] = {
        "_type": "user",
        "user_id": 1,
        "component_uuid": str(uuid.uuid4())
    }
    schema["properties"]["local_object"] = {
        "type": "object_reference",
        "title": "Object Reference"
    }
    data["local_object"] = {
        "_type": "object_reference",
        "object_id": object.id
    }
    schema["properties"]["eln_object"] = {
        "type": "object_reference",
        "title": "Object Reference"
    }
    data["eln_object"] = {
        "_type": "object_reference",
        "object_id": object.id,
        "eln_source_url": "https://example.org",
        "eln_object_url": "https://example.org/objects/1"
    }
    schema["properties"]["eln_object"] = {
        "type": "object_reference",
        "title": "Object Reference"
    }
    data["eln_object"] = {
        "_type": "object_reference",
        "object_id": object.id,
        "eln_source_url": "https://example.org",
        "eln_object_url": "https://example.org/objects/1"
    }
    schema["properties"]["fed_object"] = {
        "type": "object_reference",
        "title": "Object Reference"
    }
    data["fed_object"] = {
        "_type": "object_reference",
        "object_id": 1,
        "component_uuid": str(uuid.uuid4())
    }
    schema["properties"]["array"] = {
        "type": "array",
        "title": "Array",
        "items": {
            "type": "text",
            "title": "Text"
        }
    }
    data["array"] = [
        {
            "_type": "text",
            "text": "Test"
        }
    ]
    logic.objects.update_object(
        object_id=object.object_id,
        data=data,
        schema=schema,
        user_id=user.id,
    )

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = flask_server.base_url[7:-1]
    with app.test_request_context('/'):
        zip_bytes = export.get_eln_archive(user.id)
    app.config['SERVER_NAME'] = server_name

    eln_import = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.zip',
        zip_bytes=zip_bytes
    )

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = flask_server.base_url[7:-1]
    with app.test_request_context('/'):
        parsed_eln_import = logic.eln_import.parse_eln_file(eln_import.id)
    app.config['SERVER_NAME'] = server_name

    assert parsed_eln_import.objects[0].versions[1].data["local_user"] == {
        "_type": "user",
        "user_id": user.id,
        "eln_source_url": flask_server.base_url.rstrip('/'),
        "eln_user_url": f"{flask_server.base_url.rstrip('/')}/users/{user.id}"
    }
    assert parsed_eln_import.objects[0].versions[1].data["eln_user"] == {
        "_type": "user",
        "user_id": user.id,
        "eln_source_url": flask_server.base_url.rstrip('/'),
        "eln_user_url": f"{flask_server.base_url.rstrip('/')}/users/{user.id}"
    }
    assert parsed_eln_import.objects[0].versions[1].data["fed_user"] == {
        "_type": "user",
        "user_id": 1,
        "component_uuid": data["fed_user"]["component_uuid"]
    }

    assert parsed_eln_import.objects[0].versions[1].data["local_object"] == {
        "_type": "object_reference",
        "object_id": object.id,
        "eln_source_url": flask_server.base_url.rstrip('/'),
        "eln_object_url": f"{flask_server.base_url.rstrip('/')}/objects/{user.id}"
    }
    assert parsed_eln_import.objects[0].versions[1].data["eln_object"] == {
        "_type": "object_reference",
        "object_id": object.id,
        "eln_source_url": flask_server.base_url.rstrip('/'),
        "eln_object_url": f"{flask_server.base_url.rstrip('/')}/objects/{user.id}"
    }
    assert parsed_eln_import.objects[0].versions[1].data["fed_object"] == {
        "_type": "object_reference",
        "object_id": 1,
        "component_uuid": data["fed_object"]["component_uuid"]
    }


def test_parse_sampledb_eln_file_ro_crate_metadata_modified(user, app, flask_server):
    set_up_state(user)

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = flask_server.base_url[7:-1]
    with app.test_request_context('/'):
        archive_files, infos = export.get_export_infos(
            user_id=user.id,
            object_ids=None,
            include_rdf_files=False,
            include_users=True,
            include_actions=False,
            include_instruments=False,
            include_locations=False,
        )
        binary_archive_files = logic.eln_export.generate_ro_crate_metadata(archive_files, infos, user.id, None)
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, 'w') as zip_file:
            for file_name, file_content in binary_archive_files.items():
                if file_name == 'sampledb_export/ro-crate-metadata.json':
                    file_content = file_content.decode().replace(
                        '"description": "SampleDB .eln export generated for user #1"',
                        '"description": "SampleDB .eln export generated for user #1 modified"'
                    ).encode()
                zip_file.writestr(file_name, file_content)
    app.config['SERVER_NAME'] = server_name

    eln_zip_bytes_modified = zip_bytes.getvalue()

    with zipfile.ZipFile(io.BytesIO(eln_zip_bytes_modified)) as zip_file:
        assert zip_file.testzip() is None

        member_names = {
            os.path.normpath(member_name): member_name
            for member_name in zip_file.namelist()
        }
        assert 'sampledb_export/ro-crate-metadata.json' in member_names
        assert 'sampledb_export/ro-crate-metadata.json.minisig' in member_names

    eln_import = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.zip',
        zip_bytes=eln_zip_bytes_modified
    )

    parsed_eln_import = logic.eln_import.parse_eln_file(eln_import.id)
    assert "Signature" in parsed_eln_import.import_notes and parsed_eln_import.import_notes["Signature"] == ['Invalid URL scheme: http']
    assert all(len(import_notes) == 0 for key, import_notes in parsed_eln_import.import_notes.items() if key != "Signature")
    assert parsed_eln_import.signed_by is None


@pytest.mark.parametrize(
    [
        'modifications',
        'expected_import_notes',
        'mock_urls'
    ],
    [
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: content
            },
            {
                'Signature': ['Invalid URL scheme: http']
            },
            None
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: file:///keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['Invalid URL scheme: file']
            },
            None
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: ./keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['Missing URL scheme']
            },
            None
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://[' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['The signature does not contain a valid URL.']
            },
            None
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['The signature does not contain a valid URL pointing to /.well-known/keys.json.']
            },
            None
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://localhost:5432/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['Failed to connect to https://localhost:5432/.well-known/keys.json.']
            },
            None
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['Received an error from https://example.org/.well-known/keys.json.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "status_code": 404,
                    "text": "Not Found"
                }
            }
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['https://example.org/.well-known/keys.json did not return a valid JSON object.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "text": "-"
                }
            }
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['https://example.org/.well-known/keys.json did not return a valid JSON list.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "json": "key"
                }
            }
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['Successfully fetched all 0 keys but no matching public key was found.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "json": []
                }
            }
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['There was an error checking 1 of 1 public keys. No matching public key was found.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "json": [[]]
                }
            }
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['There was an error checking 1 of 1 public keys. No matching public key was found.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "json": {}
                }
            }
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['There was an error checking 1 of 1 public keys. No matching public key was found.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "json": {
                        "contentUrl": "https://example.org/.well-known/key.json"
                    }
                },
                "https://example.org/.well-known/key.json": {
                    "exc": requests.exceptions.ConnectionError()
                }
            }
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['There was an error checking 1 of 1 public keys. No matching public key was found.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "json": {
                        "contentUrl": "https://example.org/.well-known/key.json"
                    }
                },
                "https://example.org/.well-known/key.json": {
                    "status_code": 404,
                    "text": "Not Found"
                }
            }
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['There was an error checking 1 of 1 public keys. No matching public key was found.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "json": {
                        "contentUrl": "https://example.org/.well-known/key.json"
                    }
                },
                "https://example.org/.well-known/key.json": {
                    "text": "A"
                }
            }
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['There was an error checking 1 of 1 public keys. No matching public key was found.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "json": {
                        "contentUrl": "https://example.org/.well-known/key.json"
                    }
                },
                "https://example.org/.well-known/key.json": {
                    "text": "?"
                }
            }
        ],
        [
            {
                'sampledb_export/ro-crate-metadata.json.minisig': lambda content: (
                        '\n'.join(
                        'trusted comment: https://example.org/.well-known/keys.json' if line.startswith('trusted comment: ') else line
                        for line in content.decode().split('\n')
                    ).encode()
                )
            },
            {
                'Signature': ['Successfully fetched all 1 keys but no matching public key was found.']
            },
            {
                "https://example.org/.well-known/keys.json": {
                    "json": {
                        "contentUrl": "https://example.org/.well-known/key.json"
                    }
                },
                "https://example.org/.well-known/key.json": {
                    "text": "RWSDLBYVmOlYksrC0wULAruKf78kq4JWFHd+7zP35XeJg9LUiIaRUDOm"
                }
            }
        ],
    ]
)
def test_parse_sampledb_eln_file_with_invalid_signature_file(user, app, flask_server, eln_zip_bytes, modifications, expected_import_notes, mock_urls):
    eln_zip_bytes_modified = io.BytesIO()
    with zipfile.ZipFile(eln_zip_bytes_modified, 'w') as zip_file_modified:
        with zipfile.ZipFile(io.BytesIO(eln_zip_bytes)) as zip_file:
            for member_name in zip_file.namelist():
                with zip_file.open(member_name) as member_file:
                    member_content = member_file.read()
                normalized_member_name = os.path.normpath(member_name)
                if normalized_member_name in modifications:
                    member_content = modifications[normalized_member_name](member_content)
                zip_file_modified.writestr(member_name, member_content)

    eln_import = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.zip',
        zip_bytes=eln_zip_bytes_modified.getvalue()
    )

    if mock_urls:
        with requests_mock.Mocker() as mock:
            for mock_url in mock_urls:
                mock.get(mock_url, **mock_urls[mock_url])
            parsed_eln_import = logic.eln_import.parse_eln_file(eln_import.id)
    else:
        parsed_eln_import = logic.eln_import.parse_eln_file(eln_import.id)
    for key in expected_import_notes:
        assert key in parsed_eln_import.import_notes
    for key, value in parsed_eln_import.import_notes.items():
        if value:
            assert key in expected_import_notes and value == expected_import_notes[key]
        else:
            assert key not in expected_import_notes
    assert parsed_eln_import.signed_by is None


@pytest.mark.parametrize(
    'modify_file',
    [
        'sampledb_export/objects/1/versions/0/data.json',
        'sampledb_export/objects/1/versions/0/schema.json',
        'sampledb_export/objects/1/files/0/test.txt'
    ]
)
def test_parse_sampledb_eln_file_object_modified(user, app, flask_server, modify_file):
    set_up_state(user)

    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = flask_server.base_url[7:-1]
    with app.test_request_context('/'):
        archive_files, infos = export.get_export_infos(
            user_id=user.id,
            object_ids=None,
            include_rdf_files=False,
            include_users=True,
            include_actions=False,
            include_instruments=False,
            include_locations=False,
        )
        binary_archive_files = logic.eln_export.generate_ro_crate_metadata(archive_files, infos, user.id, None)
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, 'w') as zip_file:
            for file_name, file_content in binary_archive_files.items():
                if file_name == modify_file:
                    file_content = (file_content.decode()[:-8] + "modified").encode()
                zip_file.writestr(file_name, file_content)
    app.config['SERVER_NAME'] = server_name
    eln_zip_bytes_modified = zip_bytes.getvalue()

    with zipfile.ZipFile(io.BytesIO(eln_zip_bytes_modified)) as zip_file:
        assert zip_file.testzip() is None

        member_names = {
            os.path.normpath(member_name): member_name
            for member_name in zip_file.namelist()
        }
        assert 'sampledb_export/ro-crate-metadata.json' in member_names
        assert 'sampledb_export/ro-crate-metadata.json.minisig' in member_names

    eln_import = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.zip',
        zip_bytes=eln_zip_bytes_modified
    )

    with pytest.raises(errors.InvalidELNFileError) as exc_info:
        logic.eln_import.parse_eln_file(eln_import.id)
    assert 'Hash mismatch' in exc_info.value.args[0]


def test_import_eln_file_invalid_args(sampledb_eln_import_id):
    object_ids, users_by_id, errors = logic.eln_import.import_eln_file(sampledb_eln_import_id + 1)
    assert not object_ids
    assert not users_by_id
    assert errors == ['Unknown ELN import']

    object_ids, users_by_id, errors = logic.eln_import.import_eln_file(sampledb_eln_import_id, [sampledb.logic.action_types.ActionType.SAMPLE_CREATION] * 10)
    assert not object_ids
    assert not users_by_id
    assert errors == ['Invalid Action Type ID information for this ELN file']

    object_ids, users_by_id, errors = logic.eln_import.import_eln_file(sampledb_eln_import_id)
    assert object_ids
    assert users_by_id
    assert not errors

    object_ids, users_by_id, errors = logic.eln_import.import_eln_file(sampledb_eln_import_id)
    assert not object_ids
    assert not users_by_id
    assert errors == ['This ELN file has already been imported']


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
    assert len(object_ids) == 26
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
    data, schema = sampledb.logic.eln_import._convert_property_values_to_data_and_schema(
        property_values=[
            {
                "@type": "PropertyValue",
                "propertyID": "name",
                "value": "Other Object"
            },
            {
                "@type": "PropertyValue",
                "propertyID": "temperature",
                "value": 20,
                "unitText": "degC"
            },
            {
                "@type": "PropertyValue",
                "propertyID": "bool_array.0",
                "value": True
            },
            {
                "@type": "PropertyValue",
                "propertyID": "bool_array.1",
                "value": False
            },
            {
                "@type": "PropertyValue",
                "propertyID": ".0",
                "value": "A"
            },
            {
                "@type": "PropertyValue",
                "propertyID": ".1",
                "value": "B\nC"
            },
            {
                "@type": "PropertyValue",
                "propertyID": ".2",
                "value": False
            },
            {
                "@type": "PropertyValue",
                "propertyID": "temperature_array.1",
                "value": 10,
                "unitText": "degC"
            },
            {
                "@type": "PropertyValue",
                "propertyID": "temperature_array.0",
                "value": 20,
                "unitText": "degC"
            },
        ],
        name='Example Object',
        description='Example Description',
        description_is_markdown=True,
        tags=['test', 'tag']
    )
    sampledb.logic.schemas.validate_schema(schema)
    sampledb.logic.schemas.validate(data, schema)
    assert (data, schema) == (
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
            "temperature": {
                "_type": "quantity",
                "magnitude": 20,
                "units": "degree_Celsius",
                "dimensionality": "[temperature]",
                "magnitude_in_base_units": 293.15
            },
            "bool_array": [
                {
                    "_type": "bool",
                    "value": True
                },
                {
                    "_type": "bool",
                    "value": False
                }
            ],
            "property": [
                {
                    "_type": "text",
                    "text": {
                        "en": "A"
                    }
                },
                {
                    "_type": "text",
                    "text": {
                        "en": "B\nC"
                    }
                },
                {
                    "_type": "text",
                    "text": {
                        "en": "false"
                    }
                }
            ],
            "temperature_array": [
                {
                    "_type": "quantity",
                    "magnitude": 20,
                    "units": "degree_Celsius",
                    "dimensionality": "[temperature]",
                    "magnitude_in_base_units": 293.15
                },
                {
                    "_type": "quantity",
                    "magnitude": 10,
                    "units": "degree_Celsius",
                    "dimensionality": "[temperature]",
                    "magnitude_in_base_units": 283.15
                }
            ],
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
                "temperature": {
                    "title": {
                        "en": "temperature"
                    },
                    "type": "quantity",
                    "units": "degree_Celsius"
                },
                "bool_array": {
                    "items": {
                        "title": {
                            "en": "Item",
                        },
                        "type": "bool",
                    },
                    "title": {
                        "en": "bool_array",
                    },
                    "type": "array",
                },
                "property": {
                    "items": {
                        "title": {
                            "en": "Item",
                        },
                        "type": "text",
                        "multiline": True
                    },
                    "title": {
                        "en": "Array",
                    },
                    "type": "array",
                },
                "temperature_array": {
                    "items": {
                        "title": {
                            "en": "Item"
                        },
                        "type": "quantity",
                        "units": "degree_Celsius"
                    },
                    "title": {
                        "en": "temperature_array",
                    },
                    "type": "array",
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


def _get_reference_eln_file_paths():
    reference_eln_file_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_data', 'eln_files')
    return list(glob.glob('**/*.eln', root_dir=reference_eln_file_directory, recursive=True))


@pytest.mark.parametrize(['eln_file_path'], [[eln_file_path] for eln_file_path in _get_reference_eln_file_paths()])
def test_import_reference_eln_files(user, eln_file_path):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_data', 'eln_files', eln_file_path), 'rb') as eln_export_file:
        eln_zip_bytes = eln_export_file.read()
    eln_import_id = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.eln',
        zip_bytes=eln_zip_bytes
    ).id
    parsed_eln_import = logic.eln_import.parse_eln_file(eln_import_id)
    for import_notes_key, import_notes in parsed_eln_import.import_notes.items():
        if import_notes:
            if import_notes_key == 'Signature':
                # PASTA currently produces a trusted comment that cannot be parsed by SampleDB
                assert eln_file_path in {
                    'PASTA/PASTA.eln'
                }
            else:
                assert import_notes == ['The .eln file did not contain any valid flexible metadata for this object.']
    object_ids, users_by_id, errors = logic.eln_import.import_eln_file(eln_import_id)
    assert not errors
    assert len(object_ids) >= 1
    assert len(users_by_id) >= 1


def test_import_nested_datasets(user):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_data', 'eln_files', 'SciLog', 'export.eln'), 'rb') as eln_export_file:
        eln_zip_bytes = eln_export_file.read()
    eln_import_id = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.eln',
        zip_bytes=eln_zip_bytes
    ).id
    parsed_eln_import = logic.eln_import.parse_eln_file(eln_import_id)
    assert len(parsed_eln_import.objects) == 6
    assert all(len(parsed_object.versions) == 1 for parsed_object in parsed_eln_import.objects)
    objects_by_name = {
        parsed_object.versions[0].data['name']['text']['en']: parsed_object
        for parsed_object in parsed_eln_import.objects
    }
    assert set(objects_by_name.keys()) == {
      'SciLog ELN export: logbook-001',
      'Paragraph 69773b85d55e4cd59458ceb3',
      'Paragraph 696e3faad55e4c82fc58ceae',
      'Paragraph 696e3f8bd55e4c64c058ceac',
      'Comment 697a17c2668d1584a73c7c01',
      'Paragraph 696e3f24d55e4cdffa58ceaa',
    }
    assert parsed_eln_import.object_parts_relationships ==  {
        './696e3f05d55e4c57ec58cea9/': [
            './696e3f24d55e4cdffa58ceaa/',
            './696e3f8bd55e4c64c058ceac/',
            './696e3faad55e4c82fc58ceae/',
            './69773b85d55e4cd59458ceb3/',
            './697a17c2668d1584a73c7c01/'
        ]
    }
    assert parsed_eln_import.import_notes == {
        parsed_object.id: ['The .eln file did not contain any valid flexible metadata for this object.']
        for parsed_object in parsed_eln_import.objects
    }
    imported_object_ids, imported_users, errors = sampledb.logic.eln_import.import_eln_file(eln_import_id)
    imported_objects = [
        sampledb.logic.objects.get_object(object_id)
        for object_id in imported_object_ids
    ]
    imported_objects_by_eln_object_id = {
        object.eln_object_id: object
        for object in imported_objects
    }
    assert imported_objects_by_eln_object_id['./696e3f05d55e4c57ec58cea9/'].schema == {
        "type": "object",
        "title": {
            "en": "Object Information",
            "de": "Objektinformationen"
        },
        "properties": {
            "name": {
                "type": "text",
                "title": {
                    "en": "Name",
                    "de": "Name"
                }
            },
            "description": {
                "type": "text",
                "title": {
                    "en": "Description",
                    "de": "Beschreibung"
                },
                "multiline": False
            },
            "import_note": {
                "type": "text",
                "languages": ["en", "de"],
                "title": {
                    "en": "Import Note",
                    "de": "Import-Hinweis"
                }
            },
            "parts": {
                "type": "array",
                "title": {
                    "en": "Parts",
                    "de": "Teile"
                },
                "items": {
                    "type": "object_reference",
                    "title": {
                        "en": "Part",
                        "de": "Teil"
                    },
                    "style": "include"
                }
            }
        },
        "required": ["name"],
        "propertyOrder": ["name", "description", "import_note", "parts"]
    }
    assert imported_objects_by_eln_object_id['./696e3f05d55e4c57ec58cea9/'].data == {
        "name": {
            "_type": "text",
            "text": {
                "en": "SciLog ELN export: logbook-001"
            }
        },
        "description": {
            "_type": "text",
            "text": {
                "en": "test new logbook"
            }
        },
        "import_note": {
            "_type": "text",
            "text": {
                "en": "The .eln file did not contain any valid flexible metadata for this object.",
                "de": "Die .eln-Datei enthielt keine g\xfcltigen flexiblen Metadaten f\xfcr dieses Objekt."
            }
        },
        "parts": [
            {
                "_type": "object_reference",
                "object_id": imported_objects_by_eln_object_id[eln_object_id].object_id
            }
            for eln_object_id in parsed_eln_import.object_parts_relationships['./696e3f05d55e4c57ec58cea9/']
        ]
    }
    assert not errors
