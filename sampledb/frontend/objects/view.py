# coding: utf-8
"""

"""
import datetime
import io
import json
import math

import flask
import flask_login
import itsdangerous
from flask_babel import _

from .. import frontend
from ... import logic
from ... import models
from ... import db
from ...logic import object_log, comments
from ...logic.actions import get_action, get_actions, get_action_type, get_action_types
from ...logic.action_type_translations import get_action_type_with_translation_in_language
from ...logic.action_translations import get_action_with_translation_in_language
from ...logic.action_permissions import get_user_action_permissions, get_sorted_actions_for_user
from ...logic.object_permissions import Permissions, get_user_object_permissions, get_objects_with_permissions, get_object_info_with_permissions
from ...logic.instrument_translations import get_instrument_with_translation_in_language
from ...logic.users import get_user, get_users
from ...logic.settings import get_user_settings
from ...logic.objects import get_object
from ...logic.object_log import ObjectLogEntryType
from ...logic.projects import get_project
from ...logic.locations import get_location, get_object_location_assignment, get_object_location_assignments, assign_location_to_object, get_locations_tree
from ...logic.location_permissions import get_locations_with_user_permissions
from ...logic.languages import get_language_by_lang_code, get_language, get_languages, Language, get_user_language
from ...logic.files import FileLogEntryType
from ...logic.errors import ObjectDoesNotExistError, ActionDoesNotExistError
from ...logic.components import get_component
from ...logic.notebook_templates import get_notebook_templates
from .forms import ObjectForm, CommentForm, FileForm, FileInformationForm, FileHidingForm, ObjectLocationAssignmentForm, ExternalLinkForm, ObjectPublicationForm
from ...utils import object_permissions_required
from ..utils import generate_qrcode, get_user_if_exists
from ..labels import create_labels, PAGE_SIZES, DEFAULT_PAPER_FORMAT, HORIZONTAL_LABEL_MARGIN, VERTICAL_LABEL_MARGIN, mm
from .. import pdfexport
from ..utils import check_current_user_is_not_readonly, get_location_name
from ...logic.utils import get_translated_text
from .permissions import on_unauthorized, get_object_if_current_user_has_read_permissions, get_fed_object_if_current_user_has_read_permissions
from .object_form import show_object_form


def build_object_location_assignment_confirmation_url(object_location_assignment_id: int) -> str:
    confirmation_url = flask.url_for(
        'frontend.accept_responsibility_for_object',
        t=logic.security_tokens.generate_token(
            object_location_assignment_id,
            salt='confirm_responsibility',
            secret_key=flask.current_app.config['SECRET_KEY']
        ),
        _external=True
    )
    return confirmation_url


def get_project_if_it_exists(project_id):
    try:
        return get_project(project_id)
    except logic.errors.ProjectDoesNotExistError:
        return None


