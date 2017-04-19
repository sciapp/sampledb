# coding: utf-8
"""

"""

import flask
import flask_login

from sampledb.frontend import frontend
from sampledb.logic import user_log
from sampledb.logic.utils import send_confirm_email
from sampledb.logic.security_tokens import verify_token

from sampledb.frontend.users_forms import EmailPasswordForm, RequestPasswordResetForm, SigninForm, LoginPasswordForm
from sampledb.models import Authentication, AuthenticationType, User


@frontend.route('/users/password', methods=['GET', 'POST'])
def password_route():
    if 'token' in flask.request.args:
        return reset_password()
    else:
        return email_for_resetting_password()

def email_for_resetting_password():
    request_password_reset_form = RequestPasswordResetForm()
    if flask.request.method == "GET":
        #  GET (email dialog )
        return flask.render_template('reset_password_by_email.html',
                                     request_password_reset_form=request_password_reset_form)
    if flask.request.method == "POST":
        has_error = False
        if request_password_reset_form.validate_on_submit():
            email = request_password_reset_form.email.data
            if '@' not in email:
                has_error = True
            else:
                auth = Authentication.query.filter(Authentication.login['login'].astext == email).first()
                users = User.query.filter_by(email=str(email)).all()
                if auth is not None and len(users) > 0:
                    # send confirm link
                    send_confirm_email(request_password_reset_form.email.data, None, 'password')
                return flask.render_template('recovery_email_send.html',
                                             email=email, has_error=has_error)
        return flask.render_template('reset_password_by_email.html',
                                     request_password_reset_form=request_password_reset_form,
                                     has_error=has_error),


def reset_password():
    token = flask.request.args.get('token')
    email = verify_token(token, salt='password', secret_key=flask.current_app.config['SECRET_KEY'])
    print(email)
    if email is None or '@' not in email:
        return flask.abort(404)
    auth = Authentication.query.filter(Authentication.login['login'].astext == email).first()
    users = User.query.filter_by(email=str(email)).all()
    password_form = EmailPasswordForm()
    if password_form.email.data is None or password_form.email.data == "":
        password_form.email.data = email
    has_error = False
    authentication_email = None
    username = None
    print(flask.request.method)
    if flask.request.method == "GET":
        # confirmation dialog
        if auth is not None:
            authentication_email = email
        if len(users) != 0:
            for user in users:
                username = user.name
        if authentication_email is None and len(users) == 0:
            return flask.redirect(flask.url_for('.sign_in'))
        else:
            return flask.render_template('password.html', password_form=password_form, has_error=has_error,
                                         authentication_email=authentication_email, username=username)

    else:
        return flask.render_template('password.html', password_form=password_form, has_error=has_error, log=log)