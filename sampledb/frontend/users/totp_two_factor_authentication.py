# coding: utf-8
"""

"""

import datetime

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms.fields import StringField
from wtforms.validators import InputRequired
import pyotp

from .. import frontend
from .authentication import complete_sign_in
from ...logic import errors, authentication
from ...logic.users import get_user
from ..utils import generate_qrcode


class TOTPForm(FlaskForm):
    code = StringField(validators=[InputRequired()])


@frontend.route('/users/me/two_factor_authentication/totp/setup', methods=['GET', 'POST'])
@flask_login.login_required
def setup_totp_two_factor_authentication():
    active_method = authentication.get_active_two_factor_authentication_method(flask_login.current_user.id)
    if active_method is not None:
        flask.flash(_('You cannot set up a new two factor authentication method while another is active.'), 'error')
        return flask.redirect(flask.url_for('.user_me_preferences'))
    setup_form = TOTPForm()
    email = flask_login.current_user.email
    service_name = flask.current_app.config['SERVICE_NAME']
    if setup_form.validate_on_submit() and 'totp_secret' in flask.session:
        secret = flask.session['totp_secret']
        if pyotp.TOTP(secret).verify(setup_form.code.data):
            flask.session.pop('totp_secret')
            method = authentication.create_totp_two_factor_authentication_method(flask_login.current_user.id, secret)
            authentication.activate_two_factor_authentication_method(method.id)
            flask.flash(_('Successfully set up two factor authentication.'), 'success')
            return flask.redirect(flask.url_for('.user_me_preferences'))
        else:
            flask.flash(_('The code was invalid, please try again.'), 'error')
    else:
        secret = pyotp.random_base32()
        flask.session['totp_secret'] = secret
    url = pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=service_name)
    qrcode_url = generate_qrcode(url, should_cache=False)
    return flask.render_template(
        'two_factor_authentication/set_up_totp.html',
        setup_form=setup_form,
        qrcode_url=qrcode_url
    ), 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }


@frontend.route('/users/me/two_factor_authentication/totp/confirm', methods=['GET', 'POST'])
def confirm_totp_two_factor_authentication():
    confirm_data = flask.session.get('confirm_data')
    if confirm_data is None:
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    try:
        expiration_datetime = datetime.datetime.strptime(confirm_data['expiration_datetime'], '%Y-%m-%d %H:%M:%S')
    except Exception:
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))
    if expiration_datetime < datetime.datetime.utcnow():
        flask.flash(_('This two factor authentication attempt has expired. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))
    try:
        user = get_user(confirm_data['user_id'])
    except errors.UserDoesNotExistError:
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))
    reason = confirm_data.get('reason')
    if reason not in (
        'login',
        'activate_two_factor_authentication_method',
        'deactivate_two_factor_authentication_method'
    ):
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if reason in ('login', ) and flask_login.current_user.is_authenticated:
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if reason in (
        'activate_two_factor_authentication_method',
        'deactivate_two_factor_authentication_method'
    ) and not flask_login.current_user.is_authenticated:
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if reason in (
        'login',
        'deactivate_two_factor_authentication_method'
    ):
        method = authentication.get_active_two_factor_authentication_method(user.id)
    else:
        all_methods = authentication.get_two_factor_authentication_methods(user.id)
        method = {
            method.id: method
            for method in all_methods
        }.get(confirm_data.get('method_id'))
        if method.active:
            method = None
    if method is None or method.id != confirm_data.get('method_id'):
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if method.data.get('type') != 'totp':
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if not method.data.get('secret'):
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    confirm_form = TOTPForm()
    if confirm_form.validate_on_submit():
        secret = method.data['secret']
        if pyotp.TOTP(secret).verify(confirm_form.code.data):
            flask.session.pop('confirm_data')
            if reason == 'login':
                return complete_sign_in(user, confirm_data.get('is_for_refresh'), confirm_data.get('remember_me'))
            elif reason == 'activate_two_factor_authentication_method':
                authentication.activate_two_factor_authentication_method(method.id)
                flask.flash(_('The two factor authentication method has been enabled.'), 'success')
                return flask.redirect(flask.url_for('.user_me_preferences'))
            elif reason == 'deactivate_two_factor_authentication_method':
                authentication.deactivate_two_factor_authentication_method(method.id)
                flask.flash(_('The two factor authentication method has been disabled.'), 'success')
                return flask.redirect(flask.url_for('.user_me_preferences'))
            else:
                return flask.abort(500)
        else:
            flask.flash(_('The code was invalid, please try again.'), 'error')
    return flask.render_template(
        'two_factor_authentication/confirm_totp.html',
        confirm_form=confirm_form,
        user=user,
        reason=reason
    )