def show_inline_edit(obj, action, related_objects_tree):
    # Set view attributes
    user_language_id = get_user_language(flask_login.current_user).id
    english = get_language(Language.ENGLISH)

    object_id = obj.id

    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    user_may_grant = Permissions.GRANT in user_permissions
    user_may_use_as_template = Permissions.READ in get_user_action_permissions(obj.action_id, user_id=flask_login.current_user.id)

    new_schema_available = True if action.schema != obj.schema else False

    instrument = get_instrument_with_translation_in_language(action.instrument_id,
                                                             user_language_id) if action.instrument else None
    object_type = get_action_type_with_translation_in_language(
        action_type_id=action.type_id,
        language_id=user_language_id
    ).translation.object_name
    object_log_entries = object_log.get_object_log_entries(object_id=obj.id, user_id=flask_login.current_user.id)

    dataverse_enabled = bool(flask.current_app.config['DATAVERSE_URL'])
    if dataverse_enabled:
        dataverse_url = logic.dataverse_export.get_dataverse_url(obj.id)
        show_dataverse_export = not dataverse_url
    else:
        dataverse_url = None
        show_dataverse_export = False

    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
    token = serializer.dumps([flask_login.current_user.id, object_id])
    mobile_upload_url = flask.url_for('.mobile_file_upload', object_id=object_id, token=token, _external=True)
    mobile_upload_qrcode = generate_qrcode(mobile_upload_url, should_cache=False)
    object_url = flask.url_for('.object', object_id=object_id, _external=True)
    object_qrcode = generate_qrcode(object_url, should_cache=True)

    readable_location_ids = [
        location.id
        for location in get_locations_with_user_permissions(flask_login.current_user.id, Permissions.READ)
    ]
    location_form = ObjectLocationAssignmentForm()
    locations_map, locations_tree = get_locations_tree()
    locations = [('-1', '—')]
    unvisited_location_ids_prefixes_and_subtrees = [
        (location_id, '', locations_tree[location_id])
        for location_id in locations_tree
    ]
    while unvisited_location_ids_prefixes_and_subtrees:
        location_id, prefix, subtree = unvisited_location_ids_prefixes_and_subtrees.pop(0)
        location = locations_map[location_id]
        # skip unreadable locations, but allow processing their child locations
        # in case any of them are readable
        if location_id in readable_location_ids:
            locations.append((str(location_id), prefix + get_location_name(location, include_id=True)))
        prefix = f'{prefix}{get_location_name(location)} / '
        for location_id in sorted(subtree, key=lambda location_id: get_location_name(locations_map[location_id]), reverse=True):
            unvisited_location_ids_prefixes_and_subtrees.insert(
                0, (location_id, prefix, subtree[location_id])
            )

    location_form.location.choices = locations
    possible_responsible_users = [('-1', '—')]
    user_is_fed = {}
    for user in logic.users.get_users(exclude_hidden=True):
        possible_responsible_users.append((str(user.id), '{} (#{})'.format(user.name, user.id)))
        user_is_fed[str(user.id)] = user.fed_id is not None
    location_form.responsible_user.choices = possible_responsible_users

    measurement_actions = logic.action_translations.get_actions_with_translation_in_language(
        user_language_id,
        models.ActionType.MEASUREMENT,
        use_fallback=True
    )
    favorite_action_ids = logic.favorites.get_user_favorite_action_ids(flask_login.current_user.id)
    favorite_measurement_actions = [
        action
        for action in measurement_actions
        if action.id in favorite_action_ids and not action.is_hidden
    ]
    # Sort by: instrument name (independent actions first), action name
    favorite_measurement_actions.sort(key=lambda action: (
        action.user.name.lower() if action.user else '',
        get_instrument_with_translation_in_language(action.instrument_id,
                                                    user_language_id).translation.name.lower() if action.instrument else '',
        action.translation.name.lower()
    ))

    publication_form = ObjectPublicationForm()

    object_publications = logic.publications.get_publications_for_object(object_id=obj.id)
    user_may_link_publication = True

    notebook_templates = get_notebook_templates(
        object_id=obj.id,
        data=obj.data,
        schema=obj.schema,
        user_id=flask_login.current_user.id
    )

    linked_project = logic.projects.get_project_linked_to_object(object_id)

    object_languages = logic.languages.get_languages_in_object_data(obj.data)
    languages = []
    for lang_code in object_languages:
        languages.append(get_language_by_lang_code(lang_code))

    all_languages = get_languages()
    metadata_language = flask.request.args.get('language', None)
    if not any(
            language.lang_code == metadata_language
            for language in languages
    ):
        metadata_language = None

    view_kwargs = {
        "template_mode": "inline_edit",
        "show_object_type_and_id_on_object_page_text": get_user_settings(flask_login.current_user.id)["SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE"],
        "show_object_title": get_user_settings(flask_login.current_user.id)["SHOW_OBJECT_TITLE"],
        "measurement_type_name": logic.action_type_translations.get_action_type_translation_for_action_type_in_language(
            action_type_id=logic.actions.models.ActionType.MEASUREMENT,
            language_id=logic.languages.get_user_language(flask_login.current_user).id,
            use_fallback=True
        ).name,
        "metadata_language": metadata_language,
        "languages": languages,
        "all_languages": all_languages,
        "SUPPORTED_LOCALES": logic.locale.SUPPORTED_LOCALES,
        "ENGLISH": english,
        "object_type": object_type,
        "action": action,
        "action_type": get_action_type_with_translation_in_language(action.type_id, user_language_id),
        "instrument": instrument,
        "schema": obj.schema,
        "data": obj.data,
        "name": obj.name,
        "object_log_entries": object_log_entries,
        "ObjectLogEntryType": ObjectLogEntryType,
        "last_edit_datetime": obj.utc_datetime,
        "last_edit_user": get_user(obj.user_id),
        "object_id": object_id,
        "user_may_edit": True,
        "user_may_comment": True,
        "comments": comments.get_comments_for_object(object_id),
        "comment_form": CommentForm(),
        "files": logic.files.get_files_for_object(object_id),
        "file_source_instrument_exists": False,
        "file_source_jupyterhub_exists": False,
        "file_form": FileForm(),
        "edit_external_link_file": flask.request.args.get('edit_invalid_link_file', None),
        "edit_external_link_error": flask.request.args.get('edit_invalid_link_error', None),
        "external_link_form": ExternalLinkForm(),
        "external_link_error": flask.request.args.get('invalid_link_error', None),
        "external_link_errors": {
            '0': _('Please enter a valid URL.'),
            '1': _('The URL you have entered exceeds the length limit.'),
            '2': _('The IP address you entered is invalid.'),
            '3': _('The port number you entered is invalid.')
        },
        "mobile_upload_url": mobile_upload_url,
        "mobile_upload_qrcode": mobile_upload_qrcode,
        "notebook_templates": notebook_templates,
        "object_qrcode": object_qrcode,
        "object_url": object_url,
        "restore_form": None,
        "version_id": obj.version_id,
        "user_may_grant": user_may_grant,
        "favorite_measurement_actions": favorite_measurement_actions,
        "FileLogEntryType": FileLogEntryType,
        "file_information_form": FileInformationForm(),
        "file_hiding_form": FileHidingForm(),
        "new_schema_available": new_schema_available,
        "related_objects_tree": related_objects_tree,
        "object_publications": object_publications,
        "user_may_link_publication": user_may_link_publication,
        "user_may_use_as_template": user_may_use_as_template,
        "show_dataverse_export": show_dataverse_export,
        "dataverse_url": dataverse_url,
        "publication_form": publication_form,
        "get_object": get_object,
        "get_object_if_current_user_has_read_permissions": get_object_if_current_user_has_read_permissions,
        "get_object_location_assignment": get_object_location_assignment,
        "get_user": get_user,
        "get_location": get_location,
        "PAGE_SIZES": PAGE_SIZES,
        "HORIZONTAL_LABEL_MARGIN": HORIZONTAL_LABEL_MARGIN,
        "VERTICAL_LABEL_MARGIN": VERTICAL_LABEL_MARGIN,
        "mm": mm,
        "object_location_assignments": get_object_location_assignments(object_id),
        "build_object_location_assignment_confirmation_url": build_object_location_assignment_confirmation_url,
        "user_may_assign_location": True,
        "location_form": location_form,
        "project": linked_project,
        "get_project": get_project_if_it_exists,
        "get_action_type": get_action_type,
        "get_action_type_with_translation_in_language": get_action_type_with_translation_in_language,
        "get_instrument_with_translation_in_language": get_instrument_with_translation_in_language,
        "component": obj.component,
        "fed_object_id": obj.fed_object_id,
        "fed_version_id": obj.fed_version_id,
        "get_component": get_component,
        "location_is_fed": {str(loc.id): loc.fed_id is not None for loc in locations_map.values()},
        "user_is_fed": user_is_fed
    }

    # form kwargs
    if action is not None and action.instrument is not None and flask_login.current_user in action.instrument.responsible_users:
        instrument_log_categories = logic.instrument_log_entries.get_instrument_log_categories(action.instrument.id)
        if 'create_instrument_log_entry' in flask.request.form:
            category_ids = []
            for category_id in flask.request.form.getlist('instrument_log_categories'):
                try:
                    if int(category_id) in [category.id for category in instrument_log_categories]:
                        category_ids.append(int(category_id))
                except Exception:
                    pass

    errors = {}
    form_data = {}
    form = ObjectForm()
    if flask.request.method != 'GET' and form.validate_on_submit():
        raw_form_data = {key: flask.request.form.getlist(key) for key in flask.request.form}
        form_data = {k: v[0] for k, v in raw_form_data.items()}

    if not flask.current_app.config["LOAD_OBJECTS_IN_BACKGROUND"]:
        referencable_objects = get_objects_with_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.READ
        )
        if object is not None:
            referencable_objects = [
                referencable_object
                for referencable_object in referencable_objects
                if referencable_object.object_id != object_id
            ]

    else:
        referencable_objects = []

    sorted_actions = get_sorted_actions_for_user(
        user_id=flask_login.current_user.id
    )
    for action in sorted_actions:
        db.session.expunge(action)

    action_type_id_by_action_id = {}
    for action_type in get_action_types():
        for action in get_actions(action_type.id):
            action_type_id_by_action_id[action.id] = action_type.id

    tags = [{'name': tag.name, 'uses': tag.uses} for tag in logic.tags.get_tags()]
    users = get_users(exclude_hidden=True)
    users.sort(key=lambda user: user.id)

    english = get_language(Language.ENGLISH)

    form_kwargs = {
        "errors": errors,
        "form_data": form_data,
        "form": form,
        "referencable_objects": referencable_objects,
        "sorted_actions": sorted_actions,
        "action_type_id_by_action_id": action_type_id_by_action_id,
        "ActionType": models.ActionType,
        "datetime": datetime,
        "tags": tags,
        "users": users,
        "mode": 'edit',
        "languages": get_languages(),
        "ENGLISH": english
    }

    kwargs = {**view_kwargs, **form_kwargs}

    return flask.render_template('objects/inline_edit/inline_edit_base.html', **kwargs)


