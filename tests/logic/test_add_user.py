import pytest
from bs4 import BeautifulSoup

from sampledb.logic.authentication import insert_user_and_authentication_method_to_db

import sampledb
import sampledb.models


@pytest.fixture
def add_user(flask_server):
    with flask_server.app.app_context():
        result = insert_user_and_authentication_method_to_db('testuser', 'test123', 'example@fz-juelich.de', sampledb.models.AuthenticationType.EMAIL)
        assert len(sampledb.models.User.query.all()) == 1
        if result:
            user =  sampledb.models.query.get(1)
    return user