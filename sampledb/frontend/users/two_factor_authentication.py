# coding: utf-8
"""

"""

import base64
import datetime
import json
import typing

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms.fields import StringField, HiddenField
from wtforms.validators import InputRequired
import pyotp
from fido2.webauthn import PublicKeyCredentialUserEntity, ResidentKeyRequirement, AttestedCredentialData

from .. import frontend
from .authentication import complete_sign_in
from ...logic import errors, authentication
from ...logic.users import get_user, User
from .forms import WebAuthnLoginForm
from ..utils import generate_qrcode
from ...utils import FlaskResponseT


class TOTPForm(FlaskForm):
    code = StringField(validators=[InputRequired()])
    description = StringField()


class WebauthnSetupForm(FlaskForm):
    fido2_passkey_credentials = HiddenField(validators=[InputRequired()])
    description = StringField(validators=[InputRequired()])


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
            flask.flash(_('Successfully set up two-factor authentication.'), 'success')
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


def _parse_confirm_data() -> typing.Optional[typing.Tuple[User, str, bool, bool, bool, typing.Optional[str]]]:
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
    return user, confirm_data.get('reason'), confirm_data.get('is_for_refresh'), confirm_data.get('remember_me'), confirm_data.get('shared_device'), confirm_data.get('next_url')


@frontend.route('/users/me/two_factor_authentication/totp/confirm', methods=['GET', 'POST'])
def confirm_totp_two_factor_authentication() -> FlaskResponseT:
    confirm_data = _parse_confirm_data()
    if confirm_data is None:
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    user, reason, is_for_refresh, remember_me, shared_device, next_url = confirm_data
    if reason not in (
        'login',
        'activate_two_factor_authentication_method',
        'deactivate_two_factor_authentication_method'
    ):
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if reason in ('login', ) and flask_login.current_user.is_authenticated != is_for_refresh:
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if reason in (
        'activate_two_factor_authentication_method',
        'deactivate_two_factor_authentication_method'
    ) and not flask_login.current_user.is_authenticated:
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
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
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
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
            flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
            flask.session.pop('confirm_data')
            return flask.redirect(flask.url_for('.index'))
        if not method_to_deactivate.active:
            flask.flash(_('The two-factor authentication method has already been disabled.'), 'success')
            return flask.redirect(flask.url_for('.user_me_preferences'))
    else:
        method_to_deactivate = None

    if method.data.get('type') != 'totp':
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if not method.data.get('secret'):
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    confirm_form = TOTPForm()
    if confirm_form.validate_on_submit():
        secret = method.data['secret']
        if pyotp.TOTP(secret).verify(confirm_form.code.data):
            flask.session.pop('confirm_data')
            if reason == 'login':
                return complete_sign_in(user, is_for_refresh, remember_me, shared_device, next_url=next_url)
            elif reason == 'activate_two_factor_authentication_method':
                authentication.activate_two_factor_authentication_method(method.id)
                flask.flash(_('The two-factor authentication method has been enabled.'), 'success')
                return flask.redirect(flask.url_for('.user_me_preferences'))
            elif reason == 'deactivate_two_factor_authentication_method':
                assert method_to_deactivate is not None
                authentication.deactivate_two_factor_authentication_method(method_to_deactivate.id)
                flask.flash(_('The two-factor authentication method has been disabled.'), 'success')
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


@frontend.route('/users/me/two_factor_authentication/fido2_passkey/setup', methods=['GET', 'POST'])
@flask_login.login_required
def setup_fido2_passkey_two_factor_authentication() -> FlaskResponseT:
    setup_form = WebauthnSetupForm()

    server = authentication.get_webauthn_server()
    options, state = server.register_begin(
        PublicKeyCredentialUserEntity(
            id=f"2fa-{flask_login.current_user.id}".encode('utf-8'),
            name=f"{flask_login.current_user.name} ({flask_login.current_user.email})",
            display_name=flask_login.current_user.name,
        ),
        credentials=authentication.get_all_two_factor_fido2_passkey_credentials_for_user(user_id=flask_login.current_user.id),
        resident_key_requirement=ResidentKeyRequirement.PREFERRED,
    )
    if setup_form.validate_on_submit():
        try:
            auth_data = server.register_complete(
                flask.session["webauthn_enroll_state"],
                json.loads(setup_form.fido2_passkey_credentials.data)
            )
            assert auth_data.credential_data is not None
            method = authentication.create_fido2_passkey_two_factor_authentication_method(
                user_id=flask_login.current_user.id,
                credential_data=auth_data.credential_data,
                description=setup_form.description.data
            )
            authentication.activate_two_factor_authentication_method(method.id)
            del flask.session["webauthn_enroll_state"]
            flask.flash(_('Successfully set up two-factor authentication.'), 'success')
        except Exception:
            flask.flash(_('Failed to set up two-factor authentication.'), 'error')
        return flask.redirect(flask.url_for('.user_me_preferences'))
    else:
        flask.session["webauthn_enroll_state"] = state

    return flask.render_template(
        'two_factor_authentication/set_up_fido2_passkey.html',
        setup_form=setup_form,
        options=options
    ), 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }


