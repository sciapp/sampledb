
import flask
from werkzeug.contrib.fixers import ProxyFix
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

login_manager = LoginManager()
login_manager.session_protection = 'strong'

mail = Mail()
db = SQLAlchemy()

import sampledb.frontend
import sampledb.models


def create_app():
    app = flask.Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.config.from_object('sampledb.config')
    login_manager.init_app(app)
    mail.init_app(app)
    db.init_app(app)

    app.register_blueprint(sampledb.frontend.frontend)

    login_manager.login_view = 'frontend.sign_in'
    app.jinja_env.globals.update(signout_form=sampledb.frontend.users_forms.SignoutForm)
    app.jinja_env.filters.update(sampledb.frontend.utils.jinja_filter.filters)

    with app.app_context():
        db.metadata.create_all(bind=db.engine)
        sampledb.models.Objects.bind = db.engine

    return app
