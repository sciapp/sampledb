# coding: utf-8
"""

"""
import io
import os
import typing
import zipfile

import flask
import flask_login
import itsdangerous
import werkzeug.utils
from flask_babel import _

from .. import frontend
from ... import logic
from ...logic.objects import get_object
from ...models import Permissions
from ...logic.errors import UserDoesNotExistError, FederationFileNotAvailableError
from .forms import FileForm, FileInformationForm, FileHidingForm, ExternalLinkForm
from ...utils import object_permissions_required, FlaskResponseT
from ..utils import check_current_user_is_not_readonly
from .permissions import on_unauthorized
from ...logic.temporary_files import create_temporary_file, delete_expired_temporary_files


@frontend.route('/objects/<int:object_id>/files/')
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def object_files(object_id: int) -> FlaskResponseT:
    files = logic.files.get_files_for_object(object_id)
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, 'w') as zip_file:
        for file in files:
            if file.is_hidden:
                continue
            if file.storage in {'database', 'federation'}:
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
def object_file(object_id: int, file_id: int) -> FlaskResponseT:
    file = logic.files.get_file_for_object(object_id, file_id)
    if file is None:
        return flask.abort(404)
    if file.is_hidden:
        return flask.abort(403)
    if file.storage in ('database', 'federation'):
        if 'preview' in flask.request.args:
            mime_types = flask.current_app.config.get('MIME_TYPES', {})
            if file.preview_image_binary_data is not None and file.preview_image_mime_type is not None and file.preview_image_mime_type.lower() in mime_types.values():
                return flask.send_file(io.BytesIO(file.preview_image_binary_data), mimetype=file.preview_image_mime_type.lower(), last_modified=file.utc_datetime)
            file_extension = os.path.splitext(file.original_file_name)[1]
            mime_type = mime_types.get(file_extension, None)
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
def update_file_information(object_id: int, file_id: int) -> FlaskResponseT:
    check_current_user_is_not_readonly()
    object = get_object(object_id)
    if object.fed_object_id is not None:
        flask.flash(_('Uploading files for imported objects is not yet supported.'), 'error')
        return flask.abort(403)
    if object.action_id is None:
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
        return flask.redirect(flask.url_for('.object', object_id=object_id, _anchor=f'file-{file_id}'))
    else:
        if 'url' in form.errors:
            errorcode = form.errors['url']
            return flask.redirect(flask.url_for('.object', object_id=object_id, edit_invalid_link_file=file_id, edit_invalid_link_error=errorcode, _anchor=f'file-{file_id}'))
        return flask.abort(400)


@frontend.route('/objects/<int:object_id>/files/<int:file_id>/hide', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def hide_file(object_id: int, file_id: int) -> FlaskResponseT:
    check_current_user_is_not_readonly()
    object = get_object(object_id)
    if object.fed_object_id is not None or object.action_id is None:
        return flask.abort(403)
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
    return flask.redirect(flask.url_for('.object', object_id=object_id, _anchor=f'file-{file_id}'))


@frontend.route('/objects/<int:object_id>/files/mobile_upload/<token>', methods=['GET'])
def mobile_file_upload(object_id: int, token: str) -> FlaskResponseT:
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
def post_mobile_file_upload(object_id: int, token: str) -> FlaskResponseT:
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
        if file_storage.filename is not None:
            file_name = werkzeug.utils.secure_filename(file_storage.filename)
        else:
            file_name = 'file'
        logic.files.create_database_file(object_id, user_id, file_name, typing.cast(typing.Callable[[typing.BinaryIO], None], lambda stream, file_storage=file_storage: file_storage.save(dst=stream)))
    return flask.render_template('mobile_upload_success.html')


@frontend.route('/objects/<int:object_id>/files/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_files(object_id: int) -> FlaskResponseT:
    check_current_user_is_not_readonly()
    object = get_object(object_id)
    if object.fed_object_id is not None or object.action_id is None:
        return flask.abort(403)
    external_link_form = ExternalLinkForm()
    file_form = FileForm()
    if file_form.validate_on_submit():
        file_source = file_form.file_source.data
        if file_source == 'local':
            files = flask.request.files.getlist(file_form.local_files.name)
            for file_storage in files:
                if file_storage.filename is not None:
                    file_name = werkzeug.utils.secure_filename(file_storage.filename)
                else:
                    file_name = 'file'
                logic.files.create_database_file(object_id, flask_login.current_user.id, file_name, typing.cast(typing.Callable[[typing.BinaryIO], None], lambda stream, file_storage=file_storage: file_storage.save(dst=stream)))
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


@frontend.route('/objects/temporary_files/', methods=['POST'])
@flask_login.login_required
def temporary_file_upload() -> FlaskResponseT:
    delete_expired_temporary_files()
    context_id_token = flask.request.form.get('context_id_token', default='')
    if not context_id_token:
        return flask.abort(400)
    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='temporary-file-upload')
    try:
        user_id, context_id = serializer.loads(context_id_token, max_age=flask.current_app.config['TEMPORARY_FILE_TIME_LIMIT'])
    except itsdangerous.BadData:
        return flask.abort(400)
    if user_id != flask_login.current_user.id:
        return flask.abort(400)
    files = flask.request.files.getlist('file')
    if len(files) != 1:
        return flask.abort(400)
    file = files[0]
    file_name = file.filename or ''
    binary_data = file.stream.read()
    temporary_file = create_temporary_file(
        context_id=context_id,
        file_name=file_name,
        user_id=user_id,
        binary_data=binary_data
    )
    return str(temporary_file.id)
