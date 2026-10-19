import datetime

import requests
import pytest

import sampledb
from sampledb import logic


@pytest.fixture
def user(app):
    return logic.users.create_user(
        name="Basic User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )


@pytest.fixture
def eln_import(user):
    eln_import = sampledb.models.ELNImport(
        user_id=user.id,
        file_name='test.eln',
        binary_data=b'test',
        upload_utc_datetime=datetime.datetime.now(datetime.timezone.utc),
        import_utc_datetime=datetime.datetime.now(datetime.timezone.utc),
    )
    sampledb.db.session.add(eln_import)
    sampledb.db.session.commit()
    return eln_import


@pytest.fixture
def eln_preview(eln_import):
    eln_preview = sampledb.models.ELNImportPreviewFile(
        filepath='ro-crate-preview.html',
        eln_import_id=eln_import.id,
        binary_data='<!DOCTYPE html><html></html>'.encode('utf-8'),
        sanitized_binary_data='<!DOCTYPE html><html></html>'.encode('utf-8'),
        mime_type='text/html',
        sanitizer_version=logic.eln_sanitizer.ELNSanitizer.SANITIZER_VERSION,
    )

    sampledb.db.session.add(eln_preview)
    sampledb.db.session.commit()
    return eln_preview


@pytest.fixture
def eln_preview_styles(eln_import):
    eln_preview_styles = sampledb.models.ELNImportPreviewFile(
        filepath='ro-crate-preview_files/styles.css',
        eln_import_id=eln_import.id,
        binary_data='html { background-color: green; }'.encode('utf-8'),
        sanitized_binary_data='html { background-color: green; }'.encode('utf-8'),
        mime_type='text/css',
        sanitizer_version=logic.eln_sanitizer.ELNSanitizer.SANITIZER_VERSION,
    )

    sampledb.db.session.add(eln_preview_styles)
    sampledb.db.session.commit()
    return eln_preview_styles


def test_eln_preview_main_entrypoint_available(flask_server, user, eln_preview):
    session = requests.session()

    assert session.get(f"{flask_server.base_url}users/{user.id}/autologin").status_code == 200

    result = session.get(f"{flask_server.base_url}eln_imports/{eln_preview.eln_import_id}/preview")
    assert result.status_code == 200
    assert result.headers['Content-Type'] == "text/html; charset=utf-8"
    assert result.headers['X-Content-Type-Options'] == 'nosniff'
    assert "script-src 'none'" in result.headers['Content-Security-Policy-Report-Only']
    assert "img-src 'self'" in result.headers['Content-Security-Policy-Report-Only']
    assert result.text == '<!DOCTYPE html><html></html>'


def test_eln_preview_subpath_not_available(flask_server, user, eln_preview):
    session = requests.session()

    assert session.get(f"{flask_server.base_url}users/{user.id}/autologin").status_code == 200

    result = session.get(f"{flask_server.base_url}eln_imports/{eln_preview.eln_import_id}/preview?subpath=not_available.png")
    assert result.status_code == 404


def test_eln_preview_subpath_available(flask_server, user, eln_preview_styles):
    session = requests.session()

    assert session.get(f"{flask_server.base_url}users/{user.id}/autologin").status_code == 200

    result = session.get(f"{flask_server.base_url}eln_imports/{eln_preview_styles.eln_import_id}/preview?subpath=styles.css")
    assert result.status_code == 200
    assert result.headers['Content-Type'] == "text/css; charset=utf-8"
    assert result.headers['X-Content-Type-Options'] == 'nosniff'
    assert "script-src 'none'" in result.headers['Content-Security-Policy-Report-Only']
    assert "img-src 'self'" in result.headers['Content-Security-Policy-Report-Only']
    assert result.text == 'html { background-color: green; }'