@frontend.route('/objects/<int:object_id>', methods=['GET', 'POST'])
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object(object_id):
    object = get_object(object_id=object_id)

    user_language_id = get_user_language(flask_login.current_user).id
    english = get_language(Language.ENGLISH)

    object_languages = set()
    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    user_may_edit = Permissions.WRITE in user_permissions and object.fed_object_id is None
    user_may_grant = Permissions.GRANT in user_permissions
    if object.action_id is not None:
        user_may_use_as_template = Permissions.READ in get_user_action_permissions(object.action_id, user_id=flask_login.current_user.id)
        action = get_action_with_translation_in_language(object.action_id, user_language_id, use_fallback=True)
        if action.schema != object.schema:
            new_schema_available = True
        else:
            new_schema_available = False
    else:
        action = None
        new_schema_available = False
        user_may_use_as_template = False
    if action and action.type and action.type.enable_related_objects:
        related_objects_tree = logic.object_relationships.build_related_objects_tree(object_id, user_id=flask_login.current_user.id)
    else:
        related_objects_tree = None
    if not user_may_edit and flask.request.args.get('mode', '') == 'edit':
        if object.fed_object_id is not None:
            flask.flash(_('Editing imported objects is not yet supported.'), 'error')
        return flask.abort(403)
    if not user_may_edit and flask.request.args.get('mode', '') == 'upgrade':
        if object.fed_object_id is not None:
            flask.flash(_('Editing imported objects is not yet supported.'), 'error')
        return flask.abort(403)
    if not flask.current_app.config['DISABLE_INLINE_EDIT']:
        if not user_may_edit and flask.request.args.get('mode', '') == 'inline_edit':
            return flask.abort(403)
        if user_may_edit and flask.request.method == 'GET' and flask.request.args.get('mode', '') in {'', 'inline_edit'}:
            return show_inline_edit(object, get_action(object.action_id), related_objects_tree)
    if flask.request.method == 'GET' and flask.request.args.get('mode', '') not in ('edit', 'upgrade'):
        if action is not None:
            instrument = get_instrument_with_translation_in_language(action.instrument_id, user_language_id) if action.instrument else None
            object_type = get_action_type_with_translation_in_language(
                action_type_id=action.type_id,
                language_id=user_language_id
            ).translation.object_name
        else:
            instrument = None
            object_type = None
        object_log_entries = object_log.get_object_log_entries(object_id=object_id, user_id=flask_login.current_user.id)

        dataverse_enabled = bool(flask.current_app.config['DATAVERSE_URL'])
        if dataverse_enabled:
            dataverse_url = logic.dataverse_export.get_dataverse_url(object_id)
            show_dataverse_export = user_may_grant and not dataverse_url
        else:
            dataverse_url = None
            show_dataverse_export = False

        if user_may_edit:
            serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
            token = serializer.dumps([flask_login.current_user.id, object_id])
            mobile_upload_url = flask.url_for('.mobile_file_upload', object_id=object_id, token=token, _external=True)
            mobile_upload_qrcode = generate_qrcode(mobile_upload_url, should_cache=False)
        else:
            mobile_upload_url = None
            mobile_upload_qrcode = None

        object_url = flask.url_for('.object', object_id=object_id, _external=True)
        object_qrcode = generate_qrcode(object_url, should_cache=True)

        readable_location_ids = [
            location.id
            for location in get_locations_with_user_permissions(flask_login.current_user.id, Permissions.READ)
        ]

        location_form = ObjectLocationAssignmentForm()
        locations_map, locations_tree = get_locations_tree()
        locations = [('-1', '—')]
        unvisited_location_ids_prefixes_and_subtrees = [(location_id, '', locations_tree[location_id]) for location_id in locations_tree]
        while unvisited_location_ids_prefixes_and_subtrees:
            location_id, prefix, subtree = unvisited_location_ids_prefixes_and_subtrees.pop(0)
            location = locations_map[location_id]
            if Permissions.READ in readable_location_ids:
                locations.append((str(location_id), prefix + get_location_name(location, include_id=True)))
            prefix = '{}{} / '.format(prefix, get_location_name(location))
            for location_id in sorted(subtree, key=lambda location_id: get_location_name(locations_map[location_id]), reverse=True):
                unvisited_location_ids_prefixes_and_subtrees.insert(0, (location_id, prefix, subtree[location_id]))

        location_form.location.choices = locations
        possible_responsible_users = [('-1', '—')]
        user_is_fed = {}
        for user in logic.users.get_users(exclude_hidden=True):
            possible_responsible_users.append((str(user.id), user.get_name()))
            user_is_fed[str(user.id)] = user.fed_id is not None
        location_form.responsible_user.choices = possible_responsible_users

        measurement_actions = logic.action_translations.get_actions_with_translation_in_language(user_language_id, models.ActionType.MEASUREMENT, use_fallback=True)
        favorite_action_ids = logic.favorites.get_user_favorite_action_ids(flask_login.current_user.id)
        favorite_measurement_actions = [
            action
            for action in measurement_actions
            if action.id in favorite_action_ids and not action.is_hidden
        ]
        # Sort by: instrument name (independent actions first), action name
        favorite_measurement_actions.sort(key=lambda action: (
            action.user.name.lower() if action.user else '',
            get_instrument_with_translation_in_language(action.instrument_id, user_language_id).translation.name.lower() if action.instrument else '',
            action.translation.name.lower()
        ))

        publication_form = ObjectPublicationForm()

        object_publications = logic.publications.get_publications_for_object(object_id=object.id)
        user_may_link_publication = Permissions.WRITE in user_permissions

        if object.schema is not None and object.data is not None:
            notebook_templates = get_notebook_templates(
                object_id=object.id,
                data=object.data,
                schema=object.schema,
                user_id=flask_login.current_user.id
            )
        else:
            notebook_templates = []

        linked_project = logic.projects.get_project_linked_to_object(object_id)

        object_languages = logic.languages.get_languages_in_object_data(object.data)
        languages = []
        for lang_code in object_languages:
            languages.append(get_language_by_lang_code(lang_code))

        all_languages = get_languages()
        metadata_language = flask.request.args.get('language', None)
        if not any(
            language.lang_code == metadata_language
            for language in languages
        ):
            metadata_language = None

        if object.user_id is not None:
            last_edit_user = get_user(object.user_id)
        else:
            last_edit_user = None

        return flask.render_template(
            'objects/view/base.html',
            template_mode="view",
            show_object_type_and_id_on_object_page_text=get_user_settings(flask_login.current_user.id)["SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE"],
            show_object_title=get_user_settings(flask_login.current_user.id)["SHOW_OBJECT_TITLE"],
            measurement_type_name=logic.action_type_translations.get_action_type_translation_for_action_type_in_language(
                action_type_id=logic.actions.models.ActionType.MEASUREMENT,
                language_id=logic.languages.get_user_language(flask_login.current_user).id,
                use_fallback=True
            ).name,
            metadata_language=metadata_language,
            languages=languages,
            all_languages=all_languages,
            SUPPORTED_LOCALES=logic.locale.SUPPORTED_LOCALES,
            ENGLISH=english,
            object_type=object_type,
            action=action,
            action_type=get_action_type_with_translation_in_language(action.type_id, user_language_id) if action is not None else None,
            instrument=instrument,
            schema=object.schema,
            data=object.data,
            name=object.name,
            object_log_entries=object_log_entries,
            ObjectLogEntryType=ObjectLogEntryType,
            last_edit_datetime=object.utc_datetime,
            last_edit_user=last_edit_user,
            object_id=object_id,
            user_may_edit=user_may_edit,
            user_may_comment=user_may_edit,
            comments=comments.get_comments_for_object(object_id),
            comment_form=CommentForm(),
            files=logic.files.get_files_for_object(object_id),
            file_source_instrument_exists=False,
            file_source_jupyterhub_exists=False,
            file_form=FileForm(),
            edit_external_link_file=flask.request.args.get('edit_invalid_link_file', None),
            edit_external_link_error=flask.request.args.get('edit_invalid_link_error', None),
            external_link_form=ExternalLinkForm(),
            external_link_error=flask.request.args.get('invalid_link_error', None),
            external_link_errors={
                '0': _('Please enter a valid URL.'),
                '1': _('The URL you have entered exceeds the length limit.'),
                '2': _('The IP address you entered is invalid.'),
                '3': _('The port number you entered is invalid.')
            },
            mobile_upload_url=mobile_upload_url,
            mobile_upload_qrcode=mobile_upload_qrcode,
            notebook_templates=notebook_templates,
            object_qrcode=object_qrcode,
            object_url=object_url,
            restore_form=None,
            version_id=object.version_id,
            user_may_grant=user_may_grant,
            favorite_measurement_actions=favorite_measurement_actions,
            FileLogEntryType=FileLogEntryType,
            file_information_form=FileInformationForm(),
            file_hiding_form=FileHidingForm(),
            new_schema_available=new_schema_available,
            related_objects_tree=related_objects_tree,
            object_publications=object_publications,
            user_may_link_publication=user_may_link_publication,
            user_may_use_as_template=user_may_use_as_template,
            show_dataverse_export=show_dataverse_export,
            dataverse_url=dataverse_url,
            publication_form=publication_form,
            get_object=get_object,
            get_object_if_current_user_has_read_permissions=get_object_if_current_user_has_read_permissions,
            get_fed_object_if_current_user_has_read_permissions=get_fed_object_if_current_user_has_read_permissions,
            get_object_location_assignment=get_object_location_assignment,
            get_user=get_user_if_exists,
            get_location=get_location,
            PAGE_SIZES=PAGE_SIZES,
            HORIZONTAL_LABEL_MARGIN=HORIZONTAL_LABEL_MARGIN,
            VERTICAL_LABEL_MARGIN=VERTICAL_LABEL_MARGIN,
            mm=mm,
            object_location_assignments=get_object_location_assignments(object_id),
            build_object_location_assignment_confirmation_url=build_object_location_assignment_confirmation_url,
            user_may_assign_location=user_may_edit,
            location_form=location_form,
            project=linked_project,
            get_project=get_project_if_it_exists,
            get_action_type=get_action_type,
            get_action_type_with_translation_in_language=get_action_type_with_translation_in_language,
            get_instrument_with_translation_in_language=get_instrument_with_translation_in_language,
            component=object.component,
            fed_object_id=object.fed_object_id,
            fed_version_id=object.fed_version_id,
            get_component=get_component,
            location_is_fed={str(loc.id): loc.fed_id is not None for loc in locations_map.values()},
            user_is_fed=user_is_fed
        )
    check_current_user_is_not_readonly()
    if flask.request.args.get('mode', '') == 'upgrade':
        should_upgrade_schema = True
    else:
        should_upgrade_schema = False
    return show_object_form(object, action=get_action(object.action_id), should_upgrade_schema=should_upgrade_schema)


