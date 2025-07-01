# coding: utf-8
"""

"""

import datetime
import json
import typing

import itsdangerous
import flask
import flask_login
from flask_babel import _, lazy_gettext, refresh
from fido2.webauthn import UserVerificationRequirement
import werkzeug.wrappers.response

from .. import frontend
from ...logic import oidc
from ...logic.authentication import login, get_active_two_factor_authentication_methods, get_all_fido2_passkey_credentials, get_user_id_for_fido2_passkey_credential_id, get_webauthn_server
from ...logic.users import get_user, User, create_sampledb_federated_identity, get_federated_identity, enable_federated_identity_for_login
from ...logic.components import get_component, get_federated_login_components
from ...logic.errors import FederatedUserInFederatedIdentityError, UserDoesNotExistError, FederatedIdentityNotFoundError
from ..users_forms import SigninForm, SignoutForm
from .forms import WebAuthnLoginForm
from ... import login_manager
from ...utils import FlaskResponseT


@login_manager.user_loader
def load_user(user_id: typing.Any) -> typing.Optional[User]:
    flask.g.shared_device_state = False
    if flask.session.get('using_shared_device') and flask.request.cookies.get('SAMPLEDB_LAST_ACTIVITY_DATETIME'):
        try:
            millisecond_offset = float(flask.request.cookies.get('SAMPLEDB_LAST_ACTIVITY_MILLISECOND_OFFSET', '0'))
        except Exception:
            millisecond_offset = 0
        offset = datetime.timedelta(milliseconds=millisecond_offset)
        try:
            last_activity_datetime = datetime.datetime.strptime(flask.request.cookies['SAMPLEDB_LAST_ACTIVITY_DATETIME'], '%Y-%m-%dT%H:%M:%S')
        except Exception:
            flask.g.shared_device_state = True
        else:
            idle_sign_out_minutes = flask.current_app.config['SHARED_DEVICE_SIGN_OUT_MINUTES']
            idle_minutes = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + offset - last_activity_datetime).total_seconds() / 60 - 5 / 60
            flask.g.shared_device_state = idle_minutes < idle_sign_out_minutes
            if idle_minutes >= idle_sign_out_minutes:
                flask.session.clear()
                if user_id:
                    flask.flash(_('You have been signed out after %(idle_sign_out_minutes)s minutes of inactivity.', idle_sign_out_minutes=idle_sign_out_minutes), 'info')
                return None
    try:
        user_id = int(user_id)
    except ValueError:
        return None
    user = get_user(user_id)
    if not user.is_active:
        flask.flash(_('Your user account has been deactivated. Please contact an administrator.'), 'error')
        return None
    return user


def _is_url_safe_for_redirect(url: str) -> bool:
    """
    Checks whether a URL is safe for redirecting a user to it.

    URLs are deemed safe if they are absolute URLs on the current domain and
    server path. This is enforced by only allowing URLs that start with the
    absolute server path and only consist of alphanumerical characters or the
    following characters: /=?&_.,+-

    :param url: the URL to check
    :return: whether it is safe to redirect to or not
    """
    server_path = flask.current_app.config.get('SERVER_PATH', '/')
    # ensure the server path starts with a / to avoid relative paths or non-local paths
    if not server_path.startswith('/'):
        server_path = '/' + server_path
    # ensure the server path ends with a / to avoid paths with it as a prefix
    if not server_path.endswith('/'):
        server_path = server_path + '/'
    # prevent double slashes that would change the domain
    if url.startswith('//'):
        return False
    return url.startswith(server_path) and all(c in '/=?&_.,+-%' or c.isalnum() for c in url)


def _redirect_to_next_url(
        next_url: typing.Optional[str] = None
) -> werkzeug.wrappers.response.Response:
    if next_url is None:
        next_url = flask.request.args.get('next', flask.url_for('.index'))
    index_url = flask.url_for('.index')
    if not _is_url_safe_for_redirect(next_url):
        next_url = index_url
    return flask.redirect(next_url)


