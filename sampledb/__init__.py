import flask
from flask_babel import Babel
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
import os
import subprocess
from bs4 import BeautifulSoup
import json

login_manager = LoginManager()
login_manager.session_protection = 'basic'

mail = Mail()
db = SQLAlchemy()
babel = Babel()


import sampledb.frontend
import sampledb.api
import sampledb.logic
import sampledb.models
import sampledb.models.migrations
import sampledb.config


@babel.localeselector
def set_locale():
    if hasattr(flask.g, 'override_locale') and flask.g.override_locale in sampledb.logic.locale.get_allowed_language_codes():
        return flask.g.override_locale

    request_locale = sampledb.logic.locale.guess_request_locale()

    if not current_user or not current_user.is_authenticated:
        return request_locale

    auto_lc = sampledb.logic.settings.get_user_settings(current_user.id)['AUTO_LC']
    if auto_lc:
        return request_locale

    stored_locale = sampledb.logic.settings.get_user_settings(current_user.id)['LOCALE']
    if stored_locale in sampledb.logic.locale.get_allowed_language_codes():
        return stored_locale

    return request_locale


@babel.timezoneselector
def set_timezone():
    if current_user.is_authenticated:
        settings = sampledb.logic.settings.get_user_settings(current_user.id)
        if settings['AUTO_TZ']:
            return flask.request.args.get('timezone', settings['TIMEZONE'])
        return settings['TIMEZONE']
    return flask.request.args.get('timezone', None)


def setup_database(app):
    with app.app_context():
        db.metadata.create_all(bind=db.engine)
        sampledb.models.Objects.bind = db.engine
        sampledb.models.migrations.run(db)


def setup_admin_account_from_config(app):
    with app.app_context():
        if 'ADMIN_INFO' in app.config['internal'] and not sampledb.logic.users.get_users(exclude_hidden=False):
            admin_username, admin_email, admin_password = app.config['internal']['ADMIN_INFO']
            admin_user = sampledb.logic.users.create_user(
                admin_username,
                admin_email,
                sampledb.logic.users.UserType.PERSON
            )
            sampledb.logic.authentication.add_other_authentication(
                admin_user.id,
                admin_username,
                admin_password,
                confirmed=True
            )
            sampledb.logic.users.set_user_administrator(admin_user.id, True)


def setup_jinja_environment(app):
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
        service_imprint=app.config['SERVICE_IMPRINT'],
        service_privacy_policy=app.config['SERVICE_PRIVACY_POLICY'],
        ldap_name=app.config['LDAP_NAME'],
        is_ldap_configured=is_ldap_configured,
        get_action_types=sampledb.logic.actions.get_action_types,
        get_action_types_with_translations_in_language=sampledb.logic.action_type_translations.get_action_types_with_translations_in_language,
        get_translated_text=sampledb.logic.utils.get_translated_text,
        BeautifulSoup=BeautifulSoup,
        json=json,
        contact_email=app.config['CONTACT_EMAIL'],
        get_user_settings=lambda: sampledb.logic.settings.get_user_settings(current_user.id),
        TimezoneForm=sampledb.frontend.timezone.TimezoneForm,
        get_user_language=sampledb.logic.languages.get_user_language,
    )
    app.jinja_env.filters.update(sampledb.frontend.utils.jinja_filter.filters)
    app.jinja_env.globals.update(sampledb.frontend.utils._jinja_functions)


def build_translations(pybabel_path):
    translations_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'translations'))
    # merge extracted and manual message catalogs
    for translation_directory in os.listdir(translations_directory):
        translation_directory = os.path.join(translations_directory, translation_directory)
        extracted_message_catalog_path = os.path.join(translation_directory, 'LC_MESSAGES', 'extracted_messages.po')
        manual_message_catalog_path = os.path.join(translation_directory, 'LC_MESSAGES', 'manual_messages.po')
        merged_message_catalog_path = os.path.join(translation_directory, 'LC_MESSAGES', 'messages.po')
        if os.path.isfile(extracted_message_catalog_path) and os.path.isfile(manual_message_catalog_path):
            # manually merge instead of using msgcat to avoid duplicate headers
            with open(extracted_message_catalog_path, 'r', encoding='utf-8') as extracted_message_catalog:
                extracted_message_catalog = extracted_message_catalog.read()
            with open(manual_message_catalog_path, 'r', encoding='utf-8') as manual_message_catalog:
                manual_message_catalog = manual_message_catalog.read()
            with open(merged_message_catalog_path, 'w', encoding='utf-8') as merged_message_catalog:
                merged_message_catalog.write(extracted_message_catalog)
                merged_message_catalog.write(manual_message_catalog)
    # compile messages
    subprocess.run([pybabel_path, "compile", "-d", translations_directory], check=True)


def create_app():
    app = flask.Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app)

    app.config.from_object(sampledb.config)

    internal_config = sampledb.config.check_config(app.config)
    app.config['internal'] = internal_config

    login_manager.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    babel.init_app(app)
    sampledb.api.server.api.init_app(app)

    app.register_blueprint(sampledb.frontend.frontend)

    login_manager.login_view = 'frontend.sign_in'

    sampledb.logic.files.FILE_STORAGE_PATH = app.config['FILE_STORAGE_PATH']

    setup_database(app)
    setup_admin_account_from_config(app)
    setup_jinja_environment(app)
    if app.config['BUILD_TRANSLATIONS']:
        build_translations(app.config['PYBABEL_PATH'])

    return app
