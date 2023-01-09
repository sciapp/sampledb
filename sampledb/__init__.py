import json
import os
import signal
import subprocess
import sys
import typing

import flask
from flask_babel import Babel
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from bs4 import BeautifulSoup

login_manager = LoginManager()
login_manager.session_protection = 'basic'

mail = Mail()
db = SQLAlchemy()
babel = Babel()


import sampledb.dashboard
import sampledb.frontend
import sampledb.api
import sampledb.logic
import sampledb.models
import sampledb.models.migrations
import sampledb.config


@babel.localeselector  # type: ignore
def set_locale() -> str:
    if hasattr(flask.g, 'override_locale') and flask.g.override_locale in sampledb.logic.locale.get_allowed_language_codes():
        return typing.cast(str, flask.g.override_locale)

    request_locale = sampledb.logic.locale.guess_request_locale()

    if not current_user or not current_user.is_authenticated:
        return request_locale

    auto_lc = sampledb.logic.settings.get_user_setting(current_user.id, 'AUTO_LC')
    if auto_lc:
        return request_locale

    stored_locale = sampledb.logic.settings.get_user_setting(current_user.id, 'LOCALE')
    if stored_locale in sampledb.logic.locale.get_allowed_language_codes():
        return typing.cast(str, stored_locale)

    return request_locale


@babel.timezoneselector  # type: ignore
def set_timezone() -> typing.Optional[str]:
    if flask.current_app.config['TIMEZONE']:
        return typing.cast(typing.Optional[str], flask.current_app.config['TIMEZONE'])
    if current_user.is_authenticated:
        settings = sampledb.logic.settings.get_user_settings(current_user.id)
        if settings['AUTO_TZ']:
            return typing.cast(typing.Optional[str], flask.request.args.get('timezone', settings['TIMEZONE']))
        return typing.cast(typing.Optional[str], settings['TIMEZONE'])
    return flask.request.args.get('timezone', None)


def setup_database(app: flask.Flask) -> None:
    with app.app_context():
        db.metadata.create_all(bind=db.engine)
        sampledb.models.Objects.bind = db.engine
        sampledb.models.migrations.run(db)


def setup_admin_account_from_config(app: flask.Flask) -> None:
    with app.app_context():
        if 'ADMIN_INFO' in app.config['internal'] and not sampledb.logic.users.get_users(exclude_hidden=False):
            admin_username, admin_email, admin_password = app.config['internal']['ADMIN_INFO']
            admin_user = sampledb.logic.users.create_user(
                admin_username,
                admin_email,
                sampledb.models.users.UserType.PERSON
            )
            sampledb.logic.authentication.add_other_authentication(
                admin_user.id,
                admin_username,
                admin_password,
                confirmed=True
            )
            sampledb.logic.users.set_user_administrator(admin_user.id, True)


def setup_jinja_environment(app: flask.Flask) -> None:
    with app.app_context():
        is_ldap_configured = sampledb.logic.ldap.is_ldap_configured()

    if app.config['JUPYTERHUB_TEMPLATES_URL']:
        jupyterhub_templates_url = app.config['JUPYTERHUB_TEMPLATES_URL']
    elif app.config['JUPYTERHUB_URL']:
        jupyterhub_templates_url = app.config['JUPYTERHUB_URL'] + '/templates'
    else:
        jupyterhub_templates_url = None

    app.jinja_env.add_extension('jinja2.ext.loopcontrols')
    app.jinja_env.policies['json.dumps_kwargs'] = {'ensure_ascii': False}

    app.jinja_env.globals.update(
        export_file_formats=sampledb.logic.export.FILE_FORMATS,
        jupyterhub_name=app.config['JUPYTERHUB_NAME'],
        jupyterhub_templates_url=jupyterhub_templates_url,
        signout_form=sampledb.frontend.users_forms.SignoutForm,
        service_name=app.config['SERVICE_NAME'],
        service_description=app.config['SERVICE_DESCRIPTION'],
        service_legal_notice=app.config['SERVICE_LEGAL_NOTICE'],
        service_privacy_policy=app.config['SERVICE_PRIVACY_POLICY'],
        service_accessibility=app.config['SERVICE_ACCESSIBILITY'],
        ldap_name=app.config['LDAP_NAME'],
        is_ldap_configured=is_ldap_configured,
        get_action_types=sampledb.logic.actions.get_action_types,
        get_translated_text=sampledb.logic.utils.get_translated_text,
        BeautifulSoup=BeautifulSoup,
        json=json,
        contact_email=app.config['CONTACT_EMAIL'],
        get_user_settings=lambda: sampledb.logic.settings.get_user_settings(current_user.id),
        TimezoneForm=sampledb.frontend.timezone.TimezoneForm,
        get_user_language=sampledb.logic.languages.get_user_language,
        NotificationType=sampledb.models.NotificationType,
        get_user=sampledb.logic.users.get_user,
    )
    app.jinja_env.filters.update(sampledb.frontend.utils.jinja_filter.filters)  # type: ignore
    app.jinja_env.globals.update(sampledb.frontend.utils.jinja_function.functions)  # type: ignore


