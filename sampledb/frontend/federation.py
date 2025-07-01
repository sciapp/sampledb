# coding: utf-8
"""

"""
import hashlib
import os
import secrets
import typing

import itsdangerous
import flask
import flask_login
import requests.exceptions

from flask_babel import _

from . import frontend
from .federation_forms import AddComponentForm, EditComponentForm, SyncComponentForm, CreateAPITokenForm, \
    AddOwnAPITokenForm, AuthenticationMethodForm, AddAliasForm, EditAliasForm, DeleteAliasForm, ModifyELNIdentityForm, \
    FederatedUserCreationForm
from ..logic import errors
from ..logic.utils import send_federated_login_account_creation_email
from .utils import check_current_user_is_not_readonly
from ..logic.component_authentication import remove_component_authentication_method, add_token_authentication, remove_own_component_authentication_method, add_own_token_authentication
from ..logic.components import get_component, update_component, add_component, get_components, check_component_exists, get_component_infos, ComponentInfo, get_component_by_uuid
from ..logic.federation.update import import_updates
from ..logic.federation.utils import login_required_saml, federated_login_route
from ..logic.federation.login import sp_login, get_idp_metadata, get_sp_metadata, process_login, resolve_artifact, eval_artifact_resolve, delete_old_artifacts
from ..logic.users import create_user, get_user_aliases_for_user, create_user_alias, update_user_alias, delete_user_alias, get_user_alias, delete_user_link, \
    get_federated_identity, get_federated_identities, revoke_user_links_by_fed_ids, create_sampledb_federated_identity, delete_user_links_by_fed_ids, \
    revoke_user_link, enable_user_link, get_user_by_federated_user, get_user, get_active_federated_identity_by_federated_user, enable_federated_identity_for_login, identity_not_required_for_auth, set_user_hidden
from ..logic.background_tasks import post_poke_components_task
from ..models import OwnComponentAuthentication, ComponentAuthenticationType, ComponentAuthentication, User, UserType, BackgroundTaskStatus, Authentication, AuthenticationType
from ..utils import FlaskResponseT


FEDERATED_IDENTITY_TOKENS_MAX_AGE = 60 * 5  # seconds


