import datetime
import os.path

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
def eln_zip_bytes(user, app, tmpdir):
    files.FILE_STORAGE_PATH = tmpdir

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
    object_ids, errors = logic.eln_import.import_eln_file(sampledb_eln_import_id)
    assert not errors
    assert len(object_ids) == 1
    imported_object = sampledb.logic.objects.get_object(object_ids[0])
    assert exported_object.data == imported_object.data
    assert exported_object.schema == imported_object.schema


def test_import_elabftw_eln_file(user):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_data', 'eln_exports', 'elabftw-single-experiment.eln'), 'rb') as eln_export_file:
        eln_zip_bytes = eln_export_file.read()
    eln_import_id = logic.eln_import.create_eln_import(
        user_id=user.id,
        file_name='test.eln',
        zip_bytes=eln_zip_bytes
    ).id
    parsed_eln_import = logic.eln_import.parse_eln_file(eln_import_id)
    assert all(len(import_notes) == 1 for import_notes in parsed_eln_import.import_notes.values())
    object_ids, errors = logic.eln_import.import_eln_file(eln_import_id)
    assert not errors
    assert len(object_ids) == 1
    imported_object = sampledb.logic.objects.get_object(object_ids[0])
    assert imported_object.data == {
        'description': {
            '_type': 'text',
            'text': {
                'en': ''
            }
        },
        'name': {
            '_type': 'text',
            'text': {
                'en': 'Example experiment title'
            }
        },
        'import_note': {
            '_type': 'text',
            'text': {
                'en': 'The metadata for this object could not be imported.',
                'de': 'Die Metadaten für dieses Objekt konnten nicht importiert werden.'
            }
        }
    }


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
    object_ids, errors = logic.eln_import.import_eln_file(eln_import_id)
    assert not errors
    assert len(object_ids) == 1
    imported_object = sampledb.logic.objects.get_object(object_ids[0])
    assert imported_object.data == {
        'description': {
            '_type': 'text',
            'text': {
                'en': ''
            }
        },
        'name': {
            '_type': 'text',
            'text': {
                'en': 'Sample Record'
            }
        },
        'import_note': {
            '_type': 'text',
            'text': {
                'en': 'The metadata for this object could not be imported.',
                'de': 'Die Metadaten für dieses Objekt konnten nicht importiert werden.'
            }
        }
    }
