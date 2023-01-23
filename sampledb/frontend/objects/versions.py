# coding: utf-8
"""

"""

import flask
import flask_login
from flask_babel import _

from .. import frontend
from ... import logic
from ...logic.actions import get_action_type, get_action
from ...logic.object_permissions import Permissions, get_user_object_permissions
from ...logic.settings import get_user_setting
from ...logic.objects import get_object, get_object_versions, get_current_object_version_id
from ...logic.languages import get_language_by_lang_code, get_languages_in_object_data, get_language, Language
from ...logic.errors import ObjectDoesNotExistError, ValidationError
from ...logic.components import get_component
from ...logic.utils import get_translated_text
from .forms import ObjectVersionRestoreForm
from ...utils import object_permissions_required
from ..utils import get_user_if_exists
from .permissions import on_unauthorized, get_object_if_current_user_has_read_permissions


@frontend.route('/objects/<int:object_id>/versions/')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_versions(object_id):
    object = get_object(object_id=object_id)
    if object is None:
        return flask.abort(404)
    object_versions = get_object_versions(object_id=object_id)
    object_versions.sort(key=lambda object_version: -object_version.version_id)
    return flask.render_template('objects/object_versions.html', get_user=get_user_if_exists, object=object, object_versions=object_versions)


@frontend.route('/objects/<int:object_id>/versions/<int:version_id>')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_version(object_id, version_id):
    english = get_language(Language.ENGLISH)
    object = get_object(object_id=object_id, version_id=version_id)
    current_version_id = get_current_object_version_id(object_id=object_id)
    form = None
    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    if Permissions.WRITE in user_permissions:
        current_object = get_object(object_id=object_id)
        if current_object.version_id != version_id:
            form = ObjectVersionRestoreForm()
    user_may_grant = Permissions.GRANT in user_permissions
    action = get_action(object.action_id)
    action_type = get_action_type(action.type_id) if action.type_id else None
    instrument = action.instrument

    object_languages = get_languages_in_object_data(object.data)
    languages = []
    for lang_code in object_languages:
        languages.append(get_language_by_lang_code(lang_code))

    metadata_language = flask.request.args.get('language', None)
    if not any(
        language.lang_code == metadata_language
        for language in languages
    ):
        metadata_language = None
    return flask.render_template(
        'objects/view/base.html',
        template_mode="view",
        show_object_type_and_id_on_object_page_text=get_user_setting(flask_login.current_user.id, "SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE"),
        show_object_title=get_user_setting(flask_login.current_user.id, "SHOW_OBJECT_TITLE"),
        languages=languages,
        metadata_language=metadata_language,
        ENGLISH=english,
        is_archived=True,
        object=object,
        object_type=get_translated_text(action_type.object_name) if action_type is not None else None,
        action=action,
        action_type=action_type,
        instrument=instrument,
        schema=object.schema,
        data=object.data,
        name=object.name,
        get_object_if_current_user_has_read_permissions=get_object_if_current_user_has_read_permissions,
        object_id=object_id,
        version_id=version_id,
        current_version_id=current_version_id,
        link_version_specific_rdf=True,
        restore_form=form,
        get_user=get_user_if_exists,
        user_may_grant=user_may_grant,
        get_action_type=get_action_type,
        component=object.component,
        fed_object_id=object.fed_object_id,
        fed_version_id=object.fed_version_id,
        get_component=get_component
    )


@frontend.route('/objects/<int:object_id>/versions/<int:version_id>/restore', methods=['GET', 'POST'])
@object_permissions_required(Permissions.WRITE)
def restore_object_version(object_id, version_id):
    if version_id < 0 or object_id < 0:
        return flask.abort(404)
    try:
        current_object = get_object(object_id=object_id)
    except ObjectDoesNotExistError:
        return flask.abort(404)
    if current_object.version_id <= version_id:
        return flask.abort(404)
    form = ObjectVersionRestoreForm()
    if form.validate_on_submit():
        try:
            logic.objects.restore_object_version(object_id=object_id, version_id=version_id, user_id=flask_login.current_user.id)
        except ValidationError:
            flask.flash(_('This version contains invalid data and cannot be restored.'), 'error')
        else:
            return flask.redirect(flask.url_for('.object', object_id=object_id))
    return flask.render_template('objects/restore_object_version.html', object_id=object_id, version_id=version_id, restore_form=form)
