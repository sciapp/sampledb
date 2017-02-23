from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

from flask_login import LoginManager

login_manager = LoginManager()
login_manager.session_protection = 'strong'

mail = Mail()
db = SQLAlchemy()

import sampledb.authentication
import sampledb.object_database.object_api


def create_app():
    app = Flask(__name__)
    app.config.from_object('config')
    login_manager.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    app.register_blueprint(sampledb.authentication.authentication)
    app.register_blueprint(sampledb.object_database.object_api.object_api, url_prefix='/objects')

    with app.app_context():
        db.metadata.create_all(bind=db.engine)

        sampledb.object_database.object_api.Objects.bind = db.engine
        # create the object tables
        sampledb.object_database.object_api.Objects.metadata.create_all(db.engine)

    return app

app = create_app()

import sampledb.views
