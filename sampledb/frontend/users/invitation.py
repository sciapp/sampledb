# coding: utf-8
"""

"""

import datetime

import flask
import flask_login
from flask_babel import _

from .. import frontend
from ...logic.users import create_user, get_user_invitation, set_user_invitation_accepted
from ...logic.authentication import add_email_authentication
from ...logic.utils import send_user_invitation_email
from ...logic.security_tokens import verify_token

from ...models import users
from ...models import Authentication, UserType

from ... import db

from ..users_forms import InvitationForm, RegistrationForm


@frontend.route('/users/invitation', methods=['GET', 'POST'])
def invitation_route():
    if flask_login.current_user.is_authenticated:
        return invitation()
    elif 'token' in flask.request.args:
        return registration()
    else:
        return flask.abort(403)


def invitation():
    invitation_form = InvitationForm()
    if flask.request.method == "GET":
        #  GET (invitation dialog )
        has_success = False
        return flask.render_template('invitation.html', invitation_form=invitation_form, has_success=has_success)
    if flask.request.method == "POST":
        # POST (send invitation)
        has_success = False
        has_error = False
        if invitation_form.validate_on_submit():
            email = invitation_form.email.data
            if '@' not in email:
                has_error = True
            else:
                has_success = True

                user_invitation = users.UserInvitation(
                    inviter_id=flask_login.current_user.id,
                    utc_datetime=datetime.datetime.utcnow()
                )
                db.session.add(user_invitation)
                db.session.commit()

                # send confirm link
                send_user_invitation_email(
                    email=email,
                    invitation_id=user_invitation.id
                )
        else:
            has_error = True
        return flask.render_template('invitation.html', invitation_form=invitation_form, has_success=has_success,
                                     has_error=has_error)


def registration():
    token = flask.request.args.get('token')
    expiration_time_limit = flask.current_app.config['INVITATION_TIME_LIMIT']
    token_data = verify_token(token, salt='invitation', secret_key=flask.current_app.config['SECRET_KEY'], expiration=expiration_time_limit)
    if token_data is None:
        flask.flash(_('Invalid invitation token. Please request a new invitation.'), 'error')
        return flask.abort(403)
    if isinstance(token_data, str):
        email = token_data
        invitation_id = None
    else:
        email = token_data['email']
        invitation_id = token_data['invitation_id']
        if get_user_invitation(invitation_id).accepted:
            flask.flash(_('This invitation token has already been used. Please request a new invitation.'), 'error')
            return flask.abort(403)
    registration_form = RegistrationForm()
    if registration_form.email.data is None or registration_form.email.data == "":
        registration_form.email.data = email
    has_error = False
    if flask.request.method == "GET":
        # confirmation dialog
        return flask.render_template('registration.html', registration_form=registration_form, has_error=has_error)
    if flask.request.method == "POST":
        # redirect or register user and redirect
        has_error = False
        if registration_form.email.data != email:
            has_error = True
            return flask.render_template('registration.html', registration_form=registration_form, has_error=has_error)
        if registration_form.validate_on_submit():
            name = registration_form.name.data
            password = registration_form.password.data
            # check, if email in authentication-method already exists
            authentication_method = Authentication.query.filter(Authentication.login['login'].astext == email).first()
            # no user with this name and contact email in db => add to db
            if authentication_method is None:
                user = create_user(name=name, email=email, type=UserType.PERSON)
                add_email_authentication(user.id, email, password)
                if invitation_id is not None:
                    set_user_invitation_accepted(invitation_id)
                flask.flash(_('Your account has been created successfully.'), 'success')
                flask_login.login_user(user)
                return flask.redirect(flask.url_for('frontend.index'))
            flask.flash(_('There already is an account with this email address. Please use that account or contact an administrator.'), 'error')
            return flask.redirect(flask.url_for('frontend.sign_in'))
        else:
            return flask.render_template('registration.html', registration_form=registration_form, has_error=has_error)
