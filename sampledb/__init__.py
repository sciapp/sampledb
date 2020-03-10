
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


def create_app():
    app = flask.Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app)

    app.config.from_object(sampledb.config)

    sampledb.config.check_config(app.config)

    login_manager.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    sampledb.api.server.api.init_app(app)

    app.register_blueprint(sampledb.frontend.frontend)

    login_manager.login_view = 'frontend.sign_in'
    app.jinja_env.globals.update(
        jupyterhub_url=app.config['JUPYTERHUB_URL'],
        signout_form=sampledb.frontend.users_forms.SignoutForm,
        service_name=app.config['SERVICE_NAME'],
        service_description=app.config['SERVICE_DESCRIPTION'],
        service_imprint=app.config['SERVICE_IMPRINT'],
        service_privacy_policy=app.config['SERVICE_PRIVACY_POLICY'],
        ldap_name=app.config['LDAP_NAME'],
        contact_email=app.config['CONTACT_EMAIL']
    )
    app.jinja_env.filters.update(sampledb.frontend.utils.jinja_filter.filters)

    sampledb.logic.files.FILE_STORAGE_PATH = app.config['FILE_STORAGE_PATH']

    with app.app_context():
        db.metadata.create_all(bind=db.engine)
        sampledb.models.Objects.bind = db.engine
        sampledb.models.migrations.run(db)

    return app
