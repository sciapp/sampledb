# coding: utf-8
"""

"""

import contextlib
import getpass
import copy
import json
import logging
import os
import random
import threading
import time
import typing

# enable Flask debug mode before importing flask
os.environ['FLASK_DEBUG'] = '1'

import cherrypy
import chromedriver_binary
import flask
import flask_login
import pytest
import requests
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
import sqlalchemy
import sqlalchemy.exc

import sampledb
import sampledb.utils
import sampledb.config

# use the minimum number of rounds for bcrypt to speed up tests
sampledb.logic.authentication.NUM_BCYRPT_ROUNDS = 4

sampledb.config.MAIL_SUPPRESS_SEND = True
sampledb.config.TEMPLATES_AUTO_RELOAD = True

# avoid dead database connections, which might occur due to the database reset mechanism in the tests
sampledb.config.SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 60,
    "connect_args": {"options": "-c timezone=utc"},
}
sampledb.config.SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{0}:@localhost:5432/{0}'.format(getpass.getuser())
sampledb.config.MAIL_SENDER = 'sampledb@example.com'
sampledb.config.MAIL_SERVER = 'mail.example.com'
sampledb.config.CONTACT_EMAIL = 'sampledb@example.com'
sampledb.config.JUPYTERHUB_URL = 'example.com'
sampledb.config.LDAP_NAME = 'LDAP'
sampledb.config.LDAP_CONNECT_TIMEOUT = 60  # ldap3 requires long timeout when tests are run in multiple threads

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

    app = create_app()
    # empty the database first, to ensure all tests rebuild it before use
    _create_empty_database_copy(app)
    yield from create_flask_server(app)
    _drop_empty_database_copy()


def create_app():
    logging.getLogger('flask.app').setLevel(logging.WARNING)
    sampledb.utils.empty_database(sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI, **sampledb.config.SQLALCHEMY_ENGINE_OPTIONS), only_delete=True)
    sampledb_app = sampledb.create_app()
    sampledb_app.config['TESTING'] = True

    @sampledb_app.route('/users/me/loginstatus')
    def check_login():
        return flask.jsonify(flask_login.current_user.is_authenticated)

    @sampledb_app.route('/users/<int:user_id>/autologin')
    def autologin(user_id):
        user = sampledb.logic.users.get_user(user_id)
        fresh = json.loads(flask.request.args.get('fresh', 'true'))
        flask_login.login_user(user, fresh=fresh)
        return ''

    return sampledb_app


@pytest.fixture
def app(flask_server):
    app = flask_server.app
    # reset config and database before each test
    app.config = copy.deepcopy(flask_server.initial_config)
    _restore_empty_database_copy()

    # enable german language for input by default during testing
    with app.app_context():
        sampledb.db.engine.dispose()
        german = sampledb.logic.languages.get_language_by_lang_code('de')
        sampledb.logic.languages.update_language(
            language_id=german.id,
            names=german.names,
            lang_code=german.lang_code,
            datetime_format_datetime=german.datetime_format_datetime,
            datetime_format_moment=german.datetime_format_moment,
            datetime_format_moment_output=german.datetime_format_moment_output,
            date_format_moment_output=german.date_format_moment_output,
            enabled_for_input=True,
            enabled_for_user_interface=german.enabled_for_user_interface
        )
    return app


@pytest.fixture(autouse=True)
def app_context(app):
    with app.app_context():
        # yield to keep the app context active until the test is done
        yield None


@pytest.fixture(scope='session')
def driver_session():
    options = Options()
    options.add_argument("--lang=en-US")
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    with contextlib.closing(Chrome(options=options)) as driver:
        # wait for driver to start up
        time.sleep(5)
        driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {'timezoneId': 'UTC'})
        yield driver


@pytest.fixture()
def driver(driver_session):
    driver_session.delete_all_cookies()
    return driver_session


@pytest.fixture(autouse=True)
def clear_cache_functions():
    sampledb.logic.utils.clear_cache_functions()


def _create_empty_database_copy(app):
    database_name = sampledb.config.SQLALCHEMY_DATABASE_URI.rsplit('/')[-1]
    engine = sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI, **sampledb.config.SQLALCHEMY_ENGINE_OPTIONS)

    # setup empty database
    sampledb.utils.empty_database(engine, only_delete=False)
    sampledb.setup_database(app)

    # create a copy (with the suffix _copy) to restore later
    with engine.begin() as connection:
        connection.execute(sqlalchemy.text('COMMIT'))
        for statement in [
            f'SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = \'{database_name}\' AND pid <> pg_backend_pid();',
            f'DROP DATABASE IF EXISTS {database_name}_copy',
            f'CREATE DATABASE {database_name}_copy WITH TEMPLATE {database_name}',
        ]:
            connection.execute(sqlalchemy.text(statement))


def _restore_empty_database_copy():
    database_name = sampledb.config.SQLALCHEMY_DATABASE_URI.rsplit('/')[-1]
    engine = sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI + '_copy', **sampledb.config.SQLALCHEMY_ENGINE_OPTIONS)
    with engine.begin() as connection:
        connection.execute(sqlalchemy.text('COMMIT'))
        for statement in [
            f'SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = \'{database_name}\' AND pid <> pg_backend_pid();',
            f"DROP DATABASE {database_name}",
            f'CREATE DATABASE {database_name} WITH TEMPLATE {database_name}_copy',
        ]:
            connection.execute(sqlalchemy.text(statement))
            connection.execute(sqlalchemy.text('COMMIT'))
    engine.dispose(close=True)


def _drop_empty_database_copy():
    database_name = sampledb.config.SQLALCHEMY_DATABASE_URI.rsplit('/')[-1]
    engine = sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI, **sampledb.config.SQLALCHEMY_ENGINE_OPTIONS)
    with engine.begin() as connection:
        connection.execute(sqlalchemy.text('COMMIT'))
        for statement in [
            f'DROP DATABASE IF EXISTS {database_name}_copy',
        ]:
            connection.execute(sqlalchemy.text(statement))
            connection.execute(sqlalchemy.text('COMMIT'))


@pytest.fixture
def mock_current_user():
    modules = [
        sampledb,
        sampledb.frontend.utils,
        sampledb.frontend.objects.object_form_parser,
        sampledb.logic.utils,
    ]
    current_user_backup = getattr(modules[0], 'current_user')

    class MockUser:
        def __init__(self):
            self.language_cache: typing.List[typing.Optional[sampledb.logic.languages.Language]] = [None]
            self.is_authenticated = True
            self.timezone = 'UTC'
            self.settings = sampledb.logic.settings.DEFAULT_SETTINGS.copy()

        def set_language_by_lang_code(self, lang_code):
            language = sampledb.logic.languages.get_language_by_lang_code(lang_code)
            self.language_cache[0] = language
            self.settings['LOCALE'] = lang_code

    mock_user = MockUser()
    # use english by default to avoid settings lookups
    mock_user.set_language_by_lang_code('en')
    for module in modules:
        setattr(module, 'current_user', mock_user)

    yield mock_user

    for module in modules:
        setattr(module, 'current_user', current_user_backup)
