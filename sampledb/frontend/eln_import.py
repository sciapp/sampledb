# coding: utf-8
"""

"""
from base64 import b64decode
import typing

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import FileField, FieldList, FormField, SelectField, StringField, BooleanField
from wtforms.validators import InputRequired, ValidationError

from . import frontend
from .federation_forms import ModifyELNIdentityForm
from .utils import check_current_user_is_not_readonly
from .. import logic
from ..utils import FlaskResponseT
from ..logic.errors import UserDoesNotExistError, ELNUserInFederatedIdentityError
from ..models.users import FederatedIdentity


class UploadELNFileForm(FlaskForm):
    eln_file = FileField(validators=[InputRequired()])


class ImportELNFileObjectForm(FlaskForm):
    action_type_id = SelectField(coerce=int, validators=[InputRequired()])


class ImportELNFileForm(FlaskForm):
    object_forms = FieldList(FormField(ImportELNFileObjectForm))
    federated_identities = StringField()


class DeleteELNImportForm(FlaskForm):
    submit = StringField(validators=[InputRequired()])

    def validate_submit(form, field: StringField) -> None:
        if not field.data == 'delete':
            raise ValidationError("")


@frontend.route('/eln_imports', methods=['POST', 'GET'])
@flask_login.login_required
def upload_eln_import() -> FlaskResponseT:
    if not flask.current_app.config['ENABLE_ELN_FILE_IMPORT']:
        return flask.abort(404)
    check_current_user_is_not_readonly()

    logic.eln_import.remove_expired_eln_imports()

    upload_eln_file_form = UploadELNFileForm()

    if upload_eln_file_form.validate_on_submit():
        eln_file = upload_eln_file_form.eln_file.data
        zip_bytes = eln_file.read()
        # TODO: check that zip_bytes belong to ELN file
        eln_import_id = logic.eln_import.create_eln_import(
            user_id=flask_login.current_user.id,
            file_name=eln_file.filename,
            zip_bytes=zip_bytes
        ).id
        return flask.redirect(flask.url_for('.eln_import', eln_import_id=eln_import_id))

    pending_eln_imports = logic.eln_import.get_pending_eln_imports(flask_login.current_user.id)
    delete_eln_import_forms = [
        DeleteELNImportForm()
        for _ in pending_eln_imports
    ]

    return flask.render_template(
        'eln_files/upload_eln_file.html',
        upload_eln_file_form=upload_eln_file_form,
        pending_eln_imports=pending_eln_imports,
        delete_eln_import_forms=delete_eln_import_forms,
    )


