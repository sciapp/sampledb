# coding: utf-8
"""

"""

import datetime
import http
import json
import secrets
import typing

import flask
from flask_babel import refresh, _, lazy_gettext
import flask_login
from fido2.webauthn import PublicKeyCredentialUserEntity, ResidentKeyRequirement, UserVerificationRequirement
import pytz

from ... import db

from .. import frontend
from ..authentication_forms import ChangeUserForm, AuthenticationForm, AuthenticationMethodForm
from ..users_forms import RequestPasswordResetForm, PasswordForm, AuthenticationPasswordForm
from ..permission_forms import handle_permission_forms, set_up_permissions_forms
from .forms import NotificationModeForm, OtherSettingsForm, CreateAPITokenForm, ManageTwoFactorAuthenticationMethodForm, \
    AddWebhookForm, RemoveWebhookForm
from ..utils import get_groups_form_data

from ... import logic
from ...logic import user_log, errors
from ...logic.authentication import add_authentication_method, remove_authentication_method, change_password_in_authentication_method, add_api_token, get_two_factor_authentication_methods, activate_two_factor_authentication_method, deactivate_two_factor_authentication_method, delete_two_factor_authentication_method, get_all_fido2_passkey_credentials, add_fido2_passkey, get_webauthn_server, get_api_tokens, get_authentication_methods, get_authentication_method, confirm_authentication_method_by_email, ALL_AUTHENTICATION_TYPES
from ...logic.users import get_user, get_users
from ...logic.utils import send_email_confirmation_email, send_recovery_email
from ...logic.security_tokens import verify_token
from ...logic.default_permissions import default_permissions, get_default_permissions_for_users, get_default_permissions_for_groups, get_default_permissions_for_projects, get_default_permissions_for_all_users, get_default_permissions_for_anonymous_users
from ...logic.projects import get_project
from ...logic.groups import get_group
from ...logic.notifications import get_notification_modes, set_notification_mode_for_type
from ...logic.settings import get_user_settings, set_user_settings
from ...logic.locale import SUPPORTED_LOCALES
from ...logic.webhooks import get_webhooks, create_webhook, remove_webhook
from ...logic.instruments import get_user_instruments
from ...models import AuthenticationType, Permissions, NotificationType, NotificationMode, BackgroundTaskStatus
from ...models.webhooks import WebhookType
from ...utils import FlaskResponseT


@frontend.route('/users/me/preferences', methods=['GET', 'POST'])
def user_me_preferences() -> FlaskResponseT:
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for('.user_preferences', user_id=flask_login.current_user.id))
    return email_for_resetting_password()


@frontend.route('/users/<int:user_id>/preferences', methods=['GET', 'POST'])
def user_preferences(user_id: int) -> FlaskResponseT:
    token = flask.request.args.get('token')
    if token:
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
            if not flask_login.login_fresh():
                # ensure only fresh sessions can edit preferences including passwords and api tokens
                return flask.redirect(flask.url_for('.refresh_sign_in', next=flask.url_for('.user_preferences', user_id=flask_login.current_user.id)))
            # user is logged in and can edit their preferences
            return change_preferences()
    else:
        return typing.cast(flask_login.LoginManager, flask.current_app.login_manager).unauthorized()  # type: ignore[attr-defined, no-any-return]


