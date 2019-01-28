# coding: utf-8
"""

"""

import flask
import flask_login

from .. import frontend
from ...logic.users import create_user
from ...logic.authentication import add_email_authentication
from ...logic.utils import send_confirm_email
from ...logic.security_tokens import verify_token

from ...models import Authentication, UserType

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
    # TODO: initial instrument permissions?
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
                # send confirm link
                send_confirm_email(invitation_form.email.data, None, 'invitation')
        else:
            has_error = True
        return flask.render_template('invitation.html', invitation_form=invitation_form, has_success=has_success,
                                     has_error=has_error)


def registration():
    token = flask.request.args.get('token')
    email = verify_token(token, salt='invitation', secret_key=flask.current_app.config['SECRET_KEY'])
    if email is None or '@' not in email:
        return flask.abort(404)
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
                flask.flash('Your registration was successful.', 'success')
                return flask.redirect(flask.url_for('frontend.index'))
            flask.flash('There already is an account with this email address. Please use this account or contact an administrator.', 'error')
            return flask.redirect(flask.url_for('frontend.sign_in'))
        else:
            return flask.render_template('registration.html', registration_form=registration_form, has_error=has_error)
