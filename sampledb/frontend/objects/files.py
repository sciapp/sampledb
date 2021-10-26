# coding: utf-8
"""

"""
import io
import os
import zipfile

import flask
import flask_login
import itsdangerous
import werkzeug.utils
from flask_babel import _

from .. import frontend
from ... import logic
from ...logic.objects import get_object
from ...logic.object_permissions import Permissions
from ...logic.errors import UserDoesNotExistError, FederationFileNotAvailableError
from .forms import FileForm, FileInformationForm, FileHidingForm, ExternalLinkForm
from ...utils import object_permissions_required
from ..utils import check_current_user_is_not_readonly
from .permissions import on_unauthorized


@frontend.route('/objects/<int:object_id>/files/')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_files(object_id):
    files = logic.files.get_files_for_object(object_id)
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, 'w') as zip_file:
        for file in files:
            if file.is_hidden:
                continue
            if file.storage in {'local', 'database', 'federation'}:
                try:
                    file_bytes = file.open(read_only=True).read()
                except Exception:
                    pass
                else:
                    zip_file.writestr(os.path.basename(file.original_file_name), file_bytes)
    return flask.Response(
        zip_bytes.getvalue(),
        200,
        headers={
            'Content-Type': 'application/zip',
            'Content-Disposition': f'attachment; filename=object_{object_id}_files.zip'
        }
    )


@frontend.route('/objects/<int:object_id>/files/<int:file_id>', methods=['GET'])
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_file(object_id, file_id):
    file = logic.files.get_file_for_object(object_id, file_id)
    if file is None:
        return flask.abort(404)
    if file.is_hidden:
        return flask.abort(403)
    if file.storage in ('local', 'database', 'federation'):
        if 'preview' in flask.request.args:
            file_extension = os.path.splitext(file.original_file_name)[1]
            mime_type = flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, None)
            if mime_type is not None:
                try:
                    return flask.send_file(file.open(), mimetype=mime_type, last_modified=file.utc_datetime)
                except FederationFileNotAvailableError:
                    flask.flash(_('File stored in other database is not available.'), 'error')
                    return flask.abort(404)
        try:
            return flask.send_file(file.open(), as_attachment=True, download_name=file.original_file_name, last_modified=file.utc_datetime)
        except FederationFileNotAvailableError:
            flask.flash(_('File stored in other database is not available.'), 'error')
            return flask.abort(404)
    # TODO: better error handling
    return flask.abort(404)


@frontend.route('/objects/<int:object_id>/files/<int:file_id>', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def update_file_information(object_id, file_id):
    check_current_user_is_not_readonly()
    object = get_object(object_id)
    if object.fed_object_id is not None:
        flask.flash(_('Uploading files for imported objects is not yet supported.'), 'error')
        return flask.abort(403)
    form = FileInformationForm()
    if form.validate_on_submit():
        title = form.title.data
        url = form.url.data
        description = form.description.data
        try:
            logic.files.update_file_information(
                object_id=object_id,
                file_id=file_id,
                user_id=flask_login.current_user.id,
                title=title,
                url=url,
                description=description
            )
        except logic.errors.FileDoesNotExistError:
            return flask.abort(404)
        return flask.redirect(flask.url_for('.object', object_id=object_id, _anchor='file-{}'.format(file_id)))
    else:
        if 'url' in form.errors:
            errorcode = form.errors['url']
            return flask.redirect(flask.url_for('.object', object_id=object_id, edit_invalid_link_file=file_id, edit_invalid_link_error=errorcode, _anchor='file-{}'.format(file_id)))
        return flask.abort(400)


@frontend.route('/objects/<int:object_id>/files/<int:file_id>/hide', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def hide_file(object_id, file_id):
    check_current_user_is_not_readonly()
    form = FileHidingForm()
    if not form.validate_on_submit():
        return flask.abort(400)
    reason = form.reason.data
    try:
        logic.files.hide_file(
            object_id=object_id,
            file_id=file_id,
            user_id=flask_login.current_user.id,
            reason=reason
        )
    except logic.errors.FileDoesNotExistError:
        return flask.abort(404)
    flask.flash(_('The file was hidden successfully.'), 'success')
    return flask.redirect(flask.url_for('.object', object_id=object_id, _anchor='file-{}'.format(file_id)))


@frontend.route('/objects/<int:object_id>/files/mobile_upload/<token>', methods=['GET'])
def mobile_file_upload(object_id: int, token: str):
    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
    try:
        user_id, object_id = serializer.loads(token, max_age=15 * 60)
    except itsdangerous.BadSignature:
        return flask.abort(400)
    try:
        user = logic.users.get_user(user_id)
    except UserDoesNotExistError:
        return flask.abort(403)
    if user.is_readonly:
        return flask.abort(403)
    return flask.render_template('mobile_upload.html')


@frontend.route('/objects/<int:object_id>/files/mobile_upload/<token>', methods=['POST'])
def post_mobile_file_upload(object_id: int, token: str):
    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
    try:
        user_id, object_id = serializer.loads(token, max_age=15 * 60)
    except itsdangerous.BadSignature:
        return flask.abort(400)
    try:
        user = logic.users.get_user(user_id)
    except UserDoesNotExistError:
        return flask.abort(403)
    if user.is_readonly:
        return flask.abort(403)
    files = flask.request.files.getlist('file_input')
    if not files:
        return flask.redirect(
            flask.url_for(
                '.mobile_file_upload',
                object_id=object_id,
                token=token
            )
        )
    for file_storage in files:
        file_name = werkzeug.utils.secure_filename(file_storage.filename)
        logic.files.create_database_file(object_id, user_id, file_name, lambda stream: file_storage.save(dst=stream))
    return flask.render_template('mobile_upload_success.html')


@frontend.route('/objects/<int:object_id>/files/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_files(object_id):
    check_current_user_is_not_readonly()
    external_link_form = ExternalLinkForm()
    file_form = FileForm()
    if file_form.validate_on_submit():
        file_source = file_form.file_source.data
        if file_source == 'local':
            files = flask.request.files.getlist(file_form.local_files.name)
            for file_storage in files:
                file_name = werkzeug.utils.secure_filename(file_storage.filename)
                logic.files.create_database_file(object_id, flask_login.current_user.id, file_name, lambda stream: file_storage.save(dst=stream))
            flask.flash(_('Successfully uploaded files.'), 'success')
        else:
            flask.flash(_('Failed to upload files.'), 'error')
    elif external_link_form.validate_on_submit():
        url = external_link_form.url.data
        logic.files.create_url_file(object_id, flask_login.current_user.id, url)
        flask.flash(_('Successfully posted link.'), 'success')
    elif external_link_form.errors:
        errorcode = 1
        if 'url' in external_link_form.errors:
            errorcode = external_link_form.errors['url']

        flask.flash(_('Failed to post link.'), 'error')
        return flask.redirect(flask.url_for('.object', object_id=object_id, invalid_link_error=errorcode, _anchor='anchor-post-link'))
    else:
        flask.flash(_('Failed to upload files.'), 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))