def _sign_in_impl(is_for_refresh: bool) -> FlaskResponseT:
    if oidc.is_oidc_only_auth_method():
        return flask.redirect(flask.url_for(
            'frontend.oidc_start',
            next=flask.request.args.get('next', '/'),
        ))

    form = SigninForm()
    passkey_form = WebAuthnLoginForm()
    all_credentials = get_all_fido2_passkey_credentials()
    server = get_webauthn_server()

    has_errors = False
    federated_login_token = flask.request.args.get('federated_login_token', None)
    if form.validate_on_submit():
        username = form.username.data
        # enforce lowercase for username to ensure case insensitivity
        # TODO: move this to the model and logic layer
        username = username.lower()
        password = form.password.data
        user = login(username, password)
        if user:
            if not user.is_active:
                flask_login.logout_user()
                flask.flash(_('Your user account has been deactivated. Please contact an administrator.'), 'error')
                return flask.redirect(flask.url_for('frontend.sign_in'))
            if is_for_refresh and user != flask_login.current_user:
                user = None
        if user:
            if not is_for_refresh:
                if user.is_admin and password == 'password':
                    flask.flash(
                        lazy_gettext(
                            'You are using the default admin password from the '
                            'SampleDB documentation. Please change your password '
                            'before making this SampleDB instance available to '
                            'other users.'
                        ),
                        'warning'
                    )
            two_factor_authentication_methods = get_active_two_factor_authentication_methods(user.id)
            if not two_factor_authentication_methods:
                return complete_sign_in(user, is_for_refresh, form.remember_me.data, form.shared_device.data, federated_login_token=federated_login_token)
            flask.session['confirm_data'] = {
                'reason': 'login',
                'user_id': user.id,
                'is_for_refresh': is_for_refresh,
                'remember_me': form.remember_me.data,
                'shared_device': form.shared_device.data,
                'expiration_datetime': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S'),
                'next_url': flask.request.args.get('next', '/')
            }
            if len(two_factor_authentication_methods) == 1:
                two_factor_authentication_method = two_factor_authentication_methods[0]
                if two_factor_authentication_method.data.get('type') == 'totp':
                    return flask.redirect(flask.url_for('.confirm_totp_two_factor_authentication', method_id=two_factor_authentication_method.id))
                if two_factor_authentication_method.data.get('type') == 'fido2_passkey':
                    return flask.redirect(flask.url_for('.confirm_fido2_passkey_two_factor_authentication', method_id=two_factor_authentication_method.id))
                del flask.session['confirm_data']
                return flask.render_template('two_factor_authentication/unsupported_method.html')
            return flask.render_template(
                'two_factor_authentication/pick.html',
                methods=two_factor_authentication_methods,
            )
        has_errors = True
    elif form.errors:
        has_errors = True
    if passkey_form.validate_on_submit() and flask.current_app.config['ENABLE_FIDO2_PASSKEY_AUTHENTICATION']:
        try:
            credential = server.authenticate_complete(
                flask.session.pop("webauthn_state"),
                credentials=all_credentials,
                response=json.loads(passkey_form.assertion.data),
            )
            user_id = get_user_id_for_fido2_passkey_credential_id(credential.credential_id)
        except Exception:
            user_id = None
        if user_id is not None:
            user = get_user(user_id)
            return complete_sign_in(user, is_for_refresh, passkey_form.remember_me.data, passkey_form.shared_device.data, federated_login_token=federated_login_token)
        flask.flash(_('No user was found for this passkey.'), 'error')
        return flask.redirect(flask.url_for('frontend.sign_in'))

    options, state = server.authenticate_begin(
        credentials=all_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    flask.session["webauthn_state"] = state

    federated_logins = get_federated_login_components() if 'federated_login_token' not in flask.request.args else []

    return flask.render_template(
        'sign_in.html',
        form=form,
        is_for_refresh=is_for_refresh,
        has_errors=has_errors,
        passkey_form=passkey_form,
        components=federated_logins,
        options=options,
        saml_user_creation=False,
        federated_login_authentication=bool(flask.session.get('SAMLRequest', None)),
    )


def complete_sign_in(
        user: typing.Optional[User],
        is_for_refresh: bool,
        remember_me: bool,
        shared_device: bool,
        *,
        next_url: typing.Optional[str] = None,
        federated_login_token: typing.Optional[str] = None,
        oidc_id_token_hint: typing.Optional[str] = None,
) -> FlaskResponseT:
    if not user:
        flask.flash(_('Please sign in again.'), 'error')
        flask_login.logout_user()
        return flask.redirect(flask.url_for('.index'))
    if federated_login_token:
        serializer = itsdangerous.URLSafeTimedSerializer(secret_key=flask.current_app.config['SECRET_KEY'], salt='federated-identities')
        try:
            federated_user_id, component_id = serializer.loads(federated_login_token, max_age=150)
        except itsdangerous.BadSignature:
            flask.flash(_('The federated login token expired. No federated identity link was created.'), 'error')

        component = get_component(component_id)
        try:
            identity = get_federated_identity(user_id=user.id, eln_or_fed_user_id=get_user(federated_user_id, component_id).id)
        except (UserDoesNotExistError, FederatedIdentityNotFoundError):
            identity = None

        try:
            if identity is not None and identity.active:
                enable_federated_identity_for_login(identity)
            else:
                create_sampledb_federated_identity(user.id, component=component, fed_id=federated_user_id, update_if_inactive=True, use_for_login=True)
        except FederatedUserInFederatedIdentityError:
            flask.flash(_('The federated user already has a federated identity with a different user.'), 'error')
    if is_for_refresh:
        flask_login.confirm_login()
    else:
        flask_login.login_user(user, remember=remember_me)
        refresh()
    flask.session['using_shared_device'] = shared_device
    if oidc_id_token_hint:
        flask.session['oidc_id_token_hint'] = oidc_id_token_hint
    else:
        flask.session.pop('oidc_id_token_hint', None)
    response = _redirect_to_next_url(next_url)
    response.set_cookie('SAMPLEDB_LAST_ACTIVITY_DATETIME', '', samesite='Lax')
    return response


@frontend.route('/users/me/sign_in', methods=['GET', 'POST'])
def sign_in() -> FlaskResponseT:
    if flask_login.current_user.is_authenticated:
        # if the user was already authenticated, redirect to the index.
        return flask.redirect(flask.url_for('.index'))
    return _sign_in_impl(is_for_refresh=False)


@frontend.route('/users/me/refresh_sign_in', methods=['GET', 'POST'])
@flask_login.login_required
def refresh_sign_in() -> FlaskResponseT:
    if flask_login.current_user.is_authenticated and flask_login.login_fresh():
        # if the login was already fresh, redirect to the next_url or index.
        return _redirect_to_next_url()
    return _sign_in_impl(is_for_refresh=True)


@frontend.route('/users/me/sign_out', methods=['GET', 'POST'])
@flask_login.login_required
def sign_out() -> FlaskResponseT:
    form = SignoutForm()
    if form.validate_on_submit():
        flask_login.logout_user()
        redirect_uri = flask.url_for('.index', _external=True)
        id_token_hint = flask.session.pop('oidc_id_token_hint', None)
        if id_token_hint:
            return flask.redirect(oidc.logout(id_token_hint, redirect_uri))
        return flask.redirect(redirect_uri)
    return flask.render_template('sign_out.html')


@frontend.route('/users/me/shared_device_state')
def shared_device_state() -> FlaskResponseT:
    shared_device_state = False
    # accessing flask_login.current_user triggers the check for a user
    if flask_login.current_user.is_authenticated:
        shared_device_state = bool(flask.g.get('shared_device_state'))
    return flask.jsonify(shared_device_state)


@frontend.route('/users/me/oidc/start')
def oidc_start() -> FlaskResponseT:
    if not oidc.is_oidc_configured():
        flask.flash(_('OIDC is disabled.'), 'error')
        return flask.redirect(flask.url_for('.index'))

    if flask_login.current_user.is_authenticated and flask_login.login_fresh():
        return _redirect_to_next_url()

    url, token = oidc.start_authentication(
        flask.request.args.get('next', flask.url_for('.index')),
    )
    flask.session['oidc_token'] = token
    return flask.redirect(url)


@frontend.route('/users/me/oidc/callback')
def oidc_callback() -> FlaskResponseT:
    if not oidc.is_oidc_configured():
        flask.flash(_('OIDC is disabled.'), 'error')
        return flask.redirect(flask.url_for('.index'))

    if flask_login.current_user.is_authenticated and flask_login.login_fresh():
        return _redirect_to_next_url()

    try:
        result = oidc.handle_authentication(
            flask.request.url,
            flask.session.pop('oidc_token'),
        )
    except Exception:
        flask.flash(_('Login failed. Please contact an administrator.'), 'error')
        flask_login.logout_user()
        return flask.redirect(flask.url_for('.index'))

    user, id_token_hint, next = result

    # While the check in the user_loader would prevent a login, ensure this is
    # handled as soon as possible with a reliable message.
    if not user.is_active:
        flask.flash(_('Your user account has been deactivated. Please contact an administrator.'), 'error')
        return flask.redirect(flask.url_for('.index'))

    return complete_sign_in(
        user,
        is_for_refresh=False,
        remember_me=False,
        shared_device=False,
        next_url=next,
        oidc_id_token_hint=id_token_hint
    )
