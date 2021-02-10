
import base64
import datetime
import io
import os
import typing
import urllib.parse

import flask
import flask_login
import jinja2
import qrcode
import qrcode.image.pil
from weasyprint import default_url_fetcher, HTML

from .. import logic
from ..logic import object_log
from ..logic.objects import get_object
from ..logic.object_log import ObjectLogEntryType
from ..logic.users import get_user

from .markdown_images import IMAGE_FORMATS
from .objects import get_object_if_current_user_has_read_permissions

SECTIONS = {
    'activity_log',
    'locations',
    'publications',
    'files',
    'comments'
}


def create_pdfexport(
        object_ids: typing.Sequence[int],
        sections: typing.Set[str] = SECTIONS
):
    exported_files = {}

    base_url = flask.url_for('.index', _external=True)

    def custom_url_fetcher(url):
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
                object_id, file_id = object_id_file_id.split('/')
                object_id = int(object_id)
                file_id = int(file_id)
                file = exported_files[(object_id, file_id)]
                if file.storage == 'local' and not file.is_hidden:
                    for file_extension in IMAGE_FORMATS:
                        if file.original_file_name.endswith(file_extension):
                            image_data = file.open(read_only=True).read()
                            url = 'data:' + IMAGE_FORMATS[file_extension] + ';base64,' + base64.b64encode(image_data).decode('utf-8')
                            break
            except Exception:
                pass
        # only allow Data URLs and URLs via http or https
        if not (url.startswith('data:') or urllib.parse.urlparse(url).scheme in ('http', 'https')):
            url = ''
        return default_url_fetcher(url)

    objects = []
    for object_id in object_ids:
        object = get_object(object_id)

        activity_log_entries = []
        if 'activity_log' in sections:
            object_log_entries = object_log.get_object_log_entries(object_id=object.id, user_id=flask_login.current_user.id)
            for object_log_entry in reversed(object_log_entries):
                user_id = object_log_entry.user_id
                user_url = jinja2.escape(flask.url_for('.user_profile', user_id=user_id, _external=True))
                user_name = jinja2.escape(get_user(object_log_entry.user_id).name)
                entry_datetime = jinja2.escape(object_log_entry.utc_datetime.strftime('%Y-%m-%d %H:%M'))
                text = f'{entry_datetime} — <a href="{user_url}">{user_name} (#{user_id})</a>'
                if object_log_entry.type == ObjectLogEntryType.CREATE_BATCH:
                    text += ' created this object as part of a batch.'
                elif object_log_entry.type == ObjectLogEntryType.CREATE_OBJECT:
                    text += ' created this object.'
                elif object_log_entry.type == ObjectLogEntryType.EDIT_OBJECT:
                    text += ' edited this object.'
                elif object_log_entry.type == ObjectLogEntryType.POST_COMMENT:
                    text += ' posted a comment.'
                elif object_log_entry.type == ObjectLogEntryType.RESTORE_OBJECT_VERSION:
                    text += ' restored a previous version of this object.'
                elif object_log_entry.type == ObjectLogEntryType.UPLOAD_FILE:
                    text += ' posted a file.'
                elif object_log_entry.type == ObjectLogEntryType.USE_OBJECT_IN_MEASUREMENT:
                    try:
                        measurement_id = int(object_log_entry.data['measurement_id'])
                        object_url = jinja2.escape(flask.url_for('.object', object_id=measurement_id, _external=True))
                        permissions = logic.object_permissions.get_user_object_permissions(measurement_id, flask_login.current_user.id)
                        if logic.object_permissions.Permissions.READ in permissions:
                            measurement_name = jinja2.escape(get_object(measurement_id).data['name']['text'])
                            text += f' used this object in <a href="{object_url}">measurement {measurement_name} (#{measurement_id})</a>.'
                        else:
                            text += f' used this object in <a href="{object_url}">measurement #{measurement_id}</a>.'
                    except Exception:
                        text += ' used this object in a measurement.'
                elif object_log_entry.type == ObjectLogEntryType.USE_OBJECT_IN_SAMPLE_CREATION:
                    try:
                        sample_id = int(object_log_entry.data['sample_id'])
                        object_url = jinja2.escape(flask.url_for('.object', object_id=sample_id, _external=True))
                        permissions = logic.object_permissions.get_user_object_permissions(sample_id, flask_login.current_user.id)
                        if logic.object_permissions.Permissions.READ in permissions:
                            sample_name = jinja2.escape(get_object(sample_id).data['name']['text'])
                            text += f' used this object to create <a href="{object_url}">sample {sample_name} (#{sample_id})</a>.'
                        else:
                            text += f' used this object to create <a href="{object_url}">sample #{sample_id}</a>.'
                    except Exception:
                        text += ' used this object to create a sample.'
                elif object_log_entry.type == ObjectLogEntryType.ASSIGN_LOCATION:
                    object_location_assignment_id = object_log_entry.data['object_location_assignment_id']
                    object_location_assignment = logic.locations.get_object_location_assignment(object_location_assignment_id)
                    if object_location_assignment.location_id is not None and object_location_assignment.responsible_user_id is not None:
                        user_url = jinja2.escape(flask.url_for('.user_profile', user_id=object_location_assignment.responsible_user_id, _external=True))
                        location_url = jinja2.escape(flask.url_for('.location', location_id=object_location_assignment.location_id, _external=True))
                        text += f' assigned this object to <a href="{location_url}">location #{object_location_assignment.location_id}</a> and <a href="{user_url}">user #{object_location_assignment.responsible_user_id}</a>.'
                    elif object_location_assignment.location_id is not None:
                        location_url = jinja2.escape(flask.url_for('.location', location_id=object_location_assignment.location_id, _external=True))
                        text += f' assigned this object to <a href="{location_url}">location #{object_location_assignment.location_id}</a>.'
                    elif object_location_assignment.responsible_user_id is not None:
                        user_url = jinja2.escape(flask.url_for('.user_profile', user_id=object_location_assignment.responsible_user_id, _external=True))
                        text += f' assigned this object to <a href="{user_url}">user #{object_location_assignment.responsible_user_id}</a>.'
                elif object_log_entry.type == ObjectLogEntryType.LINK_PUBLICATION:
                    doi = jinja2.escape(object_log_entry.data['doi'])
                    text += f' linked publication <a href="https://dx.doi.org/{doi}">{doi}</a> to this object.'
                elif object_log_entry.type == ObjectLogEntryType.REFERENCE_OBJECT_IN_METADATA:
                    if object_log_entry.data['object_id'] is not None:
                        try:
                            other_object_id = int(object_log_entry.data['object_id'])
                            object_url = jinja2.escape(flask.url_for('.object', object_id=other_object_id, _external=True))
                            permissions = logic.object_permissions.get_user_object_permissions(object_log_entry.data['object_id'], flask_login.current_user.id)
                            if logic.object_permissions.Permissions.READ in permissions:
                                object_name = jinja2.escape(get_object(object_log_entry.data['object_id']).data['name']['text'])
                                text += f' referenced this object in the metadata of <a href="{object_url}">object {object_name} (#{other_object_id})</a>.'
                            else:
                                text += f' referenced this object in the metadata of <a href="{object_url}">object #{other_object_id}</a>.'
                        except Exception:
                            text += ' referenced this object in the metadata of an unknown object.'
                    else:
                        text += ' referenced this object in the metadata of another object.'
                elif object_log_entry.type == ObjectLogEntryType.EXPORT_TO_DATAVERSE:
                    dataverse_url = jinja2.escape(object_log_entry.data['dataverse_url'])
                    text += f' exported this object to dataverse as <a href="{dataverse_url}">{dataverse_url}</a>.'
                elif object_log_entry.type == ObjectLogEntryType.LINK_PROJECT:
                    try:
                        project = logic.projects.get_project(object_log_entry.data['project_id'])
                        project_url = flask.url_for('.project', project_id=project.id)
                        text += f' linked this object to <a href="{project_url}">project group {project.name} (#{project.id})</a>.'
                    except logic.errors.ProjectDoesNotExistError:
                        text += ' linked this object to a project group.'
                elif object_log_entry.type == ObjectLogEntryType.UNLINK_PROJECT:
                    if object_log_entry.data['project_deleted']:
                        text += ' deleted the project group this object was linked to.'
                    else:
                        try:
                            project = logic.projects.get_project(object_log_entry.data['project_id'])
                            project_url = flask.url_for('.project', project_id=project.id)
                            text += f' removed the link of this object to <a href="{project_url}">project group {project.name} (#{project.id})</a>.'
                        except logic.errors.ProjectDoesNotExistError:
                            text += ' removed the link of this object to a project group.'
                else:
                    text += ' performed an unknown action.'
                activity_log_entries.append(text)

        locations_entries = []
        if 'locations' in sections:
            location_assignments = logic.locations.get_object_location_assignments(object.id)
            for location_assignment in location_assignments:
                locations_entries.append({
                    'utc_datetime': location_assignment.utc_datetime.strftime('%Y-%m-%d %H:%M'),
                    'assigning_user_id': location_assignment.user_id,
                    'assigning_user_name': logic.users.get_user(location_assignment.user_id).name,
                    'location_id': location_assignment.location_id,
                    'location_name': logic.locations.get_location(location_assignment.location_id).name if location_assignment.location_id else None,
                    'responsible_user_id': location_assignment.responsible_user_id,
                    'responsible_user_name': logic.users.get_user(location_assignment.responsible_user_id).name if location_assignment.responsible_user_id else None,
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

        action = logic.actions.get_action(object.action_id)
        objects.append((object, action, activity_log_entries, locations_entries, publications, comments, files, qrcode_url))

    def get_user_if_exists(user_id):
        try:
            return get_user(user_id)
        except logic.errors.UserDoesNotExistError:
            return None

    html = flask.render_template(
        'pdfexport/export.html',
        export_date=datetime.datetime.utcnow().strftime('%Y-%m-%d'),
        get_object_if_current_user_has_read_permissions=get_object_if_current_user_has_read_permissions,
        objects=objects,
        get_user=get_user_if_exists
    )

    return HTML(
        string=html,
        url_fetcher=custom_url_fetcher,
        base_url=base_url
    ).write_pdf()
