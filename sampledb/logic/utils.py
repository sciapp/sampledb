# coding: utf-8
"""

"""

import flask
import flask_mail

from .. import mail
from .security_tokens import generate_token


def send_confirm_email(email,id,salt):
    token = generate_token([email, id], salt=salt,
                           secret_key=flask.current_app.config['SECRET_KEY'])
    subject = "Please confirm your email"
    confirm_url = flask.url_for(".confirm_email_without_form", token=token, salt=salt, _external=True)
    html = flask.render_template('activate.html', confirm_url=confirm_url)
    mail.send(flask_mail.Message(
        subject,
        sender=flask.current_app.config['MAIL_SENDER'],
        recipients=[email],
        html=html
    ))