@frontend.route('/other-databases/<int:component_id>', methods=['GET', 'POST'])
@flask_login.login_required
def component(component_id: int) -> FlaskResponseT:
    try:
        component = get_component(component_id)
    except errors.ComponentDoesNotExistError:
        return flask.abort(404)
    try:
        alias = get_user_alias(flask_login.current_user.get_id(), component_id)
    except errors.UserAliasDoesNotExistError:
        alias = None
    created_api_token = None
    add_own_api_token_form = AddOwnAPITokenForm()
    create_api_token_form = CreateAPITokenForm()
    authentication_method_form = AuthenticationMethodForm()
    own_authentication_method_form = AuthenticationMethodForm()
    edit_component_form = EditComponentForm()
    show_edit_form = False
    if edit_component_form.address.data is None:
        if component.address is None:
            edit_component_form.address.data = ''
        else:
            edit_component_form.address.data = component.address
    if edit_component_form.name.data is None:
        if component.name is None:
            edit_component_form.name.data = ''
        else:
            edit_component_form.name.data = component.name
    if edit_component_form.description.data is None:
        edit_component_form.description.data = component.description
    sync_component_form = SyncComponentForm()

    own_api_tokens = OwnComponentAuthentication.query.filter(OwnComponentAuthentication.component_id == component_id, OwnComponentAuthentication.type == ComponentAuthenticationType.TOKEN).all()
    api_tokens = ComponentAuthentication.query.filter(ComponentAuthentication.component_id == component_id, ComponentAuthentication.type == ComponentAuthenticationType.TOKEN).all()

    if 'edit' in flask.request.form:
        show_edit_form = True
        if edit_component_form.validate_on_submit():
            check_current_user_is_not_readonly()
            if not flask_login.current_user.is_admin:
                return flask.abort(403)
            name = edit_component_form.name.data
            address = edit_component_form.address.data
            if address == '':
                address = None
            if name == '':
                name = None
            try:
                update_component(component_id=component_id, name=name, description=edit_component_form.description.data, address=address)
            except errors.ComponentDoesNotExistError:
                edit_component_form.name.errors.append(_('This database does not exist'))
            except errors.InvalidComponentNameError:
                edit_component_form.name.errors.append(_('This database name is invalid'))
            except errors.InvalidComponentAddressError:
                edit_component_form.address.errors.append(_('This database address is invalid'))
            except errors.ComponentAlreadyExistsError:
                edit_component_form.name.errors.append(_('A database with this UUID or name has already been added'))
                edit_component_form.address.errors.append(_('A database with this UUID or name has already been added'))
            except errors.InvalidComponentUUIDError:
                edit_component_form.name.errors.append(_('Invalid UUID'))
            except errors.InsecureComponentAddressError:
                edit_component_form.address.errors.append(_('Only secure communication via https is allowed'))
            except Exception:
                edit_component_form.name.errors.append(_('Failed to update database'))
            else:
                post_poke_components_task()
                flask.flash(_('Database information updated successfully'), 'success')
                return flask.redirect(flask.url_for('.component', component_id=component_id))
    else:
        if component.address is None:
            edit_component_form.address.data = ''
        else:
            edit_component_form.address.data = component.address
        if component.name is None:
            edit_component_form.name.data = ''
        else:
            edit_component_form.name.data = component.name
        edit_component_form.description.data = component.description
    if 'sync' in flask.request.form and sync_component_form.validate_on_submit():
        check_current_user_is_not_readonly()
        if not flask_login.current_user.is_admin:
            return flask.abort(403)
        ignore_last_sync_time = sync_component_form.ignore_last_sync_time.data
        try:
            import_updates(component, ignore_last_sync_time=ignore_last_sync_time)
            flask.flash(_('Successfully imported data changes.'), 'success')
        except errors.MissingComponentAddressError:
            flask.flash(_('Missing database address.'), 'error')
        except errors.NoAuthenticationMethodError:
            flask.flash(_('No valid authentication method configured.'), 'error')
        except errors.UnauthorizedRequestError:
            flask.flash(_('Invalid authentication method.'), 'error')
        except errors.InvalidDataExportError as error:
            flask.flash(_('Received invalid data. Error message: "%(error)s"', error=str(error)), 'error')
        except errors.ComponentNotConfiguredForFederationError:
            flask.flash(_('This database has not been configured to exchange data with other databases.'))
        except errors.RequestServerError:
            flask.flash(_('Server error when requesting the data.'), 'error')
        except errors.RequestError:
            flask.flash(_('Received error code when requesting the data.'), 'error')
        except requests.exceptions.ConnectionError:
            flask.flash(_('Failed to establish a connection to %(component_name)s (%(component_address)s).', component_name=component.get_name(), component_address=component.address), 'error')
        return flask.redirect(flask.url_for('.component', component_id=component_id))
    if 'remove' in flask.request.form and flask.request.form['remove'] == 'Remove':
        check_current_user_is_not_readonly()
        if not flask_login.current_user.is_admin:
            return flask.abort(403)
        authentication_method_id = authentication_method_form.id.data
        if authentication_method_form.validate_on_submit():
            try:
                remove_component_authentication_method(authentication_method_id)
                flask.flash(_('Successfully removed the authentication method.'), 'success')
                api_tokens = ComponentAuthentication.query.filter(ComponentAuthentication.component_id == component_id, ComponentAuthentication.type == ComponentAuthenticationType.TOKEN).all()
            except errors.AuthenticationMethodDoesNotExistError:
                flask.flash(_('Authentication method has already been deleted.'), 'error')
            except Exception:
                flask.flash(_('Failed to remove the authentication method.'), 'error')
    if 'removeOwn' in flask.request.form and flask.request.form['removeOwn'] == 'RemoveOwn':
        check_current_user_is_not_readonly()
        if not flask_login.current_user.is_admin:
            return flask.abort(403)
        authentication_method_id = authentication_method_form.id.data
        if authentication_method_form.validate_on_submit():
            try:
                remove_own_component_authentication_method(authentication_method_id)
                flask.flash(_('Successfully removed the authentication method.'), 'success')
                own_api_tokens = OwnComponentAuthentication.query.filter(OwnComponentAuthentication.component_id == component_id, OwnComponentAuthentication.type == ComponentAuthenticationType.TOKEN).all()
            except errors.AuthenticationMethodDoesNotExistError:
                flask.flash(_('Authentication method has already been deleted.'), 'error')
            except Exception:
                flask.flash(_('Failed to remove the authentication method.'), 'error')
    if 'create_api_token' in flask.request.form and create_api_token_form.validate_on_submit():
        check_current_user_is_not_readonly()
        if not flask_login.current_user.is_admin:
            return flask.abort(403)
        created_api_token = secrets.token_hex(32)
        description = create_api_token_form.description.data
        try:
            add_token_authentication(component_id, created_api_token, description)
        except Exception:
            flask.flash(_('Failed to add API token.'), 'error')
        api_tokens = ComponentAuthentication.query.filter(ComponentAuthentication.component_id == component_id, ComponentAuthentication.type == ComponentAuthenticationType.TOKEN).all()
    if 'add_own_api_token' in flask.request.form and add_own_api_token_form.validate_on_submit():
        check_current_user_is_not_readonly()
        if not flask_login.current_user.is_admin:
            return flask.abort(403)
        description = add_own_api_token_form.description.data
        try:
            add_own_token_authentication(component_id, add_own_api_token_form.token.data, description)
            own_api_tokens = OwnComponentAuthentication.query.filter(OwnComponentAuthentication.component_id == component_id, OwnComponentAuthentication.type == ComponentAuthenticationType.TOKEN).all()
        except errors.InvalidTokenError:
            flask.flash(_('Invalid token. Required length: 64 digits.'), 'error')
        except errors.TokenExistsError:
            flask.flash(_('This token has already been linked to this database.'), 'error')
        except Exception:
            flask.flash(_('Failed to add API token.'), 'error')

    active_identities = get_federated_identities(flask_login.current_user.id, component, active_status=True)
    inactive_identities = get_federated_identities(flask_login.current_user.id, component, active_status=False)

    component_address = component.address
    if component_address and not component_address.endswith('/'):
        component_address += '/'

    has_other_auth_methods = identity_not_required_for_auth(component_id)

    return flask.render_template(
        'other_databases/component.html',
        component=component,
        alias=alias,
        show_edit_form=show_edit_form,
        edit_component_form=edit_component_form,
        sync_component_form=sync_component_form,
        add_own_api_token_form=add_own_api_token_form,
        create_api_token_form=create_api_token_form,
        authentication_method_form=authentication_method_form,
        own_authentication_method_form=own_authentication_method_form,
        api_tokens=api_tokens,
        own_api_tokens=own_api_tokens,
        created_api_token=created_api_token,
        active_identities=active_identities,
        inactive_identities=inactive_identities,
        federation_user_base_url=f"{component_address}users",
        has_other_auth_methods=has_other_auth_methods
    )


