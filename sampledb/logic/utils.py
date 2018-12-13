# coding: utf-8
"""

"""

import smtplib
import flask
import flask_mail
import flask_login
import typing

from .. import mail, db
from .security_tokens import generate_token
from ..models import Authentication, AuthenticationType, User
from .users import get_user
from . import groups
from . import projects


def send_confirm_email(email, id, salt):
    if id is None:
        route = "frontend.%s_route" % salt
        token = generate_token(email, salt=salt,
                               secret_key=flask.current_app.config['SECRET_KEY'])
        confirm_url = flask.url_for(route, token=token, _external=True)
    else:
        token = generate_token([email, id], salt=salt,
                               secret_key=flask.current_app.config['SECRET_KEY'])
        confirm_url = flask.url_for("frontend.user_preferences", user_id=id, token=token, _external=True)

    subject = "iffSamples Email Confirmation"
    html = flask.render_template('mails/email_confirmation.html', confirm_url=confirm_url)
    text = flask.render_template('mails/email_confirmation.txt', confirm_url=confirm_url)
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    try:
        mail.send(flask_mail.Message(
            subject,
            sender=flask.current_app.config['MAIL_SENDER'],
            recipients=[email],
            body=text,
            html=html
        ))
    except smtplib.SMTPRecipientsRefused:
        pass


def send_recovery_email(email):
    users = User.query.filter_by(email=email).all()
    email_authentication = Authentication.query.filter(db.and_(Authentication.login['login'].astext == email, Authentication.type == AuthenticationType.EMAIL)).first()
    if email_authentication is not None and email_authentication.user not in users:
        users.append(email_authentication.user)

    if not users:
        return

    password_reset_urls = {}
    for user in users:
        for authentication_method in user.authentication_methods:
            if authentication_method.type != AuthenticationType.LDAP:
                password_reset_urls[authentication_method] = build_confirm_url(authentication_method)

    subject = "iffSamples Account Recovery"
    html = flask.render_template('mails/account_recovery.html', email=email, users=users, password_reset_urls=password_reset_urls)
    text = flask.render_template('mails/account_recovery.txt', email=email, users=users, password_reset_urls=password_reset_urls)
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    try:
        mail.send(flask_mail.Message(
            subject,
            sender=flask.current_app.config['MAIL_SENDER'],
            recipients=[email],
            body=text,
            html=html
        ))
    except smtplib.SMTPRecipientsRefused:
        pass


def build_confirm_url(authentication_method, salt='password'):
    assert authentication_method.type != AuthenticationType.LDAP

    user_id = authentication_method.user_id
    token = generate_token(authentication_method.id, salt=salt,
                           secret_key=flask.current_app.config['SECRET_KEY'])
    return flask.url_for("frontend.user_preferences", user_id=user_id, token=token, _external=True)


def send_confirm_email_to_invite_user_to_group(group_id: int, user_id: int) -> None:
    user = get_user(user_id)
    group = groups.get_group(group_id)
    if user is None:
        return
    token_data = {
        'user_id': user.id,
        'group_id': group_id
    }
    token = generate_token(token_data, salt='invite_to_group',
                           secret_key=flask.current_app.config['SECRET_KEY'])

    confirm_url = flask.url_for("frontend.group", group_id=group.id, token=token, _external=True)

    subject = "iffSamples Group Invitation"
    html = flask.render_template('mails/invitation_to_group.html', invited_user_name=user.name, group=group, confirm_url=confirm_url)
    text = flask.render_template('mails/invitation_to_group.txt', invited_user_name=user.name, group=group, confirm_url=confirm_url)
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    try:
        mail.send(flask_mail.Message(
            subject,
            sender=flask.current_app.config['MAIL_SENDER'],
            recipients=[user.email],
            body=text,
            html=html
        ))
    except smtplib.SMTPRecipientsRefused:
        pass


def send_confirm_email_to_invite_user_to_project(project_id: int, user_id: int, other_project_ids: typing.Sequence[int]=()) -> None:
    user = get_user(user_id)
    project = projects.get_project(project_id)
    if user is None:
        return
    token_data = {
        'user_id': user.id,
        'project_id': project_id,
        'other_project_ids': other_project_ids
    }
    token = generate_token(token_data, salt='invite_to_project',
                           secret_key=flask.current_app.config['SECRET_KEY'])

    confirm_url = flask.url_for("frontend.project", project_id=project.id, token=token, _external=True)

    subject = "iffSamples Project Invitation"
    html = flask.render_template('mails/invitation_to_project.html', invited_user_name=user.name, project=project, confirm_url=confirm_url)
    text = flask.render_template('mails/invitation_to_project.txt', invited_user_name=user.name, project=project, confirm_url=confirm_url)
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    try:
        mail.send(flask_mail.Message(
            subject,
            sender=flask.current_app.config['MAIL_SENDER'],
            recipients=[user.email],
            body=text,
            html=html
        ))
    except smtplib.SMTPRecipientsRefused:
        pass
