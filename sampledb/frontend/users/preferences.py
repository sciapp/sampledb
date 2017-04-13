# coding: utf-8
"""

"""

import flask
import flask_login

from sampledb import db

from sampledb.frontend import frontend
from sampledb.logic import user_log
from sampledb.frontend.authentication_forms import ChangeUserForm, AuthenticationForm, AuthenticationMethodForm
from sampledb.logic.authentication import login, add_login, remove_authentication_method
from sampledb.logic.utils import send_confirm_email
from sampledb.logic.security_tokens import verify_token

from sampledb.models import Authentication, AuthenticationType, User


@frontend.route('/users/me/preferences', methods=['GET', 'POST'])
@flask_login.login_required
def user_me_preferences():
    return flask.redirect(flask.url_for('.user_preferences', user_id=flask_login.current_user.id))


@frontend.route('/users/<int:user_id>/preferences', methods=['GET', 'POST'])
@flask_login.login_required
def user_preferences(user_id=None):
    if user_id is None:
        return flask.redirect(flask.url_for('.user_preferences', user_id=flask_login.current_user.id))
    if user_id != flask_login.current_user.id:
        user = User.query.filter_by(id=user_id).first()
        return flask.abort(403)
    else:
        user = flask_login.current_user
    authentication_methods = Authentication.query.filter(Authentication.user_id == user_id).all()
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
                return flask.render_template('preferences.html', user=user, change_user_form=change_user_form,
                                             authentication_method_form=authentication_method_form,
                                             authentication_form=authentication_form,
                                             authentications=authentication_methods, error=str(e))
            user_log.edit_user_preferences(user_id=user_id)
            authentication_methods = Authentication.query.filter(Authentication.user_id == user_id).all()
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
                                             authentications=authentication_methods, error_add=str(e))
            authentication_methods = Authentication.query.filter(Authentication.user_id == user_id).all()
    return flask.render_template('preferences.html', user=user, change_user_form=change_user_form, authentication_method_form=authentication_method_form,
                                 authentication_form=authentication_form, authentications=authentication_methods)


@frontend.route('/users/confirm-email', methods=['GET'])
def confirm_email():
    salt = flask.request.args.get('salt')
    token = flask.request.args.get('token')
    data = verify_token(token, salt=salt, secret_key=flask.current_app.config['SECRET_KEY'])
    if data is None:
        return flask.abort(404)
    else:
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
