# coding: utf-8
"""

"""

import smtplib
import flask
import flask_mail

from .. import mail
from .security_tokens import generate_token
from ..models import Authentication


def send_confirm_email(email, id, salt):
    if id == None:
        route = "frontend.%s_route" % salt
        token = generate_token(email, salt=salt,
                               secret_key=flask.current_app.config['SECRET_KEY'])
        confirm_url = flask.url_for(route, token=token, _external=True)
    else:
        token = generate_token([email, id], salt=salt,
                               secret_key=flask.current_app.config['SECRET_KEY'])
        confirm_url = flask.url_for("frontend.user_preferences", user_id=id, token=token, _external=True)

    subject = "Please confirm your email"
    html = flask.render_template('activate.html', confirm_url=confirm_url)
    try:
        mail.send(flask_mail.Message(
            subject,
            sender=flask.current_app.config['MAIL_SENDER'],
            recipients=[email],
            html=html
        ))
    except smtplib.SMTPRecipientsRefused:
        pass


def send_recovery_email(email, users, salt):
    datalist = []
    if users is None or len(users) == 0:
        return False
    if salt is None or salt != "password":
        return False
    if email is None or email == '':
        return False
    if len(users) > 1:
        for user in users:
            id = user.id
            authentication_methods = Authentication.query.filter(Authentication.user_id == id).all()
            if authentication_methods is not None:
                for authentication_method in authentication_methods:
                    data = build_confirm_url(authentication_method, email, salt)
                    if data:
                        datalist.append(data)
    else:
        id = users[0].id
        authentication_methods = Authentication.query.filter(Authentication.user_id == id).all()
        if authentication_methods is not None:
            for authentication_method in authentication_methods:
                data = build_confirm_url(authentication_method, email, salt)
                if data:
                    datalist.append(data)
    subject = "Recovery email"
    html = flask.render_template('recovery_information.html', email=email, datalist=datalist)
    try:
        mail.send(flask_mail.Message(
            subject,
            sender=flask.current_app.config['MAIL_SENDER'],
            recipients=[email],
            html=html
        ))
    except smtplib.SMTPRecipientsRefused:
        pass
    return True

def build_confirm_url(authentication_method, email, salt):
    data = {}
    if email is None or email == "":
        return False
    if salt is None or salt != "password":
        return False
    if authentication_method:
        authentication_id = authentication_method.id
        id = authentication_method.user_id
        data['type'] = authentication_method.type.name
        data['login'] = authentication_method.login['login']
        if data['type'] != 'LDAP':
            token = generate_token([email, authentication_id, id], salt=salt,
                                   secret_key=flask.current_app.config['SECRET_KEY'])
            confirm_url = flask.url_for("frontend.user_preferences", user_id=id, token=token, _external=True)
            data['confirm_url'] = confirm_url
        else:
            data['confirm_url'] = None
        return data
    else:
        return False