@frontend.route('/eln_imports/<int:eln_import_id>', methods=['POST', 'GET'])
@flask_login.login_required
def eln_import(eln_import_id: int) -> FlaskResponseT:
    logic.eln_import.remove_expired_eln_imports()

    try:
        eln_import = logic.eln_import.get_eln_import(eln_import_id)
    except logic.errors.ELNImportDoesNotExistError:
        return flask.abort(404)
    if not eln_import.imported and eln_import.user_id != flask_login.current_user.id and not flask_login.current_user.has_admin_permissions:
        return flask.abort(403)
    if eln_import.imported:
        imported_users = logic.eln_import.get_eln_import_users(eln_import_id)
        fed_identities: dict[int, list[tuple[typing.Optional[ModifyELNIdentityForm], FederatedIdentity]]] = {}

        for eln_user in imported_users:
            identity = logic.users.get_federated_identity_by_eln_user(eln_user.id)
            if identity:
                identities = fed_identities.get(identity.user.id, [])
                form = ModifyELNIdentityForm(eln_user_id=identity.local_fed_id) if identity.user_id == flask_login.current_user.id else None
                identities.append((form, identity))
                fed_identities[identity.user.id] = identities

        return flask.render_template(
            'eln_files/view_eln_file.html',
            eln_import=eln_import,
            imported_objects=logic.eln_import.get_eln_import_objects(eln_import_id),
            imported_users=logic.eln_import.get_eln_import_users(eln_import_id),
            fed_identities=fed_identities
        )
    else:
        if not flask.current_app.config['ENABLE_ELN_FILE_IMPORT']:
            return flask.abort(404)
        check_current_user_is_not_readonly()

        delete_eln_import_form = DeleteELNImportForm()
        if delete_eln_import_form.validate_on_submit():
            logic.eln_import.delete_eln_import(eln_import_id)
            flask.flash(_("Successfully deleted .eln file."), 'success')
            return flask.redirect(flask.url_for('.upload_eln_import'))

        try:
            parsed_eln_file_data = logic.eln_import.parse_eln_file(
                eln_import_id=eln_import_id
            )
        except logic.errors.InvalidELNFileError as e:
            message = str(e)
            logic.eln_import.mark_eln_import_invalid(eln_import_id, message)
            flask.flash(_("Failed to parse .eln file: %(message)s", message=message), 'error')
            return flask.redirect(flask.url_for('.upload_eln_import'))

        valid_action_types = [
            (action_type.id, action_type)
            for action_type in logic.action_types.get_action_types()
            if action_type.component_id is None and not action_type.disable_create_objects
        ]
        import_eln_file_form = ImportELNFileForm(
            object_forms=[ImportELNFileObjectForm()] * len(parsed_eln_file_data.objects),
            attach_federated_identity=[BooleanField(name="x")] * len(parsed_eln_file_data.users)
        )
        for object_data, object_form in zip(parsed_eln_file_data.objects, import_eln_file_form.object_forms.entries):
            object_form.action_type_id.choices = valid_action_types
            if not import_eln_file_form.is_submitted() and object_data.type_id is not None:
                object_form.action_type_id.data = object_data.type_id

        if import_eln_file_form.validate_on_submit():
            imported_object_ids, users_by_id, errors = logic.eln_import.import_eln_file(
                eln_import_id=eln_import_id,
                action_type_ids=[
                    object_form.action_type_id.data
                    for object_form in import_eln_file_form.object_forms.entries
                ]
            )

            if errors:
                if imported_object_ids:
                    flask.flash(
                        _('%(num_imported_objects)s objects were imported, but the following errors occurred:', num_imported_objects=len(imported_object_ids)) + ' ' + ' '.join(errors),
                        'error'
                    )
                else:
                    flask.flash(
                        _('The following errors occurred while trying to import objects:', num_imported_objects=len(imported_object_ids)) + ' ' + ' '.join(errors),
                        'error'
                    )
                    return flask.redirect(flask.url_for('.eln_import', eln_import_id=eln_import_id))
            else:
                if len(imported_object_ids) == 1:
                    flask.flash(
                        _('Successfully imported an object.'),
                        'success'
                    )
                else:
                    flask.flash(
                        _('Successfully imported %(num_imported_objects)s objects.', num_imported_objects=len(imported_object_ids)),
                        'success'
                    )

            failed_identities: list[str] = []
            for encoded_user_id in import_eln_file_form.federated_identities.data.split(","):
                eln_user_id = b64decode(encoded_user_id).decode("utf-8")
                database_user = users_by_id.get(eln_user_id, None)
                if database_user:
                    try:
                        logic.users.create_eln_federated_identity(user_id=flask_login.current_user.id, eln_user_id=database_user.id)
                    except (UserDoesNotExistError, ELNUserInFederatedIdentityError):
                        failed_identities.append(eln_user_id)

            if failed_identities:
                flask.flash(_("An error occured: Failed to create federated identity."), "error")

            if len(imported_object_ids) == 1:
                return flask.redirect(flask.url_for('.object', object_id=imported_object_ids[0]))
            else:
                return flask.redirect(flask.url_for('.objects', ids=','.join(str(object_id) for object_id in imported_object_ids)))
        return flask.render_template(
            'eln_files/import_eln_file.html',
            import_eln_file_form=import_eln_file_form,
            parsed_eln_file_data=parsed_eln_file_data,
        )
