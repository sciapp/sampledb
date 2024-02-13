# coding: utf-8
"""

"""
import typing

from http import HTTPStatus
import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField
from wtforms import validators, ValidationError

from .. import frontend
from ...logic import users, errors, groups, projects, instruments
from ...logic.components import get_component
from ...logic.users import get_federated_identities, get_user_by_federated_user
from ..utils import validate_orcid
from ...utils import FlaskResponseT
from ...models import UserType


class UserReadOnlyForm(FlaskForm):
    action = StringField(validators=[validators.AnyOf(['toggle_read_only'])])
    should_be_read_only = BooleanField()


class UserHiddenForm(FlaskForm):
    action = StringField(validators=[validators.AnyOf(['toggle_hidden'])])
    should_be_hidden = BooleanField()


class UserActiveForm(FlaskForm):
    action = StringField(validators=[validators.AnyOf(['toggle_active'])])
    should_be_active = BooleanField()


class UserProfileForm(FlaskForm):
    action = StringField(validators=[validators.AnyOf(['edit_profile'])])
    orcid = StringField()
    affiliation = StringField()
    role = StringField()

    def validate_orcid(self, field: StringField) -> None:
        orcid = field.data
        # accept empty ORCID iDs
        if orcid is None:
            return
        orcid = orcid.strip()
        if not orcid:
            return
        # check ORCID iD syntax
        is_valid, orcid = validate_orcid(orcid)
        if not is_valid:
            raise ValidationError("Please enter a valid ORCID iD.")
        # keep sanitized ORCID iD on success
        field.data = orcid


@frontend.route('/users/me')
@flask_login.login_required
def current_user_profile() -> FlaskResponseT:
    return flask.redirect(flask.url_for('.user_profile', user_id=flask_login.current_user.id))


