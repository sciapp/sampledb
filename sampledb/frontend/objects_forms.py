# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, TextAreaField, HiddenField, FileField, StringField, BooleanField
from wtforms.validators import InputRequired, ValidationError

from ..logic import errors
from ..logic.object_permissions import Permissions
from ..logic.publications import simplify_doi
from ..logic.errors import InvalidDOIError

from .validators import ObjectIdValidator
from ..logic.utils import parse_url


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
    url = StringField()

    def validate_url(form, field):
        try:
            parse_url(field.data)
        except errors.InvalidURLError:
            raise ValidationError('Invalid URL')


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


class ObjectNewShareAccessForm(FlaskForm):
    component_id = IntegerField(validators=[InputRequired()])

    data = BooleanField()
    action = BooleanField()
    users = BooleanField()
    files = BooleanField()
    comments = BooleanField()
    object_location_assignments = BooleanField()


class ObjectEditShareAccessForm(FlaskForm):
    component_id = IntegerField(validators=[InputRequired()])

    data = BooleanField()
    action = BooleanField()
    users = BooleanField()
    files = BooleanField()
    comments = BooleanField()
    object_location_assignments = BooleanField()
