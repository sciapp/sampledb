from flask import Flask
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message

#from flask.ext.login import LoginManager

#login_manager = LoginManager()
#login_manager.session_protection = 'strong'
#login_manager.login_view = 'login'

demo = Flask(__name__)
demo.config.from_object('config')
#login_manager.init_app(demo)

demo.config.update(
MAIL_SERVER='mail.fz-juelich.de',
MAIL_PORT=25
)

mail = Mail(demo)
db = SQLAlchemy(demo)
bcrypt = Bcrypt(demo)

from demo import models, views

with demo.app_context():
    #db.engine.echo=True
    #db.metadata.drop_all(bind=db.engine)
    db.metadata.create_all(bind=db.engine)
