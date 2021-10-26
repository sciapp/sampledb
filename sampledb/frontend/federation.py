# coding: utf-8
"""

"""
import secrets
import flask
import flask_login
import requests.exceptions

from flask_babel import _

from . import frontend
from .federation_forms import AddComponentForm, EditComponentForm, SyncComponentForm, CreateAPITokenForm, \
    AddOwnAPITokenForm, AuthenticationMethodForm, AddAliasForm, EditAliasForm, DeleteAliasForm
from ..logic import errors
from .utils import check_current_user_is_not_readonly
from ..logic.component_authentication import remove_component_authentication_method, add_token_authentication, remove_own_component_authentication_method, add_own_token_authentication
from ..logic.components import get_component, update_component, add_component, get_components, check_component_exists
from ..logic.federation.update import import_updates
from ..logic.users import get_user_aliases_for_user, create_user_alias, update_user_alias, delete_user_alias, \
    get_user_alias
from ..models import OwnComponentAuthentication, ComponentAuthenticationType, ComponentAuthentication


@frontend.route('/other-databases/<int:component_id>', methods=['GET', 'POST'])
@flask_login.login_required
def component(component_id):
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
                edit_component_form.name.errors.append(_('Failed to add database'))
            else:
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
        created_api_token=created_api_token
    )


@frontend.route('/other-databases/', methods=['GET', 'POST'])
@flask_login.login_required
def federation():
    components = get_components()
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
            except errors.ComponentAlreadyExistsError:
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
                flask.flash(_('The database information has been added successfully'), 'success')
                return flask.redirect(flask.url_for('.component', component_id=component_id))
    return flask.render_template("other_databases/federation.html", current_user=flask_login.current_user, components=components, add_component_form=add_component_form, show_add_form=show_add_form)


@frontend.route('/other-databases/alias/', methods=['GET', 'POST'])
@flask_login.login_required
def user_alias():
    user = flask_login.current_user
    components = get_components()
    aliases = get_user_aliases_for_user(user.id)
    added_components = [alias.component_id for alias in aliases]
    addable_components = [comp for comp in components if comp.id not in added_components]
    try:
        add_alias_component = int(flask.request.args.get('add_alias_component'))
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

    if len(addable_components) == 0:
        add_alias_form = None
    else:
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
        add_alias_form=add_alias_form,
        edit_alias_form=edit_alias_form,
        delete_alias_form=delete_alias_form,
        aliases_by_component=aliases_by_component,
        user_data=user_data,
        component_names=component_names,
        show_edit_form=show_edit_form
    )
