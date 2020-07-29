
import flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

login_manager = LoginManager()
login_manager.session_protection = 'basic'

mail = Mail()
db = SQLAlchemy()

import sampledb.frontend
import sampledb.api
import sampledb.logic
import sampledb.models
import sampledb.models.migrations
import sampledb.config


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
        contact_email=app.config['CONTACT_EMAIL']
    )
    app.jinja_env.filters.update(sampledb.frontend.utils.jinja_filter.filters)


def create_app():
    app = flask.Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app)

    app.config.from_object(sampledb.config)

    internal_config = sampledb.config.check_config(app.config)
    app.config['internal'] = internal_config

    login_manager.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    sampledb.api.server.api.init_app(app)

    app.register_blueprint(sampledb.frontend.frontend)

    login_manager.login_view = 'frontend.sign_in'

    sampledb.logic.files.FILE_STORAGE_PATH = app.config['FILE_STORAGE_PATH']

    setup_database(app)
    setup_admin_account_from_config(app)
    setup_jinja_environment(app)

    return app