def _handle_account_information_forms(
        template_kwargs: typing.Dict[str, typing.Any]
) -> typing.Optional[FlaskResponseT]:
    change_user_form = ChangeUserForm()

    template_kwargs.update(
        change_user_form=change_user_form,
        EXTRA_USER_FIELDS=flask.current_app.config['EXTRA_USER_FIELDS'],
    )
    if 'change' not in flask.request.form:
        if change_user_form.name.data is None or change_user_form.name.data == "":
            change_user_form.name.data = flask_login.current_user.name
        if change_user_form.email.data is None or change_user_form.email.data == "":
            change_user_form.email.data = flask_login.current_user.email
        if change_user_form.orcid.data is None or change_user_form.orcid.data == "":
            change_user_form.orcid.data = flask_login.current_user.orcid
        if change_user_form.affiliation.data is None or change_user_form.affiliation.data == "":
            change_user_form.affiliation.data = flask_login.current_user.affiliation
        if change_user_form.role.data is None or change_user_form.role.data == "":
            change_user_form.role.data = flask_login.current_user.role
    if 'change' in flask.request.form and flask.request.form['change'] == 'Change':
        if change_user_form.validate_on_submit():
            if change_user_form.name.data != flask_login.current_user.name:
                logic.users.update_user(
                    flask_login.current_user.id,
                    updating_user_id=flask_login.current_user.id,
                    name=str(change_user_form.name.data)
                )
                user_log.edit_user_preferences(user_id=flask_login.current_user.id)
                flask.flash(_("Successfully updated your user name."), 'success')
            if change_user_form.email.data != flask_login.current_user.email:
                # send confirm link
                mail_send_status = send_email_confirmation_email(
                    email=change_user_form.email.data,
                    user_id=flask_login.current_user.id,
                    salt='edit_profile'
                )[0]
                if mail_send_status == BackgroundTaskStatus.FAILED:
                    flask.flash(_("Sending an email failed. Please try again later or contact an administrator."), 'error')
                else:
                    flask.flash(_("Please see your email to confirm this change."), 'success')
            if change_user_form.orcid.data != flask_login.current_user.orcid or change_user_form.affiliation.data != flask_login.current_user.affiliation or change_user_form.role.data != flask_login.current_user.role:
                if change_user_form.orcid.data and change_user_form.orcid.data.strip():
                    orcid = change_user_form.orcid.data.strip()
                else:
                    orcid = None
                if change_user_form.affiliation.data and change_user_form.affiliation.data.strip():
                    affiliation = change_user_form.affiliation.data.strip()
                else:
                    affiliation = None
                if change_user_form.role.data and change_user_form.role.data.strip():
                    role = change_user_form.role.data.strip()
                else:
                    role = None
                extra_fields = {}
                for extra_field_id in flask.current_app.config['EXTRA_USER_FIELDS']:
                    extra_field_value = flask.request.form.get('extra_field_' + str(extra_field_id))
                    if extra_field_value:
                        extra_fields[extra_field_id] = extra_field_value
                change_orcid = (flask_login.current_user.orcid != orcid and (orcid is not None or flask_login.current_user.orcid is not None))
                change_affiliation = (flask_login.current_user.affiliation != affiliation and (affiliation is not None or flask_login.current_user.affiliation is not None))
                change_role = (flask_login.current_user.role != role and (role is not None or flask_login.current_user.role is not None))
                change_extra_fields = flask_login.current_user.extra_fields != extra_fields
                if change_orcid or change_affiliation or change_role or change_extra_fields:
                    logic.users.update_user(
                        flask_login.current_user.id,
                        updating_user_id=flask_login.current_user.id,
                        orcid=orcid,
                        affiliation=affiliation,
                        role=role,
                        extra_fields=extra_fields
                    )
                    user_log.edit_user_preferences(user_id=flask_login.current_user.id)
                    flask.flash(_("Successfully updated your user information."), 'success')

            return flask.redirect(flask.url_for('frontend.user_me_preferences'))
    return None


