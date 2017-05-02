# coding: utf-8
"""

"""

import flask
import flask_login
import bcrypt

from sampledb import db

from sampledb.frontend import frontend
from sampledb.logic import user_log
from sampledb.frontend.authentication_forms import ChangeUserForm, AuthenticationForm, AuthenticationMethodForm
from sampledb.frontend.users_forms import RequestPasswordResetForm, PasswordForm
from sampledb.logic.authentication import login, add_login, remove_authentication_method
from sampledb.logic.utils import send_confirm_email, send_recovery_email
from sampledb.logic.security_tokens import verify_token

from sampledb.models import Authentication, AuthenticationType, User


@frontend.route('/users/me/preferences', methods=['GET', 'POST'])
def user_me_preferences():
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for('.user_preferences', user_id=flask_login.current_user.id))
    return email_for_resetting_password()


@frontend.route('/users/<int:user_id>/preferences', methods=['GET', 'POST'])
def user_preferences(user_id):
    if 'token' in flask.request.args:
        token = flask.request.args.get('token')
        data = verify_token(token, salt='password', secret_key=flask.current_app.config['SECRET_KEY'])
        if data is not None:
            return reset_password()
        else:
            # es ist egal, ob eingeloggt oder nicht
            return confirm_email()
    elif flask_login.current_user.is_authenticated:
        if user_id != flask_login.current_user.id:
            return flask.abort(403)
        else:
            # user eingeloggt, change preferences möglich
            user = flask_login.current_user
            return change_preferences(user, user_id)
    else:
        return flask.redirect(flask.url_for('frontend.index'))


def change_preferences(user, user_id):
    authentication_methods = Authentication.query.filter(Authentication.user_id == user_id).all()
    confirmed_authentication_methods = Authentication.query.filter(Authentication.user_id == user_id, Authentication.confirmed==True).count()
    change_user_form = ChangeUserForm()
    authentication_form = AuthenticationForm()
    authentication_method_form = AuthenticationMethodForm()
    if change_user_form.name.data is None or change_user_form.name.data == "":
        change_user_form.name.data = user.name
    if change_user_form.email.data is None or change_user_form.email.data == "":
        change_user_form.email.data = user.email
    if 'change' in flask.request.form and flask.request.form['change'] == 'Change':
        if change_user_form.validate_on_submit():
            if change_user_form.name.data != user.name:
                u = user
                u.name = str(change_user_form.name.data)
                db.session.add(u)
                db.session.commit()
                user_log.edit_user_preferences(user_id=user_id)
            if change_user_form.email.data != user.email:
                # send confirm link
                send_confirm_email(change_user_form.email.data, user.id, 'edit_profile')
            return flask.redirect(flask.url_for('frontend.index'))
    if 'remove' in flask.request.form and flask.request.form['remove'] == 'Remove':
        authentication_method_id = authentication_method_form.id.data
        if authentication_method_form.validate_on_submit():
            try:
                remove_authentication_method(user_id, authentication_method_id)
            except Exception as e:
                flask.flash("Failed to remove the authentication method.", 'error')
                return flask.render_template('preferences.html', user=user, change_user_form=change_user_form,
                                             authentication_method_form=authentication_method_form,
                                             authentication_form=authentication_form,
                                             confirmed_authentication_methods=confirmed_authentication_methods,
                                             authentications=authentication_methods, error=str(e))
            user_log.edit_user_preferences(user_id=user_id)
            return flask.redirect(flask.url_for('frontend.user_me_preferences'))
    if 'add' in flask.request.form and flask.request.form['add'] == 'Add':
        if authentication_form.validate_on_submit():
            # check, if login already exists
            all_authentication_methods = {
                'E': AuthenticationType.EMAIL,
                'L': AuthenticationType.LDAP,
                'O': AuthenticationType.OTHER
            }
            if authentication_form.authentication_method.data not in all_authentication_methods:
                return flask.abort(400)

            authentication_method = all_authentication_methods[authentication_form.authentication_method.data]
            # check, if additional authentication is correct
            try:
                add_login(user_id, authentication_form.login.data, authentication_form.password.data, authentication_method)
            except Exception as e:
                return flask.render_template('preferences.html', user=user, change_user_form=change_user_form,
                                             authentication_method_form=authentication_method_form,
                                             authentication_form=authentication_form,
                                             confirmed_authentication_methods=confirmed_authentication_methods,
                                             authentications=authentication_methods, error_add=str(e))
            authentication_methods = Authentication.query.filter(Authentication.user_id == user_id).all()
    return flask.render_template('preferences.html', user=user, change_user_form=change_user_form,
                                 authentication_method_form=authentication_method_form,
                                 authentication_form=authentication_form,
                                 confirmed_authentication_methods=confirmed_authentication_methods,
                                 authentications=authentication_methods)


def confirm_email():
    token = flask.request.args.get('token')
    data1 = verify_token(token, salt='edit_profile', secret_key=flask.current_app.config['SECRET_KEY'])
    data2 = verify_token(token, salt='add_login', secret_key=flask.current_app.config['SECRET_KEY'])
    if data1 is None and data2 is None:
        return flask.abort(404)
    else:
        if data1 is not None:
            data = data1
            salt = 'edit_profile'
        if data2 is not None:
            data = data2
            salt = 'add_login'
        if len(data) != 2:
            return flask.abort(400)
        email = data[0]
        user_id = data[1]
        if salt == 'edit_profile':
            user = User.query.get(user_id)
            user.email = email
            db.session.add(user)
        elif salt == 'add_login':
            auth = Authentication.query.filter(Authentication.user_id == user_id,
                                               Authentication.login['login'].astext == email).first()
            auth.confirmed = True
            db.session.add(auth)
        else:
            return flask.abort(400)
        db.session.commit()
        user_log.edit_user_preferences(user_id=user_id)
        return flask.redirect(flask.url_for('.user_preferences', user_id=user_id))


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
                userlist = []
                if auth is not None:
                    user = User.query.filter_by(email=str(email), id=auth.user.id).first()
                    if user is None:
                        userlist.append(auth.user)
                if len(users) >0:
                    for user in users:
                        userlist.append(user)
                    # send recovery link of all userids with this email
                send_recovery_email(email, userlist, 'password')
                return flask.render_template('recovery_email_send.html',
                                             email=email, has_error=has_error)
        return flask.render_template('reset_password_by_email.html',
                                     request_password_reset_form=request_password_reset_form,
                                     has_error=has_error),


def reset_password():
    token = flask.request.args.get('token')
    data = verify_token(token, salt='password', secret_key=flask.current_app.config['SECRET_KEY'])
    email = data[0]
    authentication_id = data[1]
    userid = data[2]
    if not userid or not authentication_id:
        return flask.abort(404)
    if email is None or '@' not in email:
        return flask.abort(404)
    authentication_method = Authentication.query.filter(Authentication.id == authentication_id,
                                         Authentication.user_id == userid).first()
    password_form = PasswordForm()
    has_error = False
    if authentication_method is None:
        return flask.abort(404)
    username = authentication_method.login['login']
    if flask.request.method == "GET":
        # confirmation dialog
        return flask.render_template('password.html', password_form=password_form, has_error=has_error,
                                     email=email, username=username)
    else:
        if password_form.validate_on_submit():
            pw_hash = bcrypt.hashpw(password_form.password.data.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            authentication_method.login = {'login': username, 'bcrypt_hash': pw_hash}
            db.session.add(authentication_method)
            db.session.commit()
            return flask.redirect(flask.url_for('frontend.index'))
        return flask.render_template('password.html', password_form=password_form, has_error=has_error)