@frontend.route('/users/<int:user_id>', methods=['GET', 'POST'])
@flask_login.login_required
def user_profile(user_id: int) -> FlaskResponseT:
    try:
        user = users.get_user(user_id)
    except errors.UserDoesNotExistError:
        return flask.abort(404)

    last_modifying_user = None
    if user.last_modified_by_id is not None and user.last_modified_by_id != user.id:
        try:
            last_modifying_user = users.get_user(user.last_modified_by_id)
        except errors.UserDoesNotExistError:
            pass

    show_federated_identities = user.type not in (UserType.ELN_IMPORT_USER, UserType.FEDERATION_USER)
    fed_identity_descriptions_sampledb: dict[str, typing.Any] = {}
    fed_identity_descriptions_eln = []

    if show_federated_identities:
        for identity in sorted(get_federated_identities(user_id=user.id, component=None, active_status=True), key=lambda identity: identity.local_fed_id):
            if identity.local_fed_user.type == UserType.FEDERATION_USER:
                if identity.local_fed_user.component is None:
                    continue
                if identity.local_fed_user.component.uuid not in fed_identity_descriptions_sampledb:
                    fed_identity_descriptions_sampledb[identity.local_fed_user.component.uuid] = {
                        "component_name": identity.local_fed_user.component.name if identity.local_fed_user.component.name else _('Unknown database'),
                        "component_url": flask.url_for('.component', component_id=identity.local_fed_user.component_id),
                        "user_links": []
                    }
                component_address = identity.local_fed_user.component.address
                if component_address and not component_address.endswith("/"):
                    component_address += "/"
                fed_identity_descriptions_sampledb[identity.local_fed_user.component.uuid]["user_links"].append({
                    "user_url": f"{component_address}users/{identity.local_fed_user.fed_id}" if identity.local_fed_user.component.address else flask.url_for('.user_profile', user_id=identity.local_fed_id),
                    "fed_id": identity.local_fed_user.fed_id
                })
            elif identity.local_fed_user.type == UserType.ELN_IMPORT_USER:
                fed_identity_descriptions_eln.append({
                    "eln_object_id": identity.local_fed_user.eln_object_id if identity.local_fed_user.eln_object_id else None,
                    "eln_import_id": identity.local_fed_user.eln_import_id,
                    "eln_import_url": flask.url_for('.eln_import', eln_import_id=identity.local_fed_user.eln_import_id),
                    "user_id": identity.local_fed_id
                })

    for identity_description in fed_identity_descriptions_sampledb.values():
        identity_description["user_links"] = sorted(identity_description["user_links"], key=lambda x: x["fed_id"])

    show_local_federated_identity = user.type in [UserType.FEDERATION_USER, UserType.ELN_IMPORT_USER]
    local_federated_identity_user = get_user_by_federated_user(federated_user_id=user.id)

    if flask_login.current_user.is_admin and not flask_login.current_user.is_readonly:
        user_read_only_form = UserReadOnlyForm()
        user_read_only_form.should_be_read_only.default = not user.is_readonly
        if user_read_only_form.validate_on_submit():
            users.set_user_readonly(user.id, user_read_only_form.should_be_read_only.data)
            if user_read_only_form.should_be_read_only.data:
                flask.flash(_('The user has been marked as read only.'), 'success')
            else:
                flask.flash(_('The user has been unmarked as read only.'), 'success')
            return flask.redirect(flask.url_for('.user_profile', user_id=user.id))
        user_hidden_form = UserHiddenForm()
        user_hidden_form.should_be_hidden.default = not user.is_hidden
        if user_hidden_form.validate_on_submit():
            users.set_user_hidden(user.id, user_hidden_form.should_be_hidden.data)
            if user_hidden_form.should_be_hidden.data:
                flask.flash(_('The user has been marked as hidden.'), 'success')
            else:
                flask.flash(_('The user has been unmarked as hidden.'), 'success')
            return flask.redirect(flask.url_for('.user_profile', user_id=user.id))
        user_active_form = UserActiveForm()
        user_active_form.should_be_active.default = not user.is_active
        if user_active_form.validate_on_submit():
            users.set_user_active(user.id, user_active_form.should_be_active.data)
            if user_active_form.should_be_active.data:
                flask.flash(_('The user has been activated.'), 'success')
            else:
                flask.flash(_('The user has been deactivated.'), 'success')
            return flask.redirect(flask.url_for('.user_profile', user_id=user.id))
        if user.component_id is None:
            user_profile_form = UserProfileForm()
            if not user_profile_form.is_submitted():
                user_profile_form.orcid.data = user.orcid
                user_profile_form.role.data = user.role
                user_profile_form.affiliation.data = user.affiliation
            if user_profile_form.validate_on_submit():
                if user_profile_form.orcid.data and user_profile_form.orcid.data.strip():
                    orcid = user_profile_form.orcid.data.strip()
                else:
                    orcid = None
                if user_profile_form.affiliation.data and user_profile_form.affiliation.data.strip():
                    affiliation = user_profile_form.affiliation.data.strip()
                else:
                    affiliation = None
                if user_profile_form.role.data and user_profile_form.role.data.strip():
                    role = user_profile_form.role.data.strip()
                else:
                    role = None
                extra_fields = {}
                for extra_field_id in flask.current_app.config['EXTRA_USER_FIELDS']:
                    extra_field_value = flask.request.form.get('extra_field_' + str(extra_field_id))
                    if extra_field_value and extra_field_value.strip():
                        extra_fields[extra_field_id] = extra_field_value
                change_orcid = (user.orcid != orcid and (orcid is not None or user.orcid is not None))
                change_affiliation = (user.affiliation != affiliation and (affiliation is not None or user.affiliation is not None))
                change_role = (user.role != role and (role is not None or user.role is not None))
                change_extra_fields = user.extra_fields != extra_fields
                if change_orcid or change_affiliation or change_role or change_extra_fields:
                    users.update_user(
                        user.id,
                        updating_user_id=flask_login.current_user.id,
                        orcid=orcid,
                        affiliation=affiliation,
                        role=role,
                        extra_fields=extra_fields
                    )
                    flask.flash(_("Successfully updated the user information."), 'success')
                    return flask.redirect(flask.url_for('.user_profile', user_id=user.id))
        else:
            user_profile_form = None
    elif flask.request.method.lower() == 'post':
        return flask.abort(HTTPStatus.METHOD_NOT_ALLOWED)
    else:
        user_read_only_form = None
        user_hidden_form = None
        user_active_form = None
        user_profile_form = None
    return flask.render_template(
        'profile.html',
        user_read_only_form=user_read_only_form,
        user_hidden_form=user_hidden_form,
        user_active_form=user_active_form,
        user_profile_form=user_profile_form,
        user=user,
        last_modifying_user=last_modifying_user,
        EXTRA_USER_FIELDS=flask.current_app.config['EXTRA_USER_FIELDS'],
        basic_groups=groups.get_user_groups(user.id),
        project_groups=projects.get_user_projects(user.id, include_groups=True),
        instruments=[
            instruments.get_instrument(instrument_id)
            for instrument_id in instruments.get_user_instruments(user.id, exclude_hidden=True)
        ],
        get_component=get_component,
        show_federated_identities=show_federated_identities,
        fed_identity_descriptions_sampledb=fed_identity_descriptions_sampledb,
        fed_identity_descriptions_eln=fed_identity_descriptions_eln,
        local_federated_identity_user=local_federated_identity_user,
        show_local_federated_identity=show_local_federated_identity
    )