def build_translations(pybabel_path: str) -> None:
    translations_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'translations'))
    # merge extracted and manual message catalogs
    for translation_directory in os.listdir(translations_directory):
        translation_directory = os.path.join(translations_directory, translation_directory)
        extracted_message_catalog_path = os.path.join(translation_directory, 'LC_MESSAGES', 'extracted_messages.po')
        manual_message_catalog_path = os.path.join(translation_directory, 'LC_MESSAGES', 'manual_messages.po')
        merged_message_catalog_path = os.path.join(translation_directory, 'LC_MESSAGES', 'messages.po')
        if os.path.isfile(extracted_message_catalog_path) and os.path.isfile(manual_message_catalog_path):
            # manually merge instead of using msgcat to avoid duplicate headers
            with open(extracted_message_catalog_path, 'r', encoding='utf-8') as extracted_message_catalog_file:
                extracted_message_catalog = extracted_message_catalog_file.read()
            with open(manual_message_catalog_path, 'r', encoding='utf-8') as manual_message_catalog_file:
                manual_message_catalog = manual_message_catalog_file.read()
            with open(merged_message_catalog_path, 'w', encoding='utf-8') as merged_message_catalog_file:
                merged_message_catalog_file.write(extracted_message_catalog)
                merged_message_catalog_file.write(manual_message_catalog)
    # compile messages
    subprocess.run([pybabel_path, "compile", "-d", translations_directory], check=True)


def create_app(include_dashboard: bool = True) -> flask.Flask:
    app = flask.Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app)  # type: ignore

    app.config.from_object(sampledb.config)

    internal_config = sampledb.config.check_config(app.config)
    app.config['internal'] = internal_config

    login_manager.init_app(app)
    mail.init_app(app)
    db.init_app(app)  # type: ignore
    babel.init_app(app)
    if include_dashboard and app.config['ENABLE_MONITORINGDASHBOARD']:
        sampledb.dashboard.init_app(app)

    app.register_blueprint(sampledb.api.server.api)
    app.register_blueprint(sampledb.api.federation.federation_api)

    app.register_blueprint(sampledb.frontend.frontend)

    login_manager.login_view = 'frontend.sign_in'
    login_manager.anonymous_user = sampledb.logic.users.AnonymousUser

    sampledb.logic.files.FILE_STORAGE_PATH = app.config['FILE_STORAGE_PATH']

    def custom_send_static_file(filename: str) -> flask.Response:
        response = flask.make_response(
            flask.send_from_directory(app.static_folder, filename)  # type: ignore
        )
        if 'v' in flask.request.args:
            # fingerprinted URLs for static files can be cached as immutable
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response

    app.send_static_file = custom_send_static_file  # type: ignore

    setup_database(app)
    setup_admin_account_from_config(app)
    setup_jinja_environment(app)
    if app.config['BUILD_TRANSLATIONS']:
        build_translations(app.config['PYBABEL_PATH'])

    if app.config['ENABLE_NUMERIC_TAGS'] is None:
        with app.app_context():
            # if ENABLE_NUMERIC_TAGS is not set explicitly, only enable numeric tags if they already exist
            app.config['ENABLE_NUMERIC_TAGS'] = sampledb.logic.utils.do_numeric_tags_exist()

    with app.app_context():
        sampledb.logic.utils.print_deprecation_warnings()

    if app.config['ENABLE_BACKGROUND_TASKS']:
        sampledb.logic.background_tasks.start_handler_threads(app)

    def signal_handler(sig: int, _: typing.Any) -> None:
        if sig == signal.SIGTERM:
            if app.config['ENABLE_BACKGROUND_TASKS']:
                sampledb.logic.background_tasks.stop_handler_threads(app)
            sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)

    return app
