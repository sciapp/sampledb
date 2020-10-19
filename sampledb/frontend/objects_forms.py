# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, SelectField, IntegerField, TextAreaField, HiddenField, FileField, StringField
from wtforms.validators import InputRequired, ValidationError, url

from ..logic.object_permissions import Permissions
from ..logic.publications import simplify_doi
from ..logic.errors import InvalidDOIError

from .validators import ObjectIdValidator


class ObjectUserPermissionsForm(FlaskForm):
    user_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ObjectGroupPermissionsForm(FlaskForm):
    group_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ObjectProjectPermissionsForm(FlaskForm):
    project_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ObjectPermissionsForm(FlaskForm):
    public_permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ)],
        validators=[InputRequired()]
    )
    user_permissions = FieldList(FormField(ObjectUserPermissionsForm), min_entries=0)
    group_permissions = FieldList(FormField(ObjectGroupPermissionsForm), min_entries=0)
    project_permissions = FieldList(FormField(ObjectProjectPermissionsForm), min_entries=0)


class ObjectForm(FlaskForm):
    pass


class ObjectVersionRestoreForm(FlaskForm):
    pass


class CommentForm(FlaskForm):
    content = TextAreaField(validators=[InputRequired()])


class FileForm(FlaskForm):
    file_source = HiddenField(validators=[InputRequired()])
    file_names = HiddenField()
    local_files = FileField()

    def validate_file_source(form, field):
        if field.data not in ['local']:
            raise ValidationError('Invalid file source')


class ExternalLinkForm(FlaskForm):
    url = StringField(validators=[url()])


class FileInformationForm(FlaskForm):
    title = StringField()
    description = TextAreaField()


class FileHidingForm(FlaskForm):
    reason = TextAreaField()


class ObjectLocationAssignmentForm(FlaskForm):
    location = SelectField(validators=[InputRequired()])
    responsible_user = SelectField(validators=[InputRequired()])
    description = StringField()


class ObjectPublicationForm(FlaskForm):
    doi = StringField()
    title = StringField()
    object_name = StringField()

    def validate_doi(form, field):
        try:
            field.data = simplify_doi(field.data)
        except InvalidDOIError:
            raise ValidationError('Please enter a valid DOI')


class CopyPermissionsForm(FlaskForm):
    object_id = SelectField(validators=[ObjectIdValidator(Permissions.GRANT), InputRequired()], validate_choice=False)