@frontend.route('/other-databases/', methods=['GET', 'POST'])
@flask_login.login_required
def federation() -> FlaskResponseT:
    components = get_components()

    # federation graph
    nodes = []
    edges = []
    if flask.current_app.config['FEDERATION_UUID']:
        node = {
            'label': flask.current_app.config['SERVICE_NAME'],
            'title': flask.current_app.config['FEDERATION_UUID'],
            'borderWidth': 2
        }
        nodes_by_uuid = {
            flask.current_app.config['FEDERATION_UUID']: node
        }
        reachable_uuids = {
            flask.current_app.config['FEDERATION_UUID']
        }

        for component in components:
            if component.uuid == flask.current_app.config['FEDERATION_UUID'] or not component.discoverable:
                continue
            node = {
                'label': component.get_name(),
                'title': component.uuid
            }
            nodes_by_uuid[component.uuid] = node
            reachable_uuids.add(component.uuid)

        component_infos_by_uuid: typing.Dict[str, typing.List[ComponentInfo]] = {}
        all_component_infos = get_component_infos()
        for component_info in all_component_infos:
            if not component_info.discoverable:
                continue
            if component_info.uuid not in component_infos_by_uuid:
                component_infos_by_uuid[component_info.uuid] = []
            component_infos_by_uuid[component_info.uuid].append(component_info)
        did_update = True
        while did_update:
            did_update = False
            for uuid, component_infos in component_infos_by_uuid.items():
                if uuid in reachable_uuids:
                    continue
                for component_info in component_infos:
                    if component_info.discoverable and component_info.source_uuid in reachable_uuids:
                        reachable_uuids.add(component_info.uuid)
                        did_update = True
        for uuid, component_infos in component_infos_by_uuid.items():
            if uuid in nodes_by_uuid or uuid not in reachable_uuids:
                continue
            component_infos_by_distance: typing.Dict[int, typing.List[ComponentInfo]] = {}
            for component_info in component_infos:
                if component_info.distance not in component_infos_by_distance:
                    component_infos_by_distance[component_info.distance] = []
                component_infos_by_distance[component_info.distance].append(component_info)
            component_infos = component_infos_by_distance[min(component_infos_by_distance)]
            names = {
                component_info.name
                for component_info in component_infos
                if component_info.name
            }
            if not names:
                name = None
            elif len(names) == 1:
                name = list(names)[0]
            else:
                name = ' / '.join(sorted(names))
            node = {
                'label': name or uuid,
                'title': uuid
            }
            nodes_by_uuid[uuid] = node

        node_ids_by_uuid = {
            uuid: node_id
            for node_id, uuid in enumerate(nodes_by_uuid)
        }
        for uuid, node in nodes_by_uuid.items():
            node['id'] = node_ids_by_uuid[uuid]
        nodes = list(nodes_by_uuid.values())

        for component in components:
            if component.uuid in node_ids_by_uuid and component.discoverable:
                edges.append({
                    'from': node_ids_by_uuid[flask.current_app.config['FEDERATION_UUID']],
                    'to': node_ids_by_uuid[component.uuid],
                    'arrows': {
                        (True, True): 'from, to',
                        (True, False): 'from',
                        (False, True): 'to',
                        (False, False): None
                    }.get((component.import_token_available, component.export_token_available))
                })
        for component_info in all_component_infos:
            if component_info.source_uuid in node_ids_by_uuid and component_info.uuid in node_ids_by_uuid and component_info.discoverable:
                edges.append({
                    'from': node_ids_by_uuid[component_info.source_uuid],
                    'to': node_ids_by_uuid[component_info.uuid],
                    'dashes': True
                })

    add_component_form = AddComponentForm()
    if add_component_form.address.data is None:
        add_component_form.address.data = ''
    if add_component_form.uuid.data is None:
        add_component_form.uuid.data = ''
    if add_component_form.name.data is None:
        add_component_form.name.data = ''
    if add_component_form.description.data is None:
        add_component_form.description.data = ''
    show_add_form = False
    if 'add' in flask.request.form:
        show_add_form = True
        if add_component_form.validate_on_submit():
            check_current_user_is_not_readonly()
            try:
                name = add_component_form.name.data
                address = add_component_form.address.data
                if not flask.current_app.config['ALLOW_HTTP'] and address[:7] == 'http://':
                    add_component_form.address.errors.append(_('Only secure communication via https is allowed'))
                    return flask.render_template("other_databases/federation.html", current_user=flask_login.current_user, components=components, add_component_form=add_component_form, show_add_form=show_add_form)
                if name == '':
                    name = None
                if address == '':
                    address = None
                component_id = add_component(uuid=add_component_form.uuid.data, name=name, description=add_component_form.description.data, address=address).id
            except errors.ComponentAlreadyExistsError as err:
                if err.is_current_app:
                    add_component_form.name.errors.append(_('This UUID or name is already used by this instance (%(service_name)s)', service_name=flask.current_app.config['SERVICE_NAME']))
                    add_component_form.uuid.errors.append(_('This UUID or name is already used by this instance (%(service_name)s)', service_name=flask.current_app.config['SERVICE_NAME']))
                else:
                    add_component_form.name.errors.append(_('A database with this UUID or name has already been added'))
                    add_component_form.uuid.errors.append(_('A database with this UUID or name has already been added'))
            except errors.InvalidComponentNameError:
                add_component_form.name.errors.append(_('This database name is invalid'))
            except errors.InvalidComponentUUIDError:
                add_component_form.uuid.errors.append(_('Invalid UUID'))
            except errors.InsecureComponentAddressError:
                add_component_form.address.errors.append(_('Only secure communication via https is allowed'))
            except errors.InvalidComponentAddressError:
                add_component_form.address.errors.append(_('This database address is invalid'))
            except Exception:
                add_component_form.name.errors.append(_('Failed to add database'))
            else:
                post_poke_components_task()
                flask.flash(_('The database information has been added successfully'), 'success')
                return flask.redirect(flask.url_for('.component', component_id=component_id))
    return flask.render_template(
        "other_databases/federation.html",
        current_user=flask_login.current_user,
        components=components,
        add_component_form=add_component_form,
        show_add_form=show_add_form,
        nodes=nodes,
        edges=edges,
    )


