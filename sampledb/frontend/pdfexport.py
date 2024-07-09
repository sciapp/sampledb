
import base64
import datetime
import io
import os
import typing
import urllib.parse

import flask
import flask_login
import markupsafe
import qrcode
import qrcode.image.pil
from flask_babel import _, refresh
from weasyprint import default_url_fetcher, HTML

from .. import logic
from ..logic import object_log
from ..logic.actions import Action
from ..logic.objects import get_object
from ..models import ObjectLogEntryType, Permissions
from ..logic.users import get_user

from .markdown_images import IMAGE_FORMATS
from .objects.permissions import get_object_if_current_user_has_read_permissions
from .utils import custom_format_datetime, get_user_if_exists, get_location_name
from ..logic.utils import get_translated_text

SECTIONS = frozenset({
    'activity_log',
    'locations',
    'publications',
    'files',
    'comments'
})


def create_pdfexport(
        object_ids: typing.Sequence[int],
        sections: typing.Union[typing.Set[str], typing.FrozenSet[str]] = SECTIONS,
        lang_code: str = 'en'
) -> bytes:
    exported_files: typing.Dict[typing.Tuple[int, int], logic.files.File] = {}

    flask.g.override_locale = lang_code
    refresh()

    base_url = flask.url_for('.index', _external=True)

    def custom_url_fetcher(url: str) -> typing.Dict[str, bytes]:
        # replace URLs of markdown images with Data URLs
        if url.startswith(base_url + 'markdown_images/'):
            file_name = url[len(base_url + 'markdown_images/'):]
            image_data = logic.markdown_images.get_markdown_image(file_name, flask_login.current_user.id)
            if image_data is None:
                url = ''
            else:
                file_extension = os.path.splitext(file_name)[1].lower()
                if file_extension in IMAGE_FORMATS:
                    url = 'data:' + IMAGE_FORMATS[file_extension] + ';base64,' + base64.b64encode(image_data).decode('utf-8')
                else:
                    url = ''
        if url.startswith(base_url + 'object_files/'):
            object_id_file_id = url[len(base_url + 'object_files/'):]
            url = ''
            try:
                object_id_str, file_id_str = object_id_file_id.split('/')
                object_id = int(object_id_str)
                file_id = int(file_id_str)
                file = exported_files[(object_id, file_id)]
                if file.storage == 'database' and not file.is_hidden:
                    for file_extension, mime_type in IMAGE_FORMATS.items():
                        if file.original_file_name.lower().endswith(file_extension):
                            image_data = file.open(read_only=True).read()
                            url = 'data:' + mime_type + ';base64,' + base64.b64encode(image_data).decode('utf-8')
                            break
            except Exception:
                pass
        # only allow Data URLs and URLs via http or https
        if not (url.startswith('data:') or urllib.parse.urlparse(url).scheme in ('http', 'https')):
            url = ''
        return typing.cast(typing.Dict[str, bytes], default_url_fetcher(url))

    objects = []
    for object_id in object_ids:
        object = get_object(object_id)

        activity_log_entries = []
        if 'activity_log' in sections:
            object_log_entries = object_log.get_object_log_entries(object_id=object.id, user_id=flask_login.current_user.id)
            for object_log_entry in reversed(object_log_entries):
                user_id = object_log_entry.user_id
                user_url = markupsafe.escape(flask.url_for('.user_profile', user_id=user_id, _external=True))
                user_name = markupsafe.escape(get_user(object_log_entry.user_id).get_name())

                entry_datetime = markupsafe.escape(custom_format_datetime(object_log_entry.utc_datetime))
                text = f'{entry_datetime} — '
                if object_log_entry.type == ObjectLogEntryType.CREATE_BATCH:
                    text += _('<a href="%(user_url)s">%(user_name)s</a> created this object as part of a batch.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.CREATE_OBJECT:
                    text += _('<a href="%(user_url)s">%(user_name)s</a> created this object.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.EDIT_OBJECT:
                    text += _('<a href="%(user_url)s">%(user_name)s</a> edited this object.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.POST_COMMENT:
                    text += _('<a href="%(user_url)s">%(user_name)s</a> posted a comment.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.RESTORE_OBJECT_VERSION:
                    text += _('<a href="%(user_url)s">%(user_name)s</a> restored a previous version of this object.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.UPLOAD_FILE:
                    text += _('<a href="%(user_url)s">%(user_name)s</a> posted a file.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.USE_OBJECT_IN_MEASUREMENT:
                    try:
                        measurement_id = int(object_log_entry.data['measurement_id'])
                        escaped_object_url = markupsafe.escape(flask.url_for('.object', object_id=measurement_id, _external=True))
                        permissions = logic.object_permissions.get_user_object_permissions(measurement_id, flask_login.current_user.id)
                        if Permissions.READ in permissions:
                            measurement_name = markupsafe.escape(get_translated_text(get_object(measurement_id).name))
                            text += _('<a href="%(user_url)s">%(user_name)s</a> used this object in <a href="%(object_url)s">measurement %(measurement_name)s (#%(measurement_id)s)</a>.', user_url=user_url, user_name=user_name, object_url=escaped_object_url, measurement_id=measurement_id, measurement_name=measurement_name)
                        else:
                            text += _('<a href="%(user_url)s">%(user_name)s</a> used this object in <a href="%(object_url)s">measurement #%(measurement_id)s</a>.', user_url=user_url, user_name=user_name, object_url=escaped_object_url, measurement_id=measurement_id)
                    except Exception:
                        text += _('<a href="%(user_url)s">%(user_name)s</a> used this object in a measurement.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.USE_OBJECT_IN_SAMPLE_CREATION:
                    try:
                        sample_id = int(object_log_entry.data['sample_id'])
                        escaped_object_url = markupsafe.escape(flask.url_for('.object', object_id=sample_id, _external=True))
                        permissions = logic.object_permissions.get_user_object_permissions(sample_id, flask_login.current_user.id)
                        if Permissions.READ in permissions:
                            sample_name = markupsafe.escape(get_translated_text(get_object(sample_id).name))
                            text += _('<a href="%(user_url)s">%(user_name)s</a> used this object to create <a href="%(object_url)s">sample %(sample_name)s (#%(sample_id)s)</a>.', user_url=user_url, user_name=user_name, object_url=escaped_object_url, sample_id=sample_id, sample_name=sample_name)
                        else:
                            text += _('<a href="%(user_url)s">%(user_name)s</a> used this object to create <a href="%(object_url)s">sample #%(sample_id)s</a>.', user_url=user_url, user_name=user_name, object_url=escaped_object_url, sample_id=sample_id)
                    except Exception:
                        text += _('<a href="%(user_url)s">%(user_name)s</a> used this object to create a sample.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.ASSIGN_LOCATION:
                    object_location_assignment_id = object_log_entry.data['object_location_assignment_id']
                    object_location_assignment = logic.locations.get_object_location_assignment(object_location_assignment_id)
                    if object_location_assignment.location_id is not None:
                        location_url = markupsafe.escape(
                            flask.url_for(
                                '.location',
                                location_id=object_location_assignment.location_id,
                                _external=True
                            )
                        )
                        location_name = get_location_name(
                            location_or_location_id=object_location_assignment.location_id,
                            include_id=True,
                            language_code=lang_code
                        )
                    else:
                        location_url = None
                        location_name = None
                    if object_location_assignment.responsible_user_id is not None:
                        other_user_url = markupsafe.escape(
                            flask.url_for(
                                '.user_profile',
                                user_id=object_location_assignment.responsible_user_id,
                                _external=True
                            )
                        )
                    else:
                        other_user_url = None
                    if object_location_assignment.confirmed:
                        responsibility_status = _(' (confirmed)')
                    elif object_location_assignment.declined:
                        responsibility_status = _(' (declined)')
                    else:
                        responsibility_status = _(' (unconfirmed)')
                    if object_location_assignment.location_id is not None and object_location_assignment.responsible_user_id is not None:
                        text += _(
                            '<a href="%(user_url)s">%(user_name)s</a> assigned this object to <a href="%(location_url)s">%(location_name)s</a> and <a href="%(other_user_url)s">user #%(responsible_user_id)s</a>%(responsibility_status)s.',
                            user_url=user_url,
                            user_name=user_name,
                            location_url=location_url,
                            location_name=location_name,
                            other_user_url=other_user_url,
                            responsible_user_id=object_location_assignment.responsible_user_id,
                            responsibility_status=responsibility_status
                        )
                    elif object_location_assignment.location_id is not None:
                        text += _(
                            '<a href="%(user_url)s">%(user_name)s</a> assigned this object to <a href="%(location_url)s">%(location_name)s</a>.',
                            user_url=user_url,
                            user_name=user_name,
                            location_url=location_url,
                            location_name=location_name
                        )
                    elif object_location_assignment.responsible_user_id is not None:
                        text += _(
                            '<a href="%(user_url)s">%(user_name)s</a> assigned this object to <a href="%(other_user_url)s">user #%(responsible_user_id)s</a>%(responsibility_status)s.',
                            user_url=user_url,
                            user_name=user_name,
                            other_user_url=other_user_url,
                            responsible_user_id=object_location_assignment.responsible_user_id,
                            responsibility_status=responsibility_status
                        )
                elif object_log_entry.type == ObjectLogEntryType.LINK_PUBLICATION:
                    doi = markupsafe.escape(object_log_entry.data['doi'])
                    text += _('<a href="%(user_url)s">%(user_name)s</a> linked publication <a href="https://dx.doi.org/%(doi)s">%(doi)s</a> to this object.', user_url=user_url, user_name=user_name, doi=doi)
                elif object_log_entry.type == ObjectLogEntryType.REFERENCE_OBJECT_IN_METADATA:
                    if object_log_entry.data['object_id'] is not None:
                        try:
                            other_object_id = int(object_log_entry.data['object_id'])
                            escaped_object_url = markupsafe.escape(flask.url_for('.object', object_id=other_object_id, _external=True))
                            permissions = logic.object_permissions.get_user_object_permissions(object_log_entry.data['object_id'], flask_login.current_user.id)
                            if Permissions.READ in permissions:
                                object_name = markupsafe.escape(get_translated_text(get_object(object_log_entry.data['object_id']).name))
                                text += _('<a href="%(user_url)s">%(user_name)s</a> referenced this object in the metadata of <a href="%(object_url)s">object %(object_name)s (#%(other_object_id)s)</a>.', user_url=user_url, user_name=user_name, object_url=escaped_object_url, object_name=object_name, other_object_id=other_object_id)
                            else:
                                text += _('<a href="%(user_url)s">%(user_name)s</a> referenced this object in the metadata of <a href="%(object_url)s">object #%(other_object_id)s</a>.', user_url=user_url, user_name=user_name, object_url=escaped_object_url, other_object_id=other_object_id)
                        except Exception:
                            text += _('<a href="%(user_url)s">%(user_name)s</a> referenced this object in the metadata of an unknown object.', user_url=user_url, user_name=user_name)
                    else:
                        text += _('<a href="%(user_url)s">%(user_name)s</a> referenced this object in the metadata of another object.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.EXPORT_TO_DATAVERSE:
                    dataverse_url = markupsafe.escape(object_log_entry.data['dataverse_url'])
                    text += _('<a href="%(user_url)s">%(user_name)s</a> exported this object to dataverse as <a href="%(dataverse_url)s">%(dataverse_url)s</a>.', user_url=user_url, user_name=user_name, dataverse_url=dataverse_url)
                elif object_log_entry.type == ObjectLogEntryType.LINK_PROJECT:
                    try:
                        project = logic.projects.get_project(object_log_entry.data['project_id'])
                        project_url = flask.url_for('.project', project_id=project.id)
                        text += _('<a href="%(user_url)s">%(user_name)s</a> linked this object to <a href="%(project_url)s">project group %(project_name)s (#%(project_id)s)</a>.', user_url=user_url, user_name=user_name, project_url=project_url, project_name=get_translated_text(project.name), project_id=project.id)
                    except logic.errors.ProjectDoesNotExistError:
                        text += _('<a href="%(user_url)s">%(user_name)s</a> linked this object to a project group.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.IMPORT_FROM_ELN_FILE:
                    text += _('<a href="%(user_url)s">%(user_name)s</a> imported this object from an .eln file.', user_url=user_url, user_name=user_name)
                elif object_log_entry.type == ObjectLogEntryType.UNLINK_PROJECT:
                    if object_log_entry.data.get('project_deleted'):
                        text += _('<a href="%(user_url)s">%(user_name)s</a> deleted the project group this object was linked to.', user_url=user_url, user_name=user_name)
                    else:
                        try:
                            project = logic.projects.get_project(object_log_entry.data['project_id'])
                            project_url = flask.url_for('.project', project_id=project.id)
                            text += _('<a href="%(user_url)s">%(user_name)s</a> removed the link of this object to <a href="%(project_url)s">project group %(project_name)s (#%(project_id)s)</a>.', user_url=user_url, user_name=user_name, project_url=project_url, project_name=get_translated_text(project.name), project_id=project.id)
                        except logic.errors.ProjectDoesNotExistError:
                            text += _('<a href="%(user_url)s">%(user_name)s</a> removed the link of this object to a project group.', user_url=user_url, user_name=user_name)
                else:
                    text += _('<a href="%(user_url)s">%(user_name)s</a> performed an unknown action.', user_url=user_url, user_name=user_name)
                activity_log_entries.append(text)

        locations_entries = []
        if 'locations' in sections:
            location_assignments = logic.locations.get_object_location_assignments(object.id)
            for location_assignment in location_assignments:
                locations_entries.append({
                    'utc_datetime': location_assignment.utc_datetime.strftime('%Y-%m-%d %H:%M') if location_assignment.utc_datetime is not None else '',
                    'assigning_user_id': location_assignment.user_id,
                    'assigning_user_name': logic.users.get_user(location_assignment.user_id).get_name() if location_assignment.user_id is not None else '',
                    'location_id': location_assignment.location_id,
                    'location_name': get_location_name(location_assignment.location_id, include_id=True, language_code=lang_code) if location_assignment.location_id else None,
                    'responsible_user_id': location_assignment.responsible_user_id,
                    'responsible_user_name': logic.users.get_user(location_assignment.responsible_user_id).get_name() if location_assignment.responsible_user_id else None,
                    'description': location_assignment.description
                })

        if 'publications' in sections:
            publications = logic.publications.get_publications_for_object(object.id)
        else:
            publications = []

        if 'files' in sections:
            files = logic.files.get_files_for_object(object.id)
            for file in files:
                exported_files[(object.id, file.id)] = file
        else:
            files = []

        if 'comments' in sections:
            comments = logic.comments.get_comments_for_object(object.id)
        else:
            comments = []

        object_url = flask.url_for('.object', object_id=object_id, _external=True)
        image = qrcode.make(object_url, image_factory=qrcode.image.pil.PilImage)
        qrcode_width, qrcode_height = image.size
        # remove margin
        margin = 40
        image = image.crop((margin, margin, qrcode_width - margin, qrcode_height - margin))
        qrcode_file = io.BytesIO()
        image.save(qrcode_file, format='PNG')
        qrcode_file.seek(0)
        qrcode_url = 'data:image/png;base64,' + base64.b64encode(qrcode_file.read()).decode('utf-8')

        if object.action_id is not None:
            action = logic.actions.get_action(object.action_id)
        else:
            action = None
        objects.append((object, action, activity_log_entries, locations_entries, publications, comments, files, qrcode_url))

    def get_object_type_name(action: Action) -> str:
        if action is None or action.type is None:
            return _('Object')
        else:
            return get_translated_text(action.type.object_name, default=_('Object'))

    files_by_object_id = {}
    for object_tuple in objects:
        files_by_object_id[object_tuple[0].object_id] = logic.files.get_files_for_object(object_tuple[0].object_id)
    html = flask.render_template(
        'pdfexport/export.html',
        get_object_type_name=get_object_type_name,
        export_date=datetime.datetime.now(datetime.timezone.utc),
        get_object_if_current_user_has_read_permissions=get_object_if_current_user_has_read_permissions,
        objects=objects,
        get_user=get_user_if_exists,
        metadata_language=lang_code,
        files_by_object_id=files_by_object_id,
        eln_import_urls={object[0].object_id: logic.eln_import.get_eln_import_object_url(object[0].object_id) for object in objects},
        IMAGE_FORMATS=IMAGE_FORMATS
    )

    # use regular user language again
    delattr(flask.g, 'override_locale')
    refresh()

    return typing.cast(bytes, HTML(
        string=html,
        url_fetcher=custom_url_fetcher,
        base_url=base_url
    ).write_pdf())