@frontend.route('/objects/<int:object_id>/dc.rdf')
@frontend.route('/objects/<int:object_id>/versions/<int:version_id>/dc.rdf')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_rdf(object_id, version_id=None):
    rdf_xml = logic.rdf.generate_rdf(flask_login.current_user.id, object_id, version_id)
    return flask.Response(
        rdf_xml,
        mimetype='application/rdf+xml',
    )


@frontend.route('/objects/<int:object_id>/label')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def print_object_label(object_id):
    mode = flask.request.args.get('mode', 'mixed')
    if mode == 'fixed-width':
        create_mixed_labels = False
        create_long_labels = False
        include_qrcode_in_long_labels = None
        paper_format = flask.request.args.get('width-paper-format', '')
        if paper_format not in PAGE_SIZES:
            paper_format = DEFAULT_PAPER_FORMAT
        maximum_width = math.floor(PAGE_SIZES[paper_format][0] / mm - 2 * HORIZONTAL_LABEL_MARGIN)
        maximum_height = math.floor(PAGE_SIZES[paper_format][1] / mm - 2 * VERTICAL_LABEL_MARGIN)
        ghs_classes_side_by_side = 'side-by-side' in flask.request.args
        label_minimum_width = 20
        if ghs_classes_side_by_side:
            label_minimum_width = 40
        try:
            label_width = float(flask.request.args.get('label-width', '20'))
        except ValueError:
            label_width = 0
        if math.isnan(label_width):
            label_width = 0
        if label_width < label_minimum_width:
            label_width = label_minimum_width
        if label_width > maximum_width:
            label_width = maximum_width
        try:
            label_minimum_height = float(flask.request.args.get('label-minimum-height', '0'))
        except ValueError:
            label_minimum_height = 0
        if math.isnan(label_minimum_height):
            label_minimum_height = 0
        if label_minimum_height < 0:
            label_minimum_height = 0
        if label_minimum_height > maximum_height:
            label_minimum_height = maximum_height
        qrcode_width = 18
        centered = 'centered' in flask.request.args
    elif mode == 'minimum-height':
        create_mixed_labels = False
        create_long_labels = True
        paper_format = flask.request.args.get('height-paper-format', '')
        if paper_format not in PAGE_SIZES:
            paper_format = DEFAULT_PAPER_FORMAT
        maximum_width = math.floor(PAGE_SIZES[paper_format][0] / mm - 2 * HORIZONTAL_LABEL_MARGIN)
        include_qrcode_in_long_labels = 'include-qrcode' in flask.request.args
        label_width = 0
        label_minimum_height = 0
        try:
            label_minimum_width = float(flask.request.args.get('label-minimum-width', '0'))
        except ValueError:
            label_minimum_width = 0
        if math.isnan(label_minimum_width):
            label_minimum_width = 0
        if label_minimum_width < 0:
            label_minimum_width = 0
        if label_minimum_width > maximum_width:
            label_minimum_width = maximum_width
        qrcode_width = 0
        ghs_classes_side_by_side = None
        centered = None
    else:
        create_mixed_labels = True
        create_long_labels = None
        include_qrcode_in_long_labels = None
        paper_format = flask.request.args.get('mixed-paper-format', '')
        if paper_format not in PAGE_SIZES:
            paper_format = DEFAULT_PAPER_FORMAT
        label_width = 0
        label_minimum_height = 0
        qrcode_width = 0
        label_minimum_width = 0
        ghs_classes_side_by_side = None
        centered = None

    object = get_object(object_id=object_id)
    object_log_entries = object_log.get_object_log_entries(object_id=object_id, user_id=flask_login.current_user.id)
    for object_log_entry in object_log_entries:
        if object_log_entry.type in (ObjectLogEntryType.CREATE_OBJECT, ObjectLogEntryType.CREATE_BATCH):
            creation_date = object_log_entry.utc_datetime.strftime('%Y-%m-%d')
            creation_user = get_user(object_log_entry.user_id).name
            break
    else:
        creation_date = _('Unknown')
        creation_user = _('Unknown')
    if 'created' in object.data and '_type' in object.data['created'] and object.data['created']['_type'] == 'datetime':
        creation_date = object.data['created']['utc_datetime'].split(' ')[0]
    object_name = get_translated_text(object.name)

    object_url = flask.url_for('.object', object_id=object_id, _external=True)

    if 'hazards' in object.data and '_type' in object.data['hazards'] and object.data['hazards']['_type'] == 'hazards':
        hazards = object.data['hazards']['hazards']
    else:
        hazards = []

    pdf_data = create_labels(
        object_id=object_id,
        object_name=object_name,
        object_url=object_url,
        creation_user=creation_user,
        creation_date=creation_date,
        ghs_classes=hazards,
        paper_format=paper_format,
        create_mixed_labels=create_mixed_labels,
        create_long_labels=create_long_labels,
        include_qrcode_in_long_labels=include_qrcode_in_long_labels,
        label_width=label_width,
        label_minimum_height=label_minimum_height,
        label_minimum_width=label_minimum_width,
        qrcode_width=qrcode_width,
        ghs_classes_side_by_side=ghs_classes_side_by_side,
        centered=centered
    )
    return flask.send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        max_age=-1
    )


