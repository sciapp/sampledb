# coding: utf-8
"""

"""

import datetime
import typing

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
from ...logic.users import get_user, User
from ..utils import generate_qrcode
from ...utils import FlaskResponseT


class TOTPForm(FlaskForm):
    code = StringField(validators=[InputRequired()])
    description = StringField()


@frontend.route('/users/me/two_factor_authentication/totp/setup', methods=['GET', 'POST'])
@flask_login.login_required
def setup_totp_two_factor_authentication() -> FlaskResponseT:
    setup_form = TOTPForm()
    email = flask_login.current_user.email
    service_name = flask.current_app.config['SERVICE_NAME']
    if setup_form.validate_on_submit() and 'totp_secret' in flask.session:
        secret = flask.session['totp_secret']
        if pyotp.TOTP(secret).verify(setup_form.code.data):
            flask.session.pop('totp_secret')
            method = authentication.create_totp_two_factor_authentication_method(flask_login.current_user.id, secret, setup_form.description.data)
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
        qrcode_url=qrcode_url,
        secret=secret
    ), 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }


def _parse_confirm_data() -> typing.Optional[typing.Tuple[User, str, bool, bool]]:
    confirm_data = flask.session.get('confirm_data')
    if confirm_data is None:
        return None
    try:
        expiration_datetime = datetime.datetime.strptime(confirm_data['expiration_datetime'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
    except Exception:
        flask.session.pop('confirm_data')
        return None
    if expiration_datetime < datetime.datetime.now(datetime.timezone.utc):
        flask.session.pop('confirm_data')
        return None
    try:
        user = get_user(confirm_data['user_id'])
    except errors.UserDoesNotExistError:
        flask.session.pop('confirm_data')
        return None
    return user, confirm_data.get('reason'), confirm_data.get('is_for_refresh'), confirm_data.get('remember_me')


@frontend.route('/users/me/two_factor_authentication/totp/confirm', methods=['GET', 'POST'])
def confirm_totp_two_factor_authentication() -> FlaskResponseT:
    confirm_data = _parse_confirm_data()
    if confirm_data is None:
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    user, reason, is_for_refresh, remember_me = confirm_data
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

    all_methods = authentication.get_two_factor_authentication_methods(
        user_id=user.id,
        active=reason in (
            'login',
            'deactivate_two_factor_authentication_method'
        )
    )
    try:
        method_id = int(flask.request.args.get('method_id', ''))
    except ValueError:
        method_id = -1
    method = {
        method.id: method
        for method in all_methods
    }.get(method_id)
    if method is None:
        flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if reason in (
        'deactivate_two_factor_authentication_method',
    ):
        method_to_deactivate_id = flask.session['confirm_data']['method_to_deactivate_id']
        method_to_deactivate = {
            method.id: method
            for method in all_methods
        }.get(method_to_deactivate_id)
        if method_to_deactivate is None:
            flask.flash(_('This two factor authentication attempt has failed. Please try again.'), 'error')
            flask.session.pop('confirm_data')
            return flask.redirect(flask.url_for('.index'))
        if not method_to_deactivate.active:
            flask.flash(_('The two factor authentication method has already been disabled.'), 'success')
            return flask.redirect(flask.url_for('.user_me_preferences'))
    else:
        method_to_deactivate = None

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
                return complete_sign_in(user, is_for_refresh, remember_me)
            elif reason == 'activate_two_factor_authentication_method':
                authentication.activate_two_factor_authentication_method(method.id)
                flask.flash(_('The two factor authentication method has been enabled.'), 'success')
                return flask.redirect(flask.url_for('.user_me_preferences'))
            elif reason == 'deactivate_two_factor_authentication_method':
                assert method_to_deactivate is not None
                authentication.deactivate_two_factor_authentication_method(method_to_deactivate.id)
                flask.flash(_('The two factor authentication method has been disabled.'), 'success')
                return flask.redirect(flask.url_for('.user_me_preferences'))
            else:
                return flask.abort(500)
        else:
            flask.flash(_('The code was invalid, please try again.'), 'error')
    return flask.render_template(
        'two_factor_authentication/confirm_totp.html',
        confirm_form=confirm_form,
        method_id=method_id,
        user=user,
        description=method.data.get('description'),
        reason=reason,
        method_to_deactivate=method_to_deactivate
    )