@frontend.route('/other-databases/alias/', methods=['GET', 'POST'])
@flask_login.login_required
def user_alias() -> FlaskResponseT:
    user = flask_login.current_user
    components = get_components()
    aliases = get_user_aliases_for_user(user.id)
    added_components = [alias.component_id for alias in aliases]
    addable_components = [comp for comp in components if comp.id not in added_components]
    try:
        add_alias_component = int(flask.request.args.get('add_alias_component', ''))
        check_component_exists(add_alias_component)
    except ValueError:
        add_alias_component = None
    except TypeError:
        add_alias_component = None
    except errors.ComponentDoesNotExistError:
        add_alias_component = None
    add_alias_form = AddAliasForm()
    add_alias_form.component.choices = [
        (str(comp.id), comp.name)
        for comp in components if comp.id not in added_components
    ]

    edit_alias_form = EditAliasForm()

    delete_alias_form = DeleteAliasForm()

    show_edit_form = False

    if 'edit' in flask.request.form:
        show_edit_form = True
        if edit_alias_form.validate_on_submit():
            try:
                update_user_alias(
                    user.id, edit_alias_form.component.data,
                    edit_alias_form.name.data if edit_alias_form.name.data != '' and not edit_alias_form.use_real_name.data else None,
                    edit_alias_form.use_real_name.data,
                    None,
                    edit_alias_form.use_real_email.data,
                    None,
                    edit_alias_form.use_real_orcid.data,
                    edit_alias_form.affiliation.data if edit_alias_form.affiliation.data != '' and not edit_alias_form.use_real_affiliation.data else None,
                    edit_alias_form.use_real_affiliation.data,
                    edit_alias_form.role.data if edit_alias_form.role.data != '' and not edit_alias_form.use_real_role.data else None,
                    edit_alias_form.use_real_role.data,
                )
            except errors.ComponentDoesNotExistError:
                flask.flash(_('That database does not exist.'), 'error')
            except errors.UserAliasDoesNotExistError:
                flask.flash(_('There is no alias for this database.'), 'error')
            else:
                flask.flash(_('User alias updated successfully.'), 'success')
                return flask.redirect(flask.url_for('.user_alias'))
    if 'add' in flask.request.form:
        if add_alias_form.validate_on_submit():
            create_user_alias(
                user.id, add_alias_form.component.data,
                add_alias_form.name.data if add_alias_form.name.data != '' and not add_alias_form.use_real_name.data else None,
                add_alias_form.use_real_name.data,
                None,
                add_alias_form.use_real_email.data,
                None,
                add_alias_form.use_real_orcid.data,
                add_alias_form.affiliation.data if add_alias_form.affiliation.data != '' and not add_alias_form.use_real_affiliation.data else None,
                add_alias_form.use_real_affiliation.data,
                add_alias_form.role.data if add_alias_form.role.data != '' and not add_alias_form.use_real_role.data else None,
                add_alias_form.use_real_role.data,
            )
            flask.flash(_('User alias updated successfully.'), 'success')
            return flask.redirect(flask.url_for('.user_alias'))
    if 'delete' in flask.request.form:
        if delete_alias_form.validate_on_submit():
            try:
                delete_user_alias(flask_login.current_user.id, edit_alias_form.component.data)
            except errors.ComponentDoesNotExistError:
                flask.flash(_('That database does not exist.'), 'error')
            except errors.UserAliasDoesNotExistError:
                flask.flash(_('The alias for this database has already been deleted.'), 'error')
            else:
                flask.flash(_('User alias updated successfully.'), 'success')
                return flask.redirect(flask.url_for('.user_alias'))

    if add_alias_form.name.data is None:
        add_alias_form.name.data = user.name
    if add_alias_form.affiliation.data is None:
        add_alias_form.affiliation.data = user.affiliation
    if add_alias_form.role.data is None:
        add_alias_form.role.data = user.role
    if add_alias_component and not add_alias_form.is_submitted():
        add_alias_form.component.data = add_alias_component

    aliases_by_component = {
        alias.component_id: {
            'is_default': alias.is_default,
            'name': alias.name if alias.name is not None else '',
            'email': alias.email if alias.email is not None else '',
            'orcid': alias.orcid if alias.orcid is not None else '',
            'affiliation': alias.affiliation if alias.affiliation is not None else '',
            'role': alias.role if alias.role is not None else '',
            'use_real_name': alias.use_real_name,
            'use_real_email': alias.use_real_email,
            'use_real_orcid': alias.use_real_orcid,
            'use_real_affiliation': alias.use_real_affiliation,
            'use_real_role': alias.use_real_role,
        } for alias in aliases}

    user_data = {
        'name': user.name if user.name is not None else '',
        'email': user.email if user.email is not None else '',
        'orcid': user.orcid if user.orcid is not None else '',
        'affiliation': user.affiliation if user.affiliation is not None else '',
        'role': user.role if user.role is not None else ''
    }

    component_names = {component.id: component.get_name() for component in components}

    return flask.render_template(
        "other_databases/federation_alias.html",
        user=user,
        addable_components=addable_components,
        aliases=aliases,
        add_alias_form=add_alias_form if addable_components else None,
        edit_alias_form=edit_alias_form,
        delete_alias_form=delete_alias_form,
        aliases_by_component=aliases_by_component,
        user_data=user_data,
        component_names=component_names,
        show_edit_form=show_edit_form
    )