def _handle_authentication_methods_forms(
        template_kwargs: typing.Dict[str, typing.Any]
) -> typing.Optional[FlaskResponseT]:
    authentication_methods = get_authentication_methods(
        user_id=flask_login.current_user.id,
        authentication_types=ALL_AUTHENTICATION_TYPES - {
            AuthenticationType.API_TOKEN,
            AuthenticationType.API_ACCESS_TOKEN
        } - ({AuthenticationType.FEDERATED_LOGIN} if not flask.current_app.config['ENABLE_FEDERATED_LOGIN'] else set())
    )
    authentication_method_ids = [authentication_method.id for authentication_method in authentication_methods]

    authentication_form = AuthenticationForm()
    if flask.current_app.config["ENABLE_FIDO2_PASSKEY_AUTHENTICATION"]:
        authentication_form.authentication_method.choices.append(('FIDO2_PASSKEY', 'FIDO2 Passkey'))
    authentication_method_form = AuthenticationMethodForm()
    authentication_password_form = AuthenticationPasswordForm()

    server = get_webauthn_server()
    all_credentials = get_all_fido2_passkey_credentials()
    options, state = server.register_begin(
        PublicKeyCredentialUserEntity(
            id=f"signin-{flask_login.current_user.id}".encode('utf-8'),
            name=f"{flask_login.current_user.name} ({flask_login.current_user.email})",
            display_name=flask_login.current_user.name,
        ),
        credentials=all_credentials,
        resident_key_requirement=ResidentKeyRequirement.PREFERRED,
        user_verification=UserVerificationRequirement.REQUIRED
    )
    if not authentication_form.validate_on_submit():
        flask.session["webauthn_enroll_state"] = state

    template_kwargs.update(
        authentication_password_form=authentication_password_form,
        authentication_method_form=authentication_method_form,
        authentication_form=authentication_form,
        confirmed_authentication_methods=len([
            authentication_method
            for authentication_method in authentication_methods
            if authentication_method.confirmed and authentication_method.type != AuthenticationType.FIDO2_PASSKEY
        ]),
        authentications=authentication_methods,
        api_access_tokens=get_authentication_methods(
            user_id=flask_login.current_user.id,
            authentication_types={AuthenticationType.API_ACCESS_TOKEN}
        ),
        options=options,
    )

    if 'edit' in flask.request.form and flask.request.form['edit'] == 'Edit':
        if authentication_password_form.validate_on_submit() and authentication_password_form.id.data in authentication_method_ids:
            authentication_method_id = authentication_password_form.id.data
            try:
                password_was_changed = change_password_in_authentication_method(authentication_method_id, authentication_password_form.password.data)
            except Exception as e:
                password_was_changed = False
                template_kwargs.update(
                    error=str(e),
                )
            if not password_was_changed:
                flask.flash(_("Failed to change password."), 'error')
                return None
            flask.flash(_("Successfully updated your password."), 'success')
            user_log.edit_user_preferences(user_id=flask_login.current_user.id)
            return flask.redirect(flask.url_for('frontend.user_me_preferences'))
        else:
            flask.flash(_("Failed to change password."), 'error')
    if 'remove' in flask.request.form and flask.request.form['remove'] == 'Remove':
        authentication_method_id = authentication_method_form.id.data
        if authentication_method_form.validate_on_submit():
            try:
                remove_authentication_method(authentication_method_id)
            except Exception as e:
                flask.flash(_("Failed to remove the authentication method."), 'error')
                template_kwargs.update(
                    error=str(e),
                )
                return None
            else:
                flask.flash(_("Successfully removed the authentication method."), 'success')
                user_log.edit_user_preferences(user_id=flask_login.current_user.id)
                return flask.redirect(flask.url_for('frontend.user_me_preferences'))
    if 'add' in flask.request.form and flask.request.form['add'] == 'Add':
        if logic.oidc.is_oidc_only_auth_method():
            # The form isn't shown to the user, so ignore attempts.
            return None

        if authentication_form.validate_on_submit():
            # check, if login already exists
            all_authentication_methods = {
                'E': AuthenticationType.EMAIL,
                'L': AuthenticationType.LDAP,
                'O': AuthenticationType.OTHER
            }
            if flask.current_app.config['ENABLE_FIDO2_PASSKEY_AUTHENTICATION']:
                all_authentication_methods['FIDO2_PASSKEY'] = AuthenticationType.FIDO2_PASSKEY
            if authentication_form.authentication_method.data not in all_authentication_methods:
                return flask.abort(400)

            authentication_method = all_authentication_methods[authentication_form.authentication_method.data]
            # check, if additional authentication is correct
            try:
                if authentication_method == AuthenticationType.FIDO2_PASSKEY:
                    auth_data = server.register_complete(
                        flask.session["webauthn_enroll_state"],
                        json.loads(authentication_form.fido2_passkey_credentials.data)
                    )
                    assert auth_data.credential_data is not None
                    add_fido2_passkey(
                        user_id=flask_login.current_user.id,
                        credential_data=auth_data.credential_data,
                        description=authentication_form.description.data
                    )
                    del flask.session["webauthn_enroll_state"]
                else:
                    add_authentication_method(flask_login.current_user.id, authentication_form.login.data, authentication_form.password.data, authentication_method)
                flask.flash(_("Successfully added the authentication method."), 'success')
                return flask.redirect(flask.url_for('.user_me_preferences'))
            except Exception as e:
                flask.flash(_("Failed to add an authentication method."), 'error')
                template_kwargs.update(
                    error_add=str(e)
                )
                return None
        else:
            flask.flash(_("Failed to add an authentication method."), 'error')
    return None


