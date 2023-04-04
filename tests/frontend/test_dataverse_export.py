import pytest
import requests

import sampledb


@pytest.fixture
def user_session(flask_server):
    user = sampledb.models.User(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    session.user_id = user.id
    return session


def test_dataverse_export_status_success(flask_server, user_session):
    task = sampledb.models.BackgroundTask(
        type="dataverse_export",
        status=sampledb.models.BackgroundTaskStatus.DONE,
        data={},
        result={
            "url": "http://localhost/dataverse_url"
        }
    )
    sampledb.db.session.add(task)
    sampledb.db.session.commit()

    r = user_session.get(flask_server.base_url + f'objects/{task.id}/dataverse_export_status')
    assert r.status_code == 200
    assert r.json() == {
        "dataverse_url": "http://localhost/dataverse_url"
    }


def test_dataverse_export_status_error(flask_server, user_session):
    task = sampledb.models.BackgroundTask(
        type="dataverse_export",
        status=sampledb.models.BackgroundTaskStatus.FAILED,
        data={},
        result={
            "error_message": "error"
        }
    )
    sampledb.db.session.add(task)
    sampledb.db.session.commit()

    r = user_session.get(flask_server.base_url + f'objects/{task.id}/dataverse_export_status')
    assert r.status_code == 200
    assert r.json() == {
        "error_message": "error"
    }