@frontend.route("/other-databases/redirect-identity-confirmation/<string:component>", methods=["POST"])
@flask_login.login_required
def redirect_login_confirmation(component: str) -> FlaskResponseT:
    try:
        database = get_component_by_uuid(component)
    except errors.InvalidComponentUUIDError:
        return flask.redirect(flask.url_for("frontend.federation"))
    serializer = itsdangerous.URLSafeTimedSerializer(secret_key=flask.current_app.config['SECRET_KEY'], salt='federated-identities')
    session_state = hashlib.sha256(os.urandom(1024)).hexdigest()
    flask.session['fim_state'] = session_state
    link_identity_token = serializer.dumps({'user_id': flask_login.current_user.id, 'state': session_state})

    component_address = database.address
    if component_address and not component_address.endswith('/'):
        component_address += '/'

    all_fed_identities = get_federated_identities(user_id=flask_login.current_user.id, component=database)
    all_component_fed_ids = {identity.local_fed_user.fed_id for identity in get_federated_identities(component=database)}
    different_linked_ids = all_component_fed_ids.difference(identity.local_fed_user.fed_id for identity in all_fed_identities)

    url_enc_verified_fed_identities = ",".join(str(identity.local_fed_user.fed_id) for identity in all_fed_identities if identity.login)
    url_enc_unverified_fed_identities = ",".join(str(identity.local_fed_user.fed_id) for identity in all_fed_identities if not identity.login)
    url_enc_different_linked_fed_identities = ",".join(str(id) for id in different_linked_ids)

    redirect_url = f"{component_address}other-databases/link-identity?source_db={flask.current_app.config['FEDERATION_UUID']}&token={str(link_identity_token)}&state={session_state}"

    if url_enc_verified_fed_identities:
        redirect_url += f"&verified_ids={url_enc_verified_fed_identities}"
    if url_enc_unverified_fed_identities:
        redirect_url += f"&unverified_ids={url_enc_unverified_fed_identities}"
    if url_enc_different_linked_fed_identities:
        redirect_url += f"&linked_ids={url_enc_different_linked_fed_identities}"

    return flask.redirect(redirect_url)


@frontend.route("/other-databases/finalize-link-identity/", methods=["GET"])
def link_identity() -> FlaskResponseT:
    identity_token = flask.request.args.get('token')
    federation_partner_uuid = flask.request.args.get('federation_partner_uuid')

    serializer = itsdangerous.URLSafeTimedSerializer(secret_key=flask.current_app.config['SECRET_KEY'], salt='federated-identities')

    if not federation_partner_uuid:
        flask.flash(_("An error occurred: Invalid database UUID."), 'error')
        return flask.redirect(flask.url_for(".federation"))

    try:
        federation_partner = get_component_by_uuid(federation_partner_uuid)
    except errors.InvalidComponentUUIDError:
        flask.flash(_("Unknown database (%(uuid)s)", uuid=federation_partner_uuid), 'error')
        return flask.redirect(flask.url_for('.federation'))

    federation_partner_address = federation_partner.address
    if federation_partner_address and not federation_partner_address.endswith('/'):
        federation_partner_address += '/'
    result = requests.get(f"{federation_partner_address}other-databases/validate-identity-token/?token={identity_token}", timeout=60)
    if result.status_code != 200:
        return flask.redirect(flask.url_for(".federation"))

    result_json = result.json()
    token = result_json.get('token')
    fed_user_id = result_json.get('fed_user')

    try:
        token_data = serializer.loads(token, max_age=FEDERATED_IDENTITY_TOKENS_MAX_AGE)
    except itsdangerous.BadSignature:
        flask.flash(_("An error occurred: Users could not be linked."), 'error')
        return flask.redirect(flask.url_for(".federation"))

    if 'fim_state' not in flask.session or flask.session['fim_state'] != token_data['state']:
        flask.flash(_("An error occurred: Users could not be linked."), 'error')
        return flask.redirect(flask.url_for(".federation"))

    try:
        federation_user = get_user(user_id=fed_user_id, component_id=federation_partner.id)
        identity = get_federated_identity(token_data['user_id'], federation_user.id)
    except (errors.FederatedIdentityNotFoundError, errors.UserDoesNotExistError):
        identity = None

    try:
        if identity is None or not identity.active:
            create_sampledb_federated_identity(token_data['user_id'], federation_partner, fed_user_id, update_if_inactive=True, use_for_login=True)
            flask.flash(_("You were successfully linked with a federated user from %(component_name)s.", component_name=federation_partner.get_name()), 'success')
        else:
            enable_federated_identity_for_login(identity)
            flask.flash(_("The identity was successfully verified."), 'success')
    except errors.FederatedUserInFederatedIdentityError:
        flask.flash(_("The federated user already has a federated identity in this database."), 'error')

    return flask.redirect(flask.url_for('.component', component_id=federation_partner.id))


