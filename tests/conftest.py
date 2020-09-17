# coding: utf-8
"""

"""

import getpass
import copy
import logging
import os
import random
import threading
import time

import flask
import flask_login
import pytest
import requests
import sqlalchemy

import sampledb
import sampledb.utils
import sampledb.config

sampledb.config.MAIL_SUPPRESS_SEND = True
sampledb.config.TEMPLATES_AUTO_RELOAD = True

sampledb.config.SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{0}:@localhost:5432/{0}'.format(getpass.getuser())
sampledb.config.MAIL_SENDER = 'sampledb@example.com'
sampledb.config.MAIL_SERVER = 'mail.example.com'
sampledb.config.CONTACT_EMAIL = 'sampledb@example.com'
sampledb.config.JUPYTERHUB_URL = 'example.com'
sampledb.config.LDAP_NAME = 'LDAP'

sampledb.config.TESTING_LDAP_UNKNOWN_LOGIN = 'unknown-login-for-sampledb-tests'
sampledb.config.TESTING_LDAP_WRONG_PASSWORD = 'wrong-password-for-sampledb-tests'

# restore possibly overridden configuration data from environment variables
sampledb.config.use_environment_configuration(env_prefix='SAMPLEDB_')


def create_flask_server(app):
    if not getattr(app, 'has_shutdown_route', False):
        @app.route('/shutdown', methods=['POST'])
        def shutdown():
            func = flask.request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
            return 'Server shutting down...'
        app.has_shutdown_route = True

    port = random.randint(10000, 20000)
    server_thread = threading.Thread(target=lambda: app.run(port=port, debug=True, use_reloader=False), daemon=True)
    server_thread.start()
    server_thread.app = app
    server_thread.initial_config = copy.deepcopy(server_thread.app.config)
    server_thread.base_url = 'http://localhost:{0}/'.format(port)
    server_thread.api_url = server_thread.base_url + 'api/'
    # short delay to allow the web server to start
    time.sleep(0.1)
    yield server_thread
    # restore initial configuration
    server_thread.app.config = server_thread.initial_config
    r = requests.post(server_thread.base_url + 'shutdown')
    assert r.status_code == 200
    server_thread.join()


@pytest.fixture(scope='session')
def flask_server():
    app = create_app()
    # empty the database first, to ensure all tests rebuild it before use
    sampledb.utils.empty_database(sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI))
    yield from create_flask_server(app)


def create_app():
    logging.getLogger('flask.app').setLevel(logging.WARNING)
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_TESTING'] = 'True'
    sampledb.utils.empty_database(sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI))
    sampledb_app = sampledb.create_app()

    @sampledb_app.route('/users/me/loginstatus')
    def check_login():
        return flask.jsonify(flask_login.current_user.is_authenticated)

    @sampledb_app.route('/users/<int:user_id>/autologin')
    def autologin(user_id):
        user = sampledb.models.User.query.get(user_id)
        assert user is not None
        flask_login.login_user(user)
        return ''

    return sampledb_app


@pytest.fixture
def app(flask_server):
    app = flask_server.app
    # reset config and database before each test
    app.config = copy.deepcopy(flask_server.initial_config)
    sampledb.utils.empty_database(sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI))
    sampledb.setup_database(app)
    return app


@pytest.fixture(autouse=True)
def app_context(app):
    with app.app_context():
        # yield to keep the app context active until the test is done
        yield None
