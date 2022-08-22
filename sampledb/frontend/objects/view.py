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
from ...logic import object_log, comments, errors
from ...logic.actions import get_action, get_action_type
from ...logic.action_permissions import get_user_action_permissions, get_sorted_actions_for_user
from ...logic.object_permissions import Permissions, get_user_object_permissions, get_objects_with_permissions
from ...logic.users import get_user, get_users
from ...logic.settings import get_user_settings
from ...logic.objects import get_object
from ...logic.object_log import ObjectLogEntryType
from ...logic.projects import get_project
from ...logic.locations import get_location, get_object_location_assignment, get_object_location_assignments, assign_location_to_object, get_locations_tree
from ...logic.location_permissions import get_locations_with_user_permissions
from ...logic.languages import get_language_by_lang_code, get_language, get_languages, Language, get_user_language
from ...logic.files import FileLogEntryType
from ...logic.components import get_component
from ...logic.notebook_templates import get_notebook_templates
from ...logic.utils import get_translated_text
from .forms import ObjectForm, CommentForm, FileForm, FileInformationForm, FileHidingForm, ObjectLocationAssignmentForm, ExternalLinkForm, ObjectPublicationForm
from ...utils import object_permissions_required
from ..utils import generate_qrcode, get_user_if_exists
from ..labels import create_labels, PAGE_SIZES, DEFAULT_PAPER_FORMAT, HORIZONTAL_LABEL_MARGIN, VERTICAL_LABEL_MARGIN, mm
from .. import pdfexport
from ..utils import check_current_user_is_not_readonly, get_location_name
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


def build_object_location_assignment_declination_url(object_location_assignment_id: int) -> str:
    declination_url = flask.url_for(
        'frontend.decline_responsibility_for_object',
        t=logic.security_tokens.generate_token(
            object_location_assignment_id,
            salt='decline_responsibility',
            secret_key=flask.current_app.config['SECRET_KEY']
        ),
        _external=True
    )
    return declination_url


def get_project_if_it_exists(project_id):
    try:
        return get_project(project_id)
    except errors.ProjectDoesNotExistError:
        return None