def _handle_create_api_token_form(
        template_kwargs: typing.Dict[str, typing.Any]
) -> typing.Optional[FlaskResponseT]:
    create_api_token_form = CreateAPITokenForm()

    template_kwargs.update(
        api_tokens=get_api_tokens(flask_login.current_user.id),
        create_api_token_form=create_api_token_form,
        created_api_token=None
    )
    if 'create_api_token' in flask.request.form and create_api_token_form.validate_on_submit():
        created_api_token = secrets.token_hex(32)
        description = create_api_token_form.description.data
        try:
            add_api_token(flask_login.current_user.id, created_api_token, description)
            template_kwargs.update(
                api_tokens=get_api_tokens(flask_login.current_user.id),
                created_api_token=created_api_token,
            )
        except Exception as e:
            flask.flash(_("Failed to add an API token."), 'error')
            template_kwargs.update(
                error_add=str(e)
            )
    return None


def _handle_two_factor_authentication_forms(
        template_kwargs: typing.Dict[str, typing.Any]
) -> typing.Optional[FlaskResponseT]:
    two_factor_authentication_methods = get_two_factor_authentication_methods(flask_login.current_user.id)
    manage_two_factor_authentication_method_form = ManageTwoFactorAuthenticationMethodForm()
    template_kwargs.update(
        two_factor_authentication_methods=two_factor_authentication_methods,
        manage_two_factor_authentication_method_form=manage_two_factor_authentication_method_form,
        has_active_method=any(method.active for method in two_factor_authentication_methods),
    )

    if manage_two_factor_authentication_method_form.validate_on_submit():
        method_id = manage_two_factor_authentication_method_form.method_id.data
        method = {
            method.id: method
            for method in two_factor_authentication_methods
        }.get(manage_two_factor_authentication_method_form.method_id.data)
        if method is not None:
            if manage_two_factor_authentication_method_form.action.data == 'delete':
                if method.active:
                    flask.flash(_('You cannot delete an active two-factor authentication method.'), 'error')
                    return flask.redirect(flask.url_for('.user_me_preferences'))
                delete_two_factor_authentication_method(method_id)
                flask.flash(_('The two-factor authentication method has been deleted.'), 'success')
                return flask.redirect(flask.url_for('.user_me_preferences'))
            if manage_two_factor_authentication_method_form.action.data == 'enable':
                flask.session['confirm_data'] = {
                    'reason': 'activate_two_factor_authentication_method',
                    'user_id': method.user_id,
                    'expiration_datetime': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
                }
                if method.data.get('type') == 'totp':
                    return flask.redirect(flask.url_for('.confirm_totp_two_factor_authentication', method_id=method.id))
                elif method.data.get('type') == 'fido2_passkey':
                    return flask.redirect(flask.url_for('.confirm_fido2_passkey_two_factor_authentication', method_id=method.id))
                else:
                    del flask.session['confirm_data']
                    activate_two_factor_authentication_method(method_id)
                    flask.flash(_('The two-factor authentication method has been enabled.'), 'success')
                    return flask.redirect(flask.url_for('.user_me_preferences'))
            if manage_two_factor_authentication_method_form.action.data == 'disable':
                flask.session['confirm_data'] = {
                    'reason': 'deactivate_two_factor_authentication_method',
                    'user_id': method.user_id,
                    'method_to_deactivate_id': method.id,
                    'expiration_datetime': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
                }
                usable_active_two_factor_authentication_methods = [
                    other_method
                    for other_method in two_factor_authentication_methods
                    if other_method.active and other_method.data.get('type') in ('totp', 'fido2_passkey',)
                ]
                if len(usable_active_two_factor_authentication_methods) < 2:
                    if usable_active_two_factor_authentication_methods:
                        two_factor_authentication_method = usable_active_two_factor_authentication_methods[0]
                        if two_factor_authentication_method.data.get('type') == 'totp':
                            return flask.redirect(flask.url_for('.confirm_totp_two_factor_authentication', method_id=two_factor_authentication_method.id))
                        if two_factor_authentication_method.data.get('type') == 'fido2_passkey':
                            return flask.redirect(flask.url_for('.confirm_fido2_passkey_two_factor_authentication', method_id=two_factor_authentication_method.id))
                    del flask.session['confirm_data']
                    deactivate_two_factor_authentication_method(method_id)
                    flask.flash(_('The two-factor authentication method has been disabled.'), 'success')
                    return flask.redirect(flask.url_for('.user_me_preferences'))
                return flask.render_template(
                    'two_factor_authentication/pick.html',
                    methods=usable_active_two_factor_authentication_methods,
                    method_to_deactivate=method
                )
        flask.flash(_('Something went wrong, please try again.'), 'error')
    return None


