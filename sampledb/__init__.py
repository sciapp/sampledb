from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

from flask_login import LoginManager

login_manager = LoginManager()
login_manager.session_protection = 'strong'

mail = Mail()
db = SQLAlchemy()

import sampledb.authentication


def create_app():
    app = Flask(__name__)
    app.config.from_object('config')
    login_manager.init_app(app)
    mail.init_app(app)
    db.init_app(app)

    with app.app_context():
        db.metadata.create_all(bind=db.engine)

    return app

app = create_app()

import sampledb.views

app.register_blueprint(sampledb.authentication.authentication)