@frontend.route('/users/me/two_factor_authentication/fido2_passkey/confirm', methods=['GET', 'POST'])
def confirm_fido2_passkey_two_factor_authentication() -> FlaskResponseT:
    confirm_data = _parse_confirm_data()
    if confirm_data is None:
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    user, reason, is_for_refresh, remember_me, shared_device, next_url = confirm_data
    if reason not in (
        'login',
        'activate_two_factor_authentication_method',
        'deactivate_two_factor_authentication_method'
    ):
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if reason in ('login', ) and flask_login.current_user.is_authenticated != is_for_refresh:
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if reason in (
        'activate_two_factor_authentication_method',
        'deactivate_two_factor_authentication_method'
    ) and not flask_login.current_user.is_authenticated:
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
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
        method_id = int(int(flask.request.args.get('method_id', '')))
    except ValueError:
        method_id = -1
    method = {
        method.id: method
        for method in all_methods
    }.get(method_id)
    if method is None:
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
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
            flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
            flask.session.pop('confirm_data')
            return flask.redirect(flask.url_for('.index'))
        if not method_to_deactivate.active:
            flask.flash(_('The two-factor authentication method has already been disabled.'), 'success')
            return flask.redirect(flask.url_for('.user_me_preferences'))
    else:
        method_to_deactivate = None

    if method.data.get('type') != 'fido2_passkey':
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    if not method.data.get('credential_data'):
        flask.flash(_('This two-factor authentication attempt has failed. Please try again.'), 'error')
        flask.session.pop('confirm_data')
        return flask.redirect(flask.url_for('.index'))

    confirm_form = WebAuthnLoginForm()
    base64_credential_data = method.data['credential_data']
    credential_data = AttestedCredentialData(base64.b64decode(base64_credential_data.encode('utf-8')))
    all_credentials = [credential_data]
    server = authentication.get_webauthn_server()
    if confirm_form.validate_on_submit():
        credential = server.authenticate_complete(
            flask.session.pop("webauthn_state"),
            credentials=all_credentials,
            response=json.loads(confirm_form.assertion.data),
        )
        if credential.credential_id == credential_data.credential_id:
            flask.session.pop('confirm_data')
            if reason == 'login':
                return complete_sign_in(user, is_for_refresh, remember_me, shared_device, next_url=next_url)
            elif reason == 'activate_two_factor_authentication_method':
                authentication.activate_two_factor_authentication_method(method.id)
                flask.flash(_('The two-factor authentication method has been enabled.'), 'success')
                return flask.redirect(flask.url_for('.user_me_preferences'))
            elif reason == 'deactivate_two_factor_authentication_method':
                assert method_to_deactivate is not None
                authentication.deactivate_two_factor_authentication_method(method_to_deactivate.id)
                flask.flash(_('The two-factor authentication method has been disabled.'), 'success')
                return flask.redirect(flask.url_for('.user_me_preferences'))
            else:
                return flask.abort(500)
        else:
            flask.flash(_('The passkey does not match the one stored for this two-factor authentication method, please try again.'), 'error')

    options, state = server.authenticate_begin(
        credentials=all_credentials
    )
    flask.session["webauthn_state"] = state
    return flask.render_template(
        'two_factor_authentication/confirm_fido2_passkey.html',
        confirm_form=confirm_form,
        options=options,
        method_id=method_id,
        user=user,
        description=method.data.get('description'),
        reason=reason,
        method_to_deactivate=method_to_deactivate,
    )
