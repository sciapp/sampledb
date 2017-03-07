from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

login_manager = LoginManager()
login_manager.session_protection = 'strong'

mail = Mail()
db = SQLAlchemy()

import sampledb.authentication
import sampledb.object_database
import sampledb.main
import sampledb.instruments
import sampledb.permissions


def create_app():
    app = Flask(__name__)
    app.config.from_object('config')
    login_manager.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    app.register_blueprint(sampledb.main.main_blueprint)
    app.register_blueprint(sampledb.authentication.authentication_blueprint)
    app.register_blueprint(sampledb.object_database.object_api, url_prefix='/objects')
    app.register_blueprint(sampledb.permissions.permissions_api, url_prefix='/objects')
    app.register_blueprint(sampledb.instruments.instrument_api)

    with app.app_context():
        db.metadata.create_all(bind=db.engine)

        sampledb.object_database.Objects.bind = db.engine

    return app