def _handle_webhook_forms(
        template_kwargs: typing.Dict[str, typing.Any]
) -> typing.Optional[FlaskResponseT]:
    may_use_webhooks = flask_login.current_user.is_admin or flask.current_app.config['ENABLE_WEBHOOKS_FOR_USERS']
    add_webhook_form = AddWebhookForm()
    if add_webhook_form.address.data is None:
        add_webhook_form.address.data = ''
    if add_webhook_form.name.data is None:
        add_webhook_form.name.data = ''
    remove_webhook_form = RemoveWebhookForm()

    template_kwargs.update(
        may_use_webhooks=may_use_webhooks,
        webhooks=get_webhooks(user_id=flask_login.current_user.get_id()),
        show_add_form=False,
        webhook_secret=None,
        add_webhook_form=add_webhook_form,
        remove_webhook_form=remove_webhook_form,
    )

    if 'remove_webhook' in flask.request.form and may_use_webhooks:
        if remove_webhook_form.validate_on_submit():
            try:
                webhook_id = remove_webhook_form.id.data
                remove_webhook(webhook_id)
                flask.flash(_('Successfully removed the webhook.'), 'success')
            except Exception:
                flask.flash(_('Failed to remove the webhook.'), 'error')
            return flask.redirect(flask.url_for('.user_preferences', user_id=flask_login.current_user.id))

    if 'add_webhook' in flask.request.form:
        if not may_use_webhooks:
            flask.flash(_('You are not allowed to create Webhooks.'), 'error')
            return None
        if add_webhook_form.validate_on_submit():
            try:
                name = add_webhook_form.name.data
                address = add_webhook_form.address.data
                if name == '':
                    name = None
                if address == '':
                    address = None
                new_webhook = create_webhook(type=WebhookType.OBJECT_LOG, user_id=flask_login.current_user.get_id(), target_url=address, name=name)
            except errors.WebhookAlreadyExistsError:
                add_webhook_form.address.errors.append(_('A webhook of this type with this target address already exists', service_name=flask.current_app.config['SERVICE_NAME']))
            except errors.InsecureComponentAddressError:
                add_webhook_form.address.errors.append(_('Only secure communication via https is allowed'))
            except errors.InvalidComponentAddressError:
                add_webhook_form.address.errors.append(_('This webhook address is invalid'))
            except Exception:
                add_webhook_form.name.errors.append(_('Failed to create webhook'))
            else:
                flask.flash(_('The webhook has been added successfully'), 'success')
                template_kwargs.update(
                    webhooks=get_webhooks(user_id=flask_login.current_user.get_id()),
                    webhook_secret=new_webhook.secret,
                )
                return None
        template_kwargs.update(
            show_add_form=True
        )
    return None


def _handle_notification_forms(
        template_kwargs: typing.Dict[str, typing.Any]
) -> typing.Optional[FlaskResponseT]:
    notification_mode_form = NotificationModeForm()

    template_kwargs.update(
        notification_modes=get_notification_modes(flask_login.current_user.id),
        notification_mode_form=notification_mode_form,
        NotificationMode=NotificationMode,
        NotificationType=NotificationType,
        is_instrument_responsible_user=bool(get_user_instruments(flask_login.current_user.id, exclude_hidden=True))
    )

    if 'edit_notification_settings' in flask.request.form and notification_mode_form.validate_on_submit():
        for notification_type in NotificationType:
            if 'notification_mode_for_type_' + notification_type.name.lower() in flask.request.form:
                notification_mode_text = flask.request.form.get('notification_mode_for_type_' + notification_type.name.lower())
                for notification_mode in [NotificationMode.IGNORE, NotificationMode.WEBAPP, NotificationMode.EMAIL]:
                    if notification_mode_text == notification_mode.name.lower():
                        set_notification_mode_for_type(notification_type, flask_login.current_user.id, notification_mode)
                        break
        flask.flash(_("Successfully updated your notification settings."), 'success')
        return flask.redirect(flask.url_for('.user_preferences', user_id=flask_login.current_user.id))
    return None