@frontend.route('/objects/<int:object_id>', methods=['GET', 'POST'])
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object(object_id):
    object = get_object(object_id=object_id)
    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    user_may_edit = Permissions.WRITE in user_permissions and object.fed_object_id is None and object.action_id is not None
    user_may_grant = Permissions.GRANT in user_permissions

    mode = flask.request.args.get('mode', '')
    if not user_may_edit and mode in {'edit', 'upgrade'}:
        if object.fed_object_id is not None:
            flask.flash(_('Editing imported objects is not yet supported.'), 'error')
        return flask.abort(403)
    if not flask.current_app.config['DISABLE_INLINE_EDIT']:
        if not user_may_edit and mode == 'inline_edit':
            return flask.abort(403)
    if mode in {'edit', 'upgrade'} or flask.request.method == 'POST':
        check_current_user_is_not_readonly()
        action = get_action(object.action_id)
        should_upgrade_schema = (mode == 'upgrade')
        if should_upgrade_schema and (not action.schema or action.schema == object.schema):
            flask.flash(_('The schema for this object cannot be updated.'), 'error')
            return flask.redirect(flask.url_for('.object', object_id=object_id))
        return show_object_form(
            object=object,
            action=action,
            should_upgrade_schema=should_upgrade_schema
        )

    template_kwargs = {}

    # languages
    user_language_id = get_user_language(flask_login.current_user).id
    english = get_language(Language.ENGLISH)
    all_languages = get_languages()
    languages_by_lang_code = {
        language.lang_code: language
        for language in all_languages
    }
    object_languages = [
        languages_by_lang_code.get(lang_code)
        for lang_code in logic.languages.get_languages_in_object_data(object.data)
    ]
    metadata_language = flask.request.args.get('language', None)
    if metadata_language not in languages_by_lang_code:
        metadata_language = None
    template_kwargs.update({
        "metadata_language": metadata_language,
        "languages": object_languages,
        "all_languages": all_languages,
        "SUPPORTED_LOCALES": logic.locale.SUPPORTED_LOCALES,
        "ENGLISH": english,
    })

    # basic object and action information
    if object.action_id is not None:
        action = get_action(object.action_id)
        action_type = get_action_type(action.type_id) if action.type_id is not None else None
        instrument = action.instrument
        object_type = get_translated_text(action_type.object_name, user_language_id) if action_type else None
        if action.schema is not None and action.schema != object.schema:
            new_schema_available = True
        else:
            new_schema_available = False
        user_may_use_as_template = Permissions.READ in get_user_action_permissions(object.action_id, user_id=flask_login.current_user.id)
    else:
        action = None
        action_type = None
        instrument = None
        object_type = None
        new_schema_available = False
        user_may_use_as_template = False
    template_kwargs.update({
        "object_id": object_id,
        "version_id": object.version_id,
        "object_type": object_type,
        "action": action,
        "action_type": action_type,
        "instrument": instrument,
        "schema": object.schema,
        "data": object.data,
        "name": object.name,
        "component": object.component,
        "fed_object_id": object.fed_object_id,
        "fed_version_id": object.fed_version_id,
        "new_schema_available": new_schema_available,
        "user_may_edit": user_may_edit,
        "user_may_grant": user_may_grant,
        "user_may_use_as_template": user_may_use_as_template,
        "restore_form": None,
    })

    # user settings
    user_settings = get_user_settings(flask_login.current_user.id)
    template_kwargs.update({
        "show_object_type_and_id_on_object_page_text": user_settings["SHOW_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE"],
        "show_object_title": user_settings["SHOW_OBJECT_TITLE"],
    })

    # QR code
    object_url = flask.url_for('.object', object_id=object_id, _external=True)
    object_qrcode = generate_qrcode(object_url, should_cache=True)
    template_kwargs.update({
        "object_qrcode": object_qrcode,
        "object_url": object_url,
    })

    # labels
    template_kwargs.update({
        "PAGE_SIZES": PAGE_SIZES,
        "HORIZONTAL_LABEL_MARGIN": HORIZONTAL_LABEL_MARGIN,
        "VERTICAL_LABEL_MARGIN": VERTICAL_LABEL_MARGIN,
        "mm": mm,
    })

    # dataverse export
    dataverse_enabled = bool(flask.current_app.config['DATAVERSE_URL'])
    if dataverse_enabled:
        dataverse_url = logic.dataverse_export.get_dataverse_url(object.id)
        show_dataverse_export = user_may_grant and not dataverse_url
    else:
        dataverse_url = None
        show_dataverse_export = False
    template_kwargs.update({
        "show_dataverse_export": show_dataverse_export,
        "dataverse_url": dataverse_url,
    })

    # scicat export
    scicat_enabled = bool(flask.current_app.config['SCICAT_API_URL']) and bool(flask.current_app.config['SCICAT_FRONTEND_URL'])
    if scicat_enabled:
        scicat_url = logic.scicat_export.get_scicat_url(object.id)
        show_scicat_export = user_may_grant and not scicat_url and action_type is not None and action_type.scicat_export_type is not None
    else:
        scicat_url = None
        show_scicat_export = False
    template_kwargs.update({
        "show_scicat_export": show_scicat_export,
        "scicat_url": scicat_url,
    })

    # download service
    download_service_enabled = bool(flask.current_app.config['DOWNLOAD_SERVICE_URL'])
    download_service_enabled = download_service_enabled and (flask.current_app.config['DOWNLOAD_SERVICE_SECRET'])
    template_kwargs.update({
        "show_download_service": download_service_enabled,
    })

    if flask_login.current_user.is_authenticated:
        # use in measurement menu
        measurement_actions = logic.actions.get_actions(
            action_type_id=models.ActionType.MEASUREMENT
        )
        favorite_action_ids = logic.favorites.get_user_favorite_action_ids(flask_login.current_user.id)
        favorite_measurement_actions = [
            action
            for action in measurement_actions
            if action.id in favorite_action_ids and not action.is_hidden
        ]
        # sort by: instrument name (independent actions first), action name
        favorite_measurement_actions.sort(
            key=lambda action: (
                action.user.name.lower() if action.user else '',
                get_translated_text(action.instrument.name, user_language_id).lower() if action.instrument else '',
                get_translated_text(action.name, user_language_id).lower()
            )
        )
    else:
        favorite_measurement_actions = []
    template_kwargs.update({
        "favorite_measurement_actions": favorite_measurement_actions,
        "measurement_type_name": get_translated_text(logic.actions.get_action_type(logic.actions.models.ActionType.MEASUREMENT).name),
    })

    # notebook templates
    if object.schema is not None and object.data is not None:
        notebook_templates = get_notebook_templates(
            object_id=object.id,
            data=object.data,
            schema=object.schema,
            user_id=flask_login.current_user.id
        )
    else:
        notebook_templates = []
    template_kwargs.update({
        "notebook_templates": notebook_templates,
    })

    # linked project group
    linked_project = logic.projects.get_project_linked_to_object(object_id)
    template_kwargs.update({
        "project": linked_project,
    })

    # files
    template_kwargs.update({
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
        "FileLogEntryType": FileLogEntryType,
        "file_information_form": FileInformationForm(),
        "file_hiding_form": FileHidingForm(),
    })

    # mobile file upload
    if user_may_edit:
        serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
        token = serializer.dumps([flask_login.current_user.id, object_id])
        mobile_upload_url = flask.url_for('.mobile_file_upload', object_id=object_id, token=token, _external=True)
        mobile_upload_qrcode = generate_qrcode(mobile_upload_url, should_cache=False)
    else:
        mobile_upload_url = None
        mobile_upload_qrcode = None
    template_kwargs.update({
        "mobile_upload_url": mobile_upload_url,
        "mobile_upload_qrcode": mobile_upload_qrcode,
    })

    # object location and/or responsible user assignments
    object_location_assignments = get_object_location_assignments(object_id)
    user_may_assign_location = user_may_edit
    if user_may_assign_location:
        readable_location_ids = [
            location.id
            for location in get_locations_with_user_permissions(flask_login.current_user.id, Permissions.READ)
        ]
        location_form = ObjectLocationAssignmentForm()
        locations_map, locations_tree = get_locations_tree()
        locations = [('-1', '—')]
        valid_locations = []
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
                if location.type is None or location.type.enable_object_assignments:
                    valid_locations.append(locations[-1])
            prefix = f'{prefix}{get_location_name(location)} / '
            for location_id in sorted(subtree, key=lambda location_id: get_location_name(locations_map[location_id]), reverse=True):
                unvisited_location_ids_prefixes_and_subtrees.insert(0, (location_id, prefix, subtree[location_id]))
        location_form.location.all_choices = locations
        location_form.location.choices = valid_locations
        possible_responsible_users = [('-1', '—')]
        user_is_fed = {}
        for user in get_users(exclude_hidden=True):
            possible_responsible_users.append((str(user.id), user.get_name()))
            user_is_fed[str(user.id)] = user.fed_id is not None
        location_form.responsible_user.choices = possible_responsible_users
        location_is_fed = {
            str(location.id): location.fed_id is not None
            for location in locations_map.values()
        }
    else:
        location_form = None
        user_is_fed = None
        location_is_fed = None
    template_kwargs.update({
        "user_may_assign_location": user_may_assign_location,
        "object_location_assignments": object_location_assignments,
        "build_object_location_assignment_confirmation_url": build_object_location_assignment_confirmation_url,
        "build_object_location_assignment_declination_url": build_object_location_assignment_declination_url,
        "location_form": location_form,
        "location_is_fed": location_is_fed,
        "user_is_fed": user_is_fed,
    })

    # publications
    object_publications = logic.publications.get_publications_for_object(object_id=object.id)
    user_may_link_publication = user_may_edit
    if user_may_link_publication:
        publication_form = ObjectPublicationForm()
    else:
        publication_form = None
    template_kwargs.update({
        "user_may_link_publication": user_may_link_publication,
        "publication_form": publication_form,
        "object_publications": object_publications,
    })

    # comments
    template_kwargs.update({
        "user_may_comment": user_may_edit,
        "comments": comments.get_comments_for_object(object_id),
        "comment_form": CommentForm(),
    })

    # activity log
    object_log_entries = object_log.get_object_log_entries(
        object_id=object_id,
        user_id=flask_login.current_user.id
    )
    template_kwargs.update({
        "object_log_entries": object_log_entries,
        "ObjectLogEntryType": ObjectLogEntryType,
    })

    # related objects tree
    if action and action.type and action.type.enable_related_objects:
        related_objects_tree = logic.object_relationships.build_related_objects_tree(object_id, user_id=flask_login.current_user.id)
    else:
        related_objects_tree = None
    template_kwargs.update({
        "related_objects_tree": related_objects_tree,
    })

    # various getters
    template_kwargs.update({
        "get_object": get_object,
        "get_object_if_current_user_has_read_permissions": get_object_if_current_user_has_read_permissions,
        "get_fed_object_if_current_user_has_read_permissions": get_fed_object_if_current_user_has_read_permissions,
        "get_user": get_user_if_exists,
        "get_location": get_location,
        "get_object_location_assignment": get_object_location_assignment,
        "get_project": get_project_if_it_exists,
        "get_action_type": get_action_type,
        "get_component": get_component,
    })

    if mode in {'', 'inline_edit'} and not flask.current_app.config['DISABLE_INLINE_EDIT'] and user_may_edit:
        template_kwargs.update({
            "errors": {},
            "form_data": {},
            "form": ObjectForm(),
            "mode": 'edit',
            "datetime": datetime,
            "languages": all_languages,
        })

        # referencable objects
        if not flask.current_app.config["LOAD_OBJECTS_IN_BACKGROUND"]:
            referencable_objects = get_objects_with_permissions(
                user_id=flask_login.current_user.id,
                permissions=Permissions.READ
            )
            referencable_objects = [
                referencable_object
                for referencable_object in referencable_objects
                if referencable_object.object_id != object_id
            ]
        else:
            referencable_objects = []
        template_kwargs.update({
            "referencable_objects": referencable_objects,
        })

        # actions and action types
        sorted_actions = get_sorted_actions_for_user(
            user_id=flask_login.current_user.id
        )
        action_type_id_by_action_id = {}
        for action in sorted_actions:
            action_type_id_by_action_id[action.id] = action.type_id
            db.session.expunge(action)
        template_kwargs.update({
            "sorted_actions": sorted_actions,
            "action_type_id_by_action_id": action_type_id_by_action_id,
            "ActionType": models.ActionType,
        })

        # previously used tags
        tags = [
            {
                'name': tag.name,
                'uses': tag.uses
            }
            for tag in logic.tags.get_tags()
        ]
        template_kwargs.update({
            "tags": tags,
        })

        # users
        users = get_users(exclude_hidden=True)
        users.sort(key=lambda user: user.id)
        template_kwargs.update({
            "users": users,
        })

        return flask.render_template(
            'objects/inline_edit/inline_edit_base.html',
            template_mode="inline_edit",
            **template_kwargs
        )
    else:
        return flask.render_template(
            'objects/view/base.html',
            template_mode="view",
            **template_kwargs
        )


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
    object = get_object(object_id)
    if object.fed_object_id is not None:
        flask.flash(_('Commenting on imported objects is not yet supported.'), 'error')
        return flask.abort(403)
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
    object = get_object(object_id)
    if object.fed_object_id is not None:
        flask.flash(_('Assigning locations to imported objects is not yet supported.'), 'error')
        return flask.abort(403)
    location_form = ObjectLocationAssignmentForm()
    location_form.location.choices = [('-1', '—')] + [
        (str(location.id), get_location_name(location, include_id=True))
        for location in get_locations_with_user_permissions(flask_login.current_user.id, Permissions.READ)
        if location.type is None or location.type.enable_object_assignments
    ]
    possible_responsible_users = [('-1', '—')]
    for user in get_users(exclude_hidden=True):
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
            except errors.LanguageDoesNotExistError:
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
    object = get_object(object_id)
    if object.fed_object_id is not None:
        flask.flash(_('Assigning publications to imported objects is not yet supported.'), 'error')
        return flask.abort(403)
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
    if action_id is not None:
        try:
            action_id = int(action_id)
        except ValueError:
            action_id = None

    previous_object_id = flask.request.args.get('previous_object_id', None)
    if previous_object_id is not None:
        try:
            previous_object_id = int(previous_object_id)
        except ValueError:
            previous_object_id = None

    if not action_id and not previous_object_id:
        return flask.abort(404)

    sample_id = flask.request.args.get('sample_id', None)

    previous_object = None
    action = None
    if previous_object_id:
        try:
            previous_object = get_object(previous_object_id)
        except errors.ObjectDoesNotExistError:
            flask.flash(_("This object does not exist."), 'error')
            return flask.abort(404)
        if Permissions.READ not in get_user_object_permissions(user_id=flask_login.current_user.id, object_id=previous_object_id):
            flask.flash(_("You do not have the required permissions to use this object as a template."), 'error')
            return flask.abort(403)
        if action_id:
            if action_id != previous_object.action_id:
                flask.flash(_("This object was created with a different action."), 'error')
                return flask.abort(400)
            else:
                action_id = previous_object.action_id
    if action_id:
        try:
            action = get_action(action_id)
        except errors.ActionDoesNotExistError:
            flask.flash(_("This action does not exist."), 'error')
            return flask.abort(404)
        if Permissions.READ not in get_user_action_permissions(action_id, user_id=flask_login.current_user.id):
            flask.flash(_("You do not have the required permissions to use this action."), 'error')
            return flask.abort(403)
        if action.type_id is None or action.schema is None:
            flask.flash(_("Creating objects with this action has been disabled."), 'error')
            return flask.redirect(flask.url_for('.action', action_id=action_id))

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
            get_object(sample_id)
        except errors.ObjectDoesNotExistError:
            sample_id = None
    if sample_id is not None and action is not None and action.schema is not None:
        sample_type = action.schema.get('properties', {}).get('sample', {}).get('type', '')
        if sample_type in ('sample', 'object_reference'):
            placeholder_data = {
                ('sample', ): {'_type': sample_type, 'object_id': sample_id}
            }

    # TODO: check instrument permissions
    return show_object_form(None, action, previous_object, placeholder_data=placeholder_data)