@frontend.route("/other-databases/redirect-uuid/<string:component>", methods=["GET"])
def redirect_by_federation_uuid(component: str) -> FlaskResponseT:
    try:
        database = get_component_by_uuid(component_uuid=component)
    except errors.ComponentDoesNotExistError:
        return flask.redirect(flask.url_for('.federation'))
    return flask.redirect(flask.url_for('.component', component_id=database.id))


@frontend.route("/other-databases/link-identity/", methods=["GET"])
@flask_login.login_required
def confirm_identity() -> FlaskResponseT:
    source_database_uuid = flask.request.args.get('source_db', '')
    token = flask.request.args.get('token')

    def int_or_none(s: str) -> typing.Optional[int]:
        try:
            return int(s)
        except ValueError:
            return None

    form_verified_ids = flask.request.args.get('verified_ids')
    form_unverified_ids = flask.request.args.get('unverified_ids')
    form_linked_ids = flask.request.args.get('linked_ids')
    verified_ids = [int_or_none(id) for id in form_verified_ids.split(',')] if form_verified_ids else []
    unverified_ids = [int_or_none(id) for id in form_unverified_ids.split(',')] if form_unverified_ids else []
    linked_ids = [int_or_none(id) for id in form_linked_ids.split(',')] if form_linked_ids else []
    serializer = itsdangerous.URLSafeTimedSerializer(secret_key=flask.current_app.config['SECRET_KEY'], salt='identity-token-validation')

    source_database = None

    try:
        source_database = get_component_by_uuid(source_database_uuid)
    except (errors.InvalidComponentUUIDError, errors.ComponentDoesNotExistError):
        flask.flash(_('Could not confirm identity: The databases are not in a federation.'), 'error')
        return flask.redirect(flask.url_for('.index'))

    identity_token = serializer.dumps({'fed_user': flask_login.current_user.id, 'token': token})
    component_address = source_database.address
    if component_address and not component_address.endswith('/'):
        component_address += '/'

    confirmation_url = f"{component_address}other-databases/finalize-link-identity"
    cancel_url = f"{component_address}other-databases/redirect-uuid/{flask.current_app.config['FEDERATION_UUID']}"

    verified_linked = flask_login.current_user.id in verified_ids
    unverified_linked = flask_login.current_user.id in unverified_ids
    linked = flask_login.current_user.id in linked_ids

    return flask.render_template(
        "other_databases/confirm_identity.html",
        source_database=source_database,
        confirmation_url=confirmation_url,
        cancel_url=cancel_url,
        identity_token=identity_token,
        verified_linked=verified_linked,
        unverified_linked=unverified_linked,
        linked=linked
    )


@frontend.route("/other-databases/validate-identity-token/", methods=["GET"])
def validate_identity_token() -> FlaskResponseT:
    identity_token = flask.request.args.get('token')

    if not identity_token:
        return flask.Response({}, mimetype='application/json', status=400)

    serializer = itsdangerous.URLSafeTimedSerializer(secret_key=flask.current_app.config['SECRET_KEY'], salt='identity-token-validation')

    try:
        data = serializer.loads(identity_token, max_age=FEDERATED_IDENTITY_TOKENS_MAX_AGE)
    except itsdangerous.BadSignature:
        return flask.Response({}, mimetype='application/json', status=400)

    return flask.jsonify(data)


@frontend.route("/other-databases/delete-inactive-identities/<int:component_id>", methods=["POST"])
@flask_login.login_required
def delete_inactive_identities(component_id: int) -> FlaskResponseT:
    try:
        component = get_component(component_id)
        fed_ids: list[int] = [int(val) for val in flask.request.form.getlist('local_fed_id')]
    except (errors.ComponentDoesNotExistError, ValueError):
        flask.flash(_('Failed to remove user links.'), 'error')
        return flask.redirect(flask.url_for(".component", component_id=component_id))

    if fed_ids:
        delete_user_links_by_fed_ids(flask_login.current_user.id, component, fed_ids)

    return flask.redirect(flask.url_for(".component", component_id=component_id))


@frontend.route("/other-databases/revoke-active-identities/<int:component_id>", methods=["POST"])
@flask_login.login_required
def revoke_active_identities(component_id: int) -> FlaskResponseT:
    try:
        component = get_component(component_id)
        fed_ids: list[int] = [int(val) for val in flask.request.form.getlist('local_fed_id')]
    except (errors.ComponentDoesNotExistError, ValueError):
        flask.flash(_('Failed to revoke user links.'), 'error')
        return flask.redirect(flask.url_for(".component", component_id=component_id))

    if fed_ids:
        try:
            revoke_user_links_by_fed_ids(flask_login.current_user.id, component.id, fed_ids)
        except errors.NoAuthenticationMethodError:
            flask.flash(_('You must keep at least one federated identity to login or add another authentication method first.'), 'error')

    return flask.redirect(flask.url_for(".component", component_id=component_id))


