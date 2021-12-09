# coding: utf-8
"""

"""

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import InputRequired

from . import frontend
from .. import logic
from .pdfexport import create_pdfexport


class CreateExportForm(FlaskForm):
    file_extension = SelectField(
        choices=[],
        validators=[InputRequired()]
    )


@frontend.route('/users/me/export')
@flask_login.login_required
def export_self():
    return flask.redirect(
        flask.url_for('.export', user_id=flask_login.current_user.id)
    )


@frontend.route('/users/<int:user_id>/export', methods=['POST', 'GET'])
@flask_login.login_required
def export(user_id):
    if user_id != flask_login.current_user.id and not flask_login.current_user.is_admin:
        return flask.abort(403)

    create_export_form = CreateExportForm()
    create_export_form.file_extension.choices = [
        ('.pdf', _('PDF file'))
    ] + [
        (file_extension, _(file_format_info[0]))
        for file_extension, file_format_info in logic.export.FILE_FORMATS.items()
    ]
    if create_export_form.validate_on_submit():
        file_extension = create_export_form.file_extension.data
        if file_extension == '.pdf':
            readable_objects = logic.object_permissions.get_objects_with_permissions(
                user_id,
                logic.object_permissions.Permissions.READ
            )
            file_bytes = create_pdfexport(list(sorted(
                object.id
                for object in readable_objects
            )))
            file_type = 'application/pdf'
        elif file_extension in logic.export.FILE_FORMATS:
            file_bytes = logic.export.FILE_FORMATS[file_extension][1](user_id)
            file_type = logic.export.FILE_FORMATS[file_extension][2]
        else:
            flask.flash(_('Please select an export format.'), 'warning')
            file_bytes = None
            file_type = None
        if file_bytes:
            return flask.Response(
                file_bytes,
                200,
                headers={
                    'Content-Type': file_type,
                    'Content-Disposition': f'attachment; filename=sampledb_export{file_extension}'
                }
            )
    return flask.render_template(
        'export.html',
        create_export_form=create_export_form
    )
