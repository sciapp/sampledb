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

import cherrypy
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

sampledb.config.FEDERATION_UUID = 'aef05dbb-2763-49d1-964d-71205d8da0bf'

# restore possibly overridden configuration data from environment variables
sampledb.config.use_environment_configuration(env_prefix='SAMPLEDB_')


def create_flask_server(app):
    if not getattr(app, 'has_shutdown_route', False):
        @app.route('/shutdown', methods=['POST'])
        def shutdown():
            cherrypy.engine.exit()
            return 'Server shutting down...'
        app.has_shutdown_route = True

    def run_server():
        cherrypy.engine.start()
        cherrypy.engine.block()

    app.debug = True
    port = random.randint(10000, 20000)
    cherrypy.tree.graft(app, '/')
    cherrypy.config.update({
        'environment': 'test_suite',
        'server.socket_host': '127.0.0.1',
        'server.socket_port': port,
        'server.socket_queue_size': 20,
        'log.screen': True
    })
    server_thread = threading.Thread(target=run_server, daemon=True)
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
def flask_server(worker_id):
    if worker_id != 'master':
        sampledb.config.SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://postgres:@postgres:5432/testdb_" + worker_id[2:]
        sampledb.config.FILE_STORAGE_PATH = sampledb.config.FILE_STORAGE_PATH + worker_id[2:] + '/'

    app = create_app()
    # empty the database first, to ensure all tests rebuild it before use
    if worker_id != 'master':
        sampledb.utils.empty_database(sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI), only_delete=True)
    else:
        sampledb.utils.empty_database(sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI), only_delete=False)
    yield from create_flask_server(app)


def create_app():
    logging.getLogger('flask.app').setLevel(logging.WARNING)
    os.environ['FLASK_ENV'] = 'development'
    sampledb.utils.empty_database(sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI), only_delete=True)
    sampledb_app = sampledb.create_app()
    sampledb_app.config['TESTING'] = True

    @sampledb_app.route('/users/me/loginstatus')
    def check_login():
        return flask.jsonify(flask_login.current_user.is_authenticated)

    @sampledb_app.route('/users/<int:user_id>/autologin')
    def autologin(user_id):
        user = sampledb.logic.users.get_user(user_id)
        flask_login.login_user(user)
        return ''

    return sampledb_app


@pytest.fixture
def app(flask_server):
    app = flask_server.app
    # reset config and database before each test
    app.config = copy.deepcopy(flask_server.initial_config)
    sampledb.utils.empty_database(sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI), only_delete=True)
    sampledb.setup_database(app)

    # enable german language for input by default during testing
    with app.app_context():
        german = sampledb.logic.languages.get_language_by_lang_code('de')
        sampledb.logic.languages.update_language(
            language_id=german.id,
            names=german.names,
            lang_code=german.lang_code,
            datetime_format_datetime=german.datetime_format_datetime,
            datetime_format_moment=german.datetime_format_moment,
            datetime_format_moment_output=german.datetime_format_moment_output,
            enabled_for_input=True,
            enabled_for_user_interface=german.enabled_for_user_interface
        )
    return app


@pytest.fixture(autouse=True)
def app_context(app):
    with app.app_context():
        # yield to keep the app context active until the test is done
        yield None