@frontend.route("/other-databases/edit-eln-identity/<int:eln_import_id>", methods=['POST'])
@flask_login.login_required
def modify_eln_identity(eln_import_id: int) -> FlaskResponseT:
    modify_eln_identity_form = ModifyELNIdentityForm()

    if modify_eln_identity_form.validate_on_submit():
        try:
            fed_identity = get_federated_identity(flask_login.current_user.id, eln_or_fed_user_id=modify_eln_identity_form.eln_user_id.data)
        except errors.FederatedIdentityNotFoundError:
            flask.flash(_('An error occurred: Failed to edit federated identity.'), 'error')
            return flask.redirect(flask.url_for('.eln_import', eln_import_id=eln_import_id))

        if modify_eln_identity_form.type.data == 'remove':
            delete_user_link(flask_login.current_user.id, fed_identity.local_fed_id)
            flask.flash(_('Successfully deleted user link.'), 'success')
        elif modify_eln_identity_form.type.data == 'revoke':
            revoke_user_link(flask_login.current_user.id, fed_identity.local_fed_id)
            flask.flash(_('Successfully revoked user link.'), 'success')
        elif modify_eln_identity_form.type.data == 'enable':
            enable_user_link(flask_login.current_user.id, fed_identity.local_fed_id)
            flask.flash(_('Successfully enabled user link.'), 'success')
    else:
        flask.flash(_('An error occurred: Failed to edit federated identity.'), 'error')
    return flask.redirect(flask.url_for('.eln_import', eln_import_id=eln_import_id))


@frontend.route("/federated-login/sp/<int:component_id>", methods=['POST', 'GET'])
@federated_login_route
def federated_login(component_id: int) -> FlaskResponseT:
    try:
        component = get_component(component_id)
    except errors.ComponentDoesNotExistError:
        return flask.redirect(flask.url_for("frontend.sign_in"))

    if not component.fed_login_available:
        flask.flash(_('The federated login is not available for %(component_name)s.', component_name=component.get_name()), 'error')
        return flask.redirect(flask.url_for("frontend.sign_in"))

    is_shared_device = bool(flask.request.form.get('shared_device'))

    try:
        redirect = sp_login(component, shared_device=is_shared_device)
    except errors.FailedMetadataFetchingError:
        flask.flash(_("%(component_name)s disabled the federated login.", component_name=component.get_name()), 'error')
        return flask.redirect(flask.url_for('frontend.sign_in'))
    except errors.InvalidSAMLRequestError:
        flask.flash(_("Failed to use federated login. Please contact an administrator."), 'error')
        return flask.redirect(flask.url_for('frontend.sign_in'))
    return redirect


@frontend.route("/federated-login/sp/metadata.xml/<string:component>", methods=['GET'])
@federated_login_route
def service_provider_metadata(component: str) -> FlaskResponseT:
    try:
        database = get_component_by_uuid(component)
    except errors.ComponentDoesNotExistError:
        return flask.redirect(flask.url_for("frontend.sign_in"))

    return flask.Response(get_sp_metadata(database), mimetype="text/xml")


@frontend.route("/federated-login/sp/acs", methods=['GET'])
@federated_login_route
def assertion_consumer_service() -> FlaskResponseT:
    args = flask.request.args
    if 'SAMLart' not in args and 'current_saml_artifact' not in flask.session:
        flask.flash(_('An error occurred: Failed to use federated login. Please try again.'), 'error')
        return flask.redirect(flask.url_for('frontend.sign_in'))

    if 'SAMLart' in args:
        saml_artifact = args['SAMLart']
        flask.session['current_saml_artifact'] = args['SAMLart']
    else:
        saml_artifact = flask.session['current_saml_artifact']

    try:
        federated_user_information = resolve_artifact(saml_artifact)
    except errors.MismatchedResponseToRequestError:
        flask.flash(_('An error occurred: The authentication could not be verified. Please try again.'), 'error')
        return flask.redirect(flask.url_for('.sign_in'))

    if 'saml_sso_component' not in flask.session:
        flask.flash(_('Failed to use federated login. Please try again.'), 'error')
        return flask.redirect(flask.url_for("frontend.sign_in"))

    component = get_component_by_uuid(flask.session['saml_sso_component'])

    try:
        fed_user = get_user(int(federated_user_information["uid"]), component.id)
    except errors.UserDoesNotExistError:
        fed_user = create_user(name=None, email=None, type=UserType.FEDERATION_USER, component_id=component.id, fed_id=int(federated_user_information["uid"]))
        set_user_hidden(fed_user.id, hidden=True)

    local_user = get_user_by_federated_user(fed_user.id, login=True)

    if local_user is not None:
        flask_login.login_user(local_user)
        return flask.redirect(flask.url_for('.index'))

    federated_identity_exists = get_active_federated_identity_by_federated_user(federated_user_id=fed_user.id) is not None

    flask.session['saml_sso_user_details'] = {
        "fed_user_id": fed_user.fed_id,
        "component_id": fed_user.component_id,
        "user_email": federated_user_information['email']
    }

    authentication_mails = [auth.login['login'] for auth in Authentication.query.filter_by(type=AuthenticationType.EMAIL).all()]
    user_by_email = User.query.filter_by(email=federated_user_information['email']).first()

    if federated_identity_exists:
        flask.flash(_('The federated user already has a federated identity in this database which is not verified. Please sign in to the corresponding user.'), 'info')
    elif user_by_email or federated_user_information['email'] in authentication_mails:
        flask.flash(_('A user with this email address exists already. If you own this account, please use the sign in.'), 'info')

    create_user_form = FederatedUserCreationForm()
    serializer = itsdangerous.URLSafeTimedSerializer(secret_key=flask.current_app.config['SECRET_KEY'], salt='federated-identities')
    federated_login_token = serializer.dumps((fed_user.fed_id, fed_user.component_id))

    return flask.render_template(
        "other_databases/federated_login.html",
        component=component,
        has_errors=False,
        federated_user_information=federated_user_information,
        allow_create_user=flask.current_app.config['ENABLE_FEDERATED_LOGIN_CREATE_NEW_USER'] and not federated_identity_exists,
        create_user_form=create_user_form,
        federated_login_token=federated_login_token,
        not_verified=federated_identity_exists
    )


