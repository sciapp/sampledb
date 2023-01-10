import flask
import requests
import pytest
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound, InternalServerError

import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def auth_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_other_authentication(user.id, 'username', 'password')
        assert user.id is not None
    return ('username', 'password'), user


@pytest.fixture
def auth(auth_user):
    return auth_user[0]


@pytest.fixture
def user(auth_user):
    return auth_user[1]


sampledb.api.server.api.add_url_rule(
    '/api/v1/errors/<int:error_code>', endpoint='errors', view_func=lambda error_code: flask.abort(error_code)
)


def test_errors(flask_server, auth, user):
    # actual errors from the API
    r = requests.get(flask_server.base_url + 'api/v1/errors', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."
    }
    r = requests.get(flask_server.base_url + 'api/v1/objects/')
    assert r.status_code == 401
    assert r.json() == {
        'message': "The server could not verify that you are authorized to access the URL requested. You either supplied the wrong credentials (e.g. a bad password), or your browser doesn't understand how to supply the credentials required."
    }
    # simulated errors
    for error in [BadRequest, Unauthorized, Forbidden, NotFound, InternalServerError]:
        status_code = error.code
        message = error.description
        r = requests.get(flask_server.base_url + f'api/v1/errors/{status_code}', auth=auth)
        assert r.status_code == status_code
        assert r.json() == {
            'message': message
        }