def _handle_default_permissions_forms(
        template_kwargs: typing.Dict[str, typing.Any]
) -> typing.Optional[FlaskResponseT]:
    user_permissions = get_default_permissions_for_users(creator_id=flask_login.current_user.id)
    group_permissions = get_default_permissions_for_groups(creator_id=flask_login.current_user.id)
    project_permissions = get_default_permissions_for_projects(creator_id=flask_login.current_user.id)
    all_user_permissions = get_default_permissions_for_all_users(creator_id=flask_login.current_user.id)
    anonymous_user_permissions = get_default_permissions_for_anonymous_users(creator_id=flask_login.current_user.id)

    (
        add_user_permissions_form,
        add_group_permissions_form,
        add_project_permissions_form,
        default_permissions_form
    ) = set_up_permissions_forms(
        resource_permissions=logic.default_permissions.default_permissions,
        resource_id=flask_login.current_user.id,
        existing_all_user_permissions=all_user_permissions,
        existing_anonymous_user_permissions=anonymous_user_permissions,
        existing_user_permissions=user_permissions,
        existing_group_permissions=group_permissions,
        existing_project_permissions=project_permissions
    )

    users_without_permissions = get_users(exclude_hidden=not flask_login.current_user.is_admin or not flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN'], exclude_fed=True, exclude_eln_import=True)
    users_without_permissions = [user for user in users_without_permissions if user.id not in user_permissions]
    users_without_permissions.sort(key=lambda user: user.id)

    show_groups_form, groups_treepicker_info = get_groups_form_data(
        basic_group_filter=lambda group: group.id not in group_permissions
    )

    show_projects_form, projects_treepicker_info = get_groups_form_data(
        project_group_filter=lambda group: group.id not in project_permissions
    )
    template_kwargs.update(
        Permissions=Permissions,
        user_permissions=user_permissions,
        group_permissions=group_permissions,
        project_permissions=project_permissions,
        all_user_permissions=all_user_permissions,
        default_permissions_form=default_permissions_form,
        add_user_permissions_form=add_user_permissions_form,
        add_group_permissions_form=add_group_permissions_form,
        add_project_permissions_form=add_project_permissions_form,
        users=users_without_permissions,
        show_groups_form=show_groups_form,
        groups_treepicker_info=groups_treepicker_info,
        show_projects_form=show_projects_form,
        projects_treepicker_info=projects_treepicker_info,
        get_user=get_user,
        get_group=get_group,
        get_project=get_project,
    )
    if handle_permission_forms(
        default_permissions,
        flask_login.current_user.id,
        add_user_permissions_form,
        add_group_permissions_form,
        add_project_permissions_form,
        default_permissions_form
    ):
        flask.flash(_("Successfully updated default permissions."), 'success')
        return flask.redirect(flask.url_for('.user_preferences', user_id=flask_login.current_user.id))
    return None


def _handle_other_settings_forms(
        template_kwargs: typing.Dict[str, typing.Any]
) -> typing.Optional[FlaskResponseT]:
    other_settings_form = OtherSettingsForm()
    all_timezones = list(pytz.all_timezones)

    template_kwargs.update(
        user_settings=get_user_settings(flask_login.current_user.id),
        other_settings_form=other_settings_form,
        all_timezones=all_timezones,
        supported_locales=SUPPORTED_LOCALES,
        your_locale=flask.request.accept_languages.best_match(SUPPORTED_LOCALES),
        allowed_language_codes=logic.locale.get_allowed_language_codes(),
    )
    if 'edit_other_settings' in flask.request.form and other_settings_form.validate_on_submit():
        use_schema_editor = flask.request.form.get('input-use-schema-editor', 'yes') != 'no'
        modified_settings: typing.Dict[str, typing.Any] = {
            'USE_SCHEMA_EDITOR': use_schema_editor
        }
        select_timezone = flask.request.form.get('select-timezone', '')
        select_locale = flask.request.form.get('select-locale', '')

        if select_locale == 'auto_lc':
            set_user_settings(
                flask_login.current_user.id,
                {
                    'LOCALE': 'en',
                    'AUTO_LC': True
                }
            )
        elif select_locale in logic.locale.get_allowed_language_codes():
            set_user_settings(flask_login.current_user.id, {'LOCALE': select_locale, 'AUTO_LC': False})

        if not flask.current_app.config['TIMEZONE']:
            if select_timezone == 'auto_tz':
                set_user_settings(flask_login.current_user.id, {'AUTO_TZ': True})
            elif select_timezone in all_timezones:
                set_user_settings(flask_login.current_user.id, {'AUTO_TZ': False, 'TIMEZONE': select_timezone})
            else:
                flask.flash("Invalid timezone", 'error')

        objects_per_page = flask.request.form.get('input-objects-per-page', '')
        if objects_per_page == 'all':
            modified_settings['OBJECTS_PER_PAGE'] = None
        else:
            try:
                modified_settings['OBJECTS_PER_PAGE'] = int(objects_per_page)
            except ValueError:
                pass

        show_object_type_and_id_on_object_page_text = flask.request.form.get('input-show-object-type-and-id-on-object-page', 'default')
        if show_object_type_and_id_on_object_page_text == 'yes':
            show_object_type_and_id_on_object_page = True
        elif show_object_type_and_id_on_object_page_text == 'no':
            show_object_type_and_id_on_object_page = False
        else:
            show_object_type_and_id_on_object_page = None
        modified_settings['SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE'] = show_object_type_and_id_on_object_page

        show_object_title_text = flask.request.form.get('input-show-object-title', 'default')
        if show_object_title_text == 'yes':
            show_object_title = True
        elif show_object_title_text == 'no':
            show_object_title = False
        else:
            show_object_title = None
        modified_settings['SHOW_OBJECT_TITLE'] = show_object_title

        full_width_objects_table_text = flask.request.form.get('input-full-width-objects-table', 'default')
        if full_width_objects_table_text == 'yes':
            full_width_objects_table = True
        elif full_width_objects_table_text == 'no':
            full_width_objects_table = False
        else:
            full_width_objects_table = None
        modified_settings['FULL_WIDTH_OBJECTS_TABLE'] = full_width_objects_table

        workflow_view_modals_text = flask.request.form.get('input-workflow-view-modals', 'default')
        if workflow_view_modals_text == 'yes':
            workflow_view_modals = True
        elif workflow_view_modals_text == 'no':
            workflow_view_modals = False
        else:
            workflow_view_modals = None
        modified_settings['WORKFLOW_VIEW_MODALS'] = workflow_view_modals

        workflow_view_collapsed_text = flask.request.form.get('input-workflow-view-collapsed', 'default')
        if workflow_view_collapsed_text == 'yes':
            workflow_view_collapsed = True
        elif workflow_view_collapsed_text == 'no':
            workflow_view_collapsed = False
        else:
            workflow_view_collapsed = None
        modified_settings['WORKFLOW_VIEW_COLLAPSED'] = workflow_view_collapsed

        if flask_login.current_user.is_admin:
            use_admin_permissions = flask.request.form.get('input-use-admin-permissions', 'yes') != 'no'
            modified_settings['USE_ADMIN_PERMISSIONS'] = use_admin_permissions
            show_invitation_log = flask.request.form.get('input-show-invitation-log', 'yes') != 'no'
            modified_settings['SHOW_INVITATION_LOG'] = show_invitation_log
            show_hidden_users_as_admin = flask.request.form.get('input-show-hidden-users-as-admin', 'yes') != 'no'
            modified_settings['SHOW_HIDDEN_USERS_AS_ADMIN'] = show_hidden_users_as_admin
        set_user_settings(flask_login.current_user.id, modified_settings)
        flask_login.current_user.clear_caches()
        refresh()
        flask.flash(lazy_gettext("Successfully updated your settings."), 'success')
        return flask.redirect(flask.url_for('.user_preferences', user_id=flask_login.current_user.id))

    if 'delete_dataverse_api_token' in flask.request.form:
        set_user_settings(flask_login.current_user.id, {
            'DATAVERSE_API_TOKEN': ''
        })
        flask.flash(_('Successfully deleted your stored Dataverse API Token.'), 'success')
        return flask.redirect(flask.url_for('frontend.user_me_preferences'))
    return None


def change_preferences() -> FlaskResponseT:
    template_kwargs: typing.Dict[str, typing.Any] = {}

    response = _handle_account_information_forms(template_kwargs)
    if response is not None:
        return response
    response = _handle_authentication_methods_forms(template_kwargs)
    if response is not None:
        return response
    response = _handle_create_api_token_form(template_kwargs)  # pylint: disable=assignment-from-none
    if response is not None:
        return response
    response = _handle_two_factor_authentication_forms(template_kwargs)
    if response is not None:
        return response
    response = _handle_webhook_forms(template_kwargs)
    if response is not None:
        return response
    response = _handle_notification_forms(template_kwargs)
    if response is not None:
        return response
    response = _handle_default_permissions_forms(template_kwargs)
    if response is not None:
        return response
    response = _handle_other_settings_forms(template_kwargs)
    if response is not None:
        return response

    return flask.render_template(
        'preferences.html',
        **template_kwargs
    )


def confirm_email() -> FlaskResponseT:
    token = flask.request.args.get('token')
    if not token:
        return flask.abort(404)
    data1 = verify_token(token, salt='edit_profile', secret_key=flask.current_app.config['SECRET_KEY'])
    data2 = verify_token(token, salt='add_login', secret_key=flask.current_app.config['SECRET_KEY'])
    if data1 is None and data2 is None:
        return flask.abort(404)
    else:
        if data1 is not None:
            data = data1
            salt = 'edit_profile'
        else:
            data = data2
            salt = 'add_login'
        if isinstance(data, dict) and 'email' in data and 'user_id' in data:
            email = data['email']
            user_id = data['user_id']
        else:
            return flask.abort(400)
        if salt == 'edit_profile':
            logic.users.update_user(
                user_id,
                updating_user_id=user_id,
                email=email
            )
        elif salt == 'add_login':
            try:
                confirm_authentication_method_by_email(
                    user_id=user_id,
                    email=email
                )
            except errors.AuthenticationMethodDoesNotExistError:
                return flask.abort(400)
        else:
            return flask.abort(400)
        db.session.commit()
        user_log.edit_user_preferences(user_id=user_id)
        return flask.redirect(flask.url_for('.user_preferences', user_id=user_id))


def email_for_resetting_password() -> FlaskResponseT:
    request_password_reset_form = RequestPasswordResetForm()
    if flask.request.method == "GET":
        #  GET (email dialog )
        return flask.render_template(
            'reset_password_by_email.html',
            request_password_reset_form=request_password_reset_form
        )
    if flask.request.method == "POST":
        has_error = False
        if request_password_reset_form.validate_on_submit():
            email = request_password_reset_form.email.data
            if '@' not in email:
                has_error = True
            else:
                mail_send_status_info = send_recovery_email(email)
                if mail_send_status_info is not None and mail_send_status_info[0] == BackgroundTaskStatus.FAILED:
                    flask.flash(_("Sending an email failed. Please try again later or contact an administrator."), 'error')
                else:
                    return flask.render_template(
                        'recovery_email_send.html',
                        email=email,
                        has_error=has_error
                    )
        return flask.render_template(
            'reset_password_by_email.html',
            request_password_reset_form=request_password_reset_form,
            has_error=has_error
        )
    return flask.abort(http.HTTPStatus.METHOD_NOT_ALLOWED)


def reset_password() -> FlaskResponseT:
    token = flask.request.args.get('token')
    if not token:
        return flask.abort(404)
    authentication_id = verify_token(token, salt='password', secret_key=flask.current_app.config['SECRET_KEY'])
    if not authentication_id:
        return flask.abort(404)
    authentication_method = get_authentication_method(authentication_method_id=authentication_id)
    password_form = PasswordForm()
    has_error = False
    if authentication_method is None:
        return flask.abort(404)
    username = authentication_method.login['login']
    if flask.request.method == "GET":
        # confirmation dialog
        return flask.render_template('password.html', password_form=password_form, has_error=has_error,
                                     user=authentication_method.user, username=username)
    else:
        if password_form.validate_on_submit():
            if change_password_in_authentication_method(authentication_method.id, password_form.password.data):
                flask.flash(_("Your password has been reset."), 'success')
            else:
                flask.flash(_("Resetting your password failed. Please try again or contact an administrator."), 'error')
            return flask.redirect(flask.url_for('frontend.index'))
        return flask.render_template('password.html', password_form=password_form, has_error=has_error,
                                     user=authentication_method.user, username=username)