@frontend.route("/federated-login/idp/verify", methods=['GET', 'POST'])
@federated_login_route
@login_required_saml
def federated_login_verify() -> FlaskResponseT:
    form_data: dict[str, typing.Any] = {}
    form_data.update(flask.request.args)
    if 'SAMLRequest' in flask.session:
        form_data.update({
            'SAMLRequest': flask.session['SAMLRequest']
        })
        del flask.session['SAMLRequest']

    try:
        response = process_login(form_data)
    except errors.InvalidSAMLRequestError:
        flask.flash(_('Failed to verify the authentication request. Please try again or contact an administrator. If you are an administrator, follow the <a href="%(docs_url)s">documentation</a>.', docs_url="https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/administrator_guide/federation.html#federated-login"), "error-url")
        return flask.redirect(flask.url_for('.index'))

    if response is None:
        flask.flash(_('Failed to use federated login because of missing metadata. Please contact an administrator. If you are an administrator, follow the <a href="%(docs_url)s">documentation</a>.', docs_url="https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/administrator_guide/federation.html#federated-login"), 'error-url')
        return flask.redirect(flask.url_for('.index'))
    return response


@frontend.route("/federated-login/idp/metadata.xml", methods=['GET'])
@federated_login_route
def identity_provider_metadata() -> FlaskResponseT:
    return flask.Response(get_idp_metadata(), mimetype="text/xml")


@frontend.route("/federated-login/idp/ars", methods=['POST'])
@federated_login_route
def artifact_resolution_service() -> FlaskResponseT:
    try:
        response = eval_artifact_resolve(flask.request.data)
    except Exception:
        return flask.Response("Artifact not found", status=404)
    delete_old_artifacts()
    return flask.Response(response=response['data'], headers=response['headers'])


@frontend.route("/federated-login/sp/finalize", methods=['POST'])
@federated_login_route
def finalize_federated_login() -> FlaskResponseT:
    create_user_form = FederatedUserCreationForm()
    sso_details = flask.session['saml_sso_user_details']

    if create_user_form.validate_on_submit():
        mail_status_send = send_federated_login_account_creation_email(
            email=sso_details['user_email'],
            username=create_user_form.username.data,
            component_id=sso_details['component_id'],
            fed_id=sso_details['fed_user_id']
        )[0]

        if mail_status_send == BackgroundTaskStatus.FAILED:
            flask.flash(_("Sending an email failed. Please try again later or contact an administrator."), 'error')
        else:
            flask.flash(_("Please see your email to confirm this mail address and create the user."), 'success')

    else:
        flask.flash(_('The selected username is not valid: %(error)s', error=create_user_form.username.errors[0]), 'error')
        return flask.redirect(flask.url_for('.assertion_consumer_service'))
    return flask.redirect(flask.url_for('.index'))


@frontend.route("/federated-login/create-account/<string:token>", methods=['GET'])
@federated_login_route
def create_account_by_federated_login(token: str) -> FlaskResponseT:
    serializer = itsdangerous.URLSafeTimedSerializer(secret_key=flask.current_app.config['SECRET_KEY'], salt='federated_login_account')
    try:
        token_data = serializer.loads(token, max_age=flask.current_app.config['INVITATION_TIME_LIMIT'])
    except itsdangerous.BadData:
        flask.flash(_("Invalid token. Please login again."), 'error')
        return flask.redirect(flask.url_for('.index'))

    try:
        federated_user = get_user(user_id=token_data['fed_id'], component_id=token_data['component_id'])
    except errors.UserDoesNotExistError:
        federated_user = None

    if federated_user is not None and get_user_by_federated_user(federated_user_id=federated_user.id):
        flask.flash(_("The federated user already has a local federated identity. Please login with this user."), 'error')
        return flask.redirect(flask.url_for('.index'))

    local_user = create_user(
        name=token_data['username'],
        email=token_data['email'],
        type=UserType.PERSON
    )

    create_sampledb_federated_identity(
        user_id=local_user.id,
        component=get_component(component_id=token_data['component_id']),
        fed_id=token_data['fed_id'],
        use_for_login=True
    )

    flask.flash(_("The user was successfully created. Please sign in."), 'success')
    return flask.render_template('sign_in.html',
                                 saml_user_creation=True,
                                 component=get_component(token_data['component_id']),
                                 )