@frontend.route('/objects/<int:object_id>/comments/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_comments(object_id):
    check_current_user_is_not_readonly()
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        content = comment_form.content.data
        comments.create_comment(object_id=object_id, user_id=flask_login.current_user.id, content=content)
        flask.flash(_('Successfully posted a comment.'), 'success')
    else:
        flask.flash(_('Please enter a comment text.'), 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/objects/<int:object_id>/locations/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_location(object_id):
    check_current_user_is_not_readonly()
    location_form = ObjectLocationAssignmentForm()
    location_form.location.choices = [('-1', '—')] + [
        (str(location.id), get_location_name(location, include_id=True))
        for location in get_locations_with_user_permissions(flask_login.current_user.id, Permissions.READ)
    ]
    possible_responsible_users = [('-1', '—')]
    for user in logic.users.get_users(exclude_hidden=True):
        possible_responsible_users.append((str(user.id), '{} (#{})'.format(user.name, user.id)))
    location_form.responsible_user.choices = possible_responsible_users
    if location_form.validate_on_submit():
        location_id = int(location_form.location.data)
        if location_id < 0:
            location_id = None
        responsible_user_id = int(location_form.responsible_user.data)
        if responsible_user_id < 0:
            responsible_user_id = None
        description = location_form.description.data
        try:
            description = json.loads(description)
        except Exception:
            description = {}
        valid_description = {'en': ''}
        for language_code, description_text in description.items():
            if not isinstance(language_code, str):
                continue
            try:
                language = get_language_by_lang_code(language_code)
            except logic.errors.LanguageDoesNotExistError:
                continue
            if not language.enabled_for_input:
                continue
            valid_description[language_code] = description_text
        description = valid_description
        if location_id is not None or responsible_user_id is not None:
            assign_location_to_object(object_id, location_id, responsible_user_id, flask_login.current_user.id, description)
            flask.flash(_('Successfully assigned a new location to this object.'), 'success')
        else:
            flask.flash(_('Please select a location or a responsible user.'), 'error')
    else:
        flask.flash(_('Please select a location or a responsible user.'), 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/objects/<int:object_id>/publications/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_publication(object_id):
    check_current_user_is_not_readonly()
    publication_form = ObjectPublicationForm()
    if publication_form.validate_on_submit():
        doi = publication_form.doi.data
        title = publication_form.title.data
        object_name = publication_form.object_name.data
        if title is not None:
            title = title.strip()
        if not title:
            title = None
        if object_name is not None:
            object_name = object_name.strip()
        if not object_name:
            object_name = None
        existing_publication = ([
            publication
            for publication in logic.publications.get_publications_for_object(object_id)
            if publication.doi == doi
        ] or [None])[0]
        if existing_publication is not None and existing_publication.title == title and existing_publication.object_name == object_name:
            flask.flash(_('This object has already been linked to this publication.'), 'info')
        else:
            logic.publications.link_publication_to_object(user_id=flask_login.current_user.id, object_id=object_id, doi=doi, title=title, object_name=object_name)
            if existing_publication is None:
                flask.flash(_('Successfully linked this object to a publication.'), 'success')
            else:
                flask.flash(_('Successfully updated the information for this publication.'), 'success')
    else:
        flask.flash(_('Please enter a valid DOI for the publication you want to link this object to.'), 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/objects/<int:object_id>/export')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def export_data(object_id):
    object_ids = [object_id]
    file_extension = flask.request.args.get('format', '.pdf')
    if file_extension != '.pdf' and file_extension not in logic.export.FILE_FORMATS:
        return flask.abort(400)
    if 'object_ids' in flask.request.args:
        try:
            object_ids = json.loads(flask.request.args['object_ids'])
            object_ids = [int(i) for i in object_ids]
            if any((Permissions.READ not in get_user_object_permissions(i, flask_login.current_user.id)) for i in object_ids):
                return flask.abort(400)
        except Exception:
            return flask.abort(400)
        if not object_ids:
            return flask.abort(400)
    if file_extension == '.pdf':
        sections = pdfexport.SECTIONS
        if 'sections' in flask.request.args:
            try:
                sections = sections.intersection(json.loads(flask.request.args['sections']))
            except Exception:
                return flask.abort(400)
        if 'language' in flask.request.args:
            try:
                lang_code = flask.request.args['language']
                if lang_code not in logic.locale.SUPPORTED_LOCALES:
                    raise ValueError()
                language = logic.languages.get_language_by_lang_code(lang_code)
                if not language.enabled_for_user_interface:
                    raise ValueError()
            except Exception:
                lang_code = 'en'
        else:
            lang_code = 'en'
        pdf_data = pdfexport.create_pdfexport(object_ids, sections, lang_code)
        file_bytes = io.BytesIO(pdf_data)
    elif file_extension in logic.export.FILE_FORMATS:
        file_bytes = logic.export.FILE_FORMATS[file_extension][1](flask_login.current_user.id, object_ids=object_ids)
    else:
        file_bytes = None
    if file_bytes:
        return flask.Response(
            file_bytes,
            200,
            headers={
                'Content-Disposition': f'attachment; filename=sampledb_export{file_extension}',
                'Content-Type': 'application/pdf' if file_extension == '.pdf' else logic.export.FILE_FORMATS[file_extension][2]
            }
        )
    return flask.abort(500)


@frontend.route('/objects/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_object():
    check_current_user_is_not_readonly()
    action_id = flask.request.args.get('action_id', None)
    previous_object_id = flask.request.args.get('previous_object_id', None)
    if not action_id and not previous_object_id:
        # TODO: handle error
        return flask.abort(404)

    sample_id = flask.request.args.get('sample_id', None)

    previous_object = None
    action = None
    if previous_object_id:
        try:
            previous_object = get_object(previous_object_id)
        except ObjectDoesNotExistError:
            flask.flash(_("This object does not exist."), 'error')
            return flask.abort(404)
        if Permissions.READ not in get_user_object_permissions(user_id=flask_login.current_user.id, object_id=previous_object_id):
            flask.flash(_("You do not have the required permissions to use this object as a template."), 'error')
            return flask.abort(403)
        if action_id:
            if action_id != str(previous_object.action_id):
                flask.flash(_("This object was created with a different action."), 'error')
                return flask.abort(400)
            else:
                action_id = previous_object.action_id
    if action_id:
        try:
            action = get_action(action_id)
        except ActionDoesNotExistError:
            flask.flash(_("This action does not exist."), 'error')
            return flask.abort(404)
        if Permissions.READ not in get_user_action_permissions(action_id, user_id=flask_login.current_user.id):
            flask.flash(_("You do not have the required permissions to use this action."), 'error')
            return flask.abort(403)

    placeholder_data = {}

    if sample_id is not None:
        try:
            sample_id = int(sample_id)
        except ValueError:
            sample_id = None
        else:
            if sample_id <= 0:
                sample_id = None
    if sample_id is not None:
        try:
            logic.objects.get_object(sample_id)
        except logic.errors.ObjectDoesNotExistError:
            sample_id = None
    if sample_id is not None:
        if action.schema.get('properties', {}).get('sample', {}).get('type', '') == 'sample':
            placeholder_data = {
                ('sample', ): {'_type': 'sample', 'object_id': sample_id}
            }

    # TODO: check instrument permissions
    return show_object_form(None, action, previous_object, placeholder_data=placeholder_data)
