# coding: utf-8
"""

"""

import flask
import flask_login
from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, FloatField, TextAreaField, HiddenField, FileField, StringField, BooleanField, RadioField
from wtforms.validators import InputRequired, ValidationError, Optional

from ...logic import errors
from ...models import Permissions, User
from ...logic.publications import simplify_doi
from ...logic.errors import InvalidDOIError
from ...logic.utils import get_translated_text
from ...logic.groups import get_groups
from ...logic.users import get_users
from ...logic.projects import get_projects
from ..validators import ObjectIdValidator
from ...logic.utils import parse_url


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

    def validate_file_source(form, field: StringField) -> None:
        if field.data not in ['local']:
            raise ValidationError('Invalid file source')


def _validate_url(url: str) -> None:
    try:
        parse_url(url)
    except errors.InvalidURLError:
        raise ValidationError(0)
    except errors.URLTooLongError:
        raise ValidationError(1)
    except errors.InvalidIPAddressError:
        raise ValidationError(2)
    except errors.InvalidPortNumberError:
        raise ValidationError(3)


class ExternalLinkForm(FlaskForm):
    url = StringField()

    def validate_url(form, field: StringField) -> None:
        _validate_url(field.data)


class FileInformationForm(FlaskForm):
    title = StringField()
    url = StringField()
    description = TextAreaField()

    def validate_url(form, field: StringField) -> None:
        if field.data is not None:
            _validate_url(field.data)


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

    def validate_doi(form, field: StringField) -> None:
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


class UseInActionForm(FlaskForm):
    action_type_id = HiddenField()
    action_id = HiddenField()
    objects = HiddenField(validators=[InputRequired()])


class GenerateLabelsForm(FlaskForm):
    form_variant = SelectField(validators=[InputRequired()], choices=[('mixed-formats', lazy_gettext('Mixed label formats')), ('fixed-width', lazy_gettext('Fixed-width labels')), ('minimal-height', lazy_gettext('Minimal-height labels'))])
    objects = HiddenField(validators=[InputRequired()])
    paper_size = SelectField(validators=[InputRequired()], choices=[("DIN A4 (Portrait)", lazy_gettext('DIN A4 (Portrait)')), ("DIN A4 (Landscape)", lazy_gettext('DIN A4 (Landscape)')), ("Letter (Portrait)", lazy_gettext('Letter / ANSI A (Portrait)')), ("Letter (Landscape)", lazy_gettext('Letter / ANSI A (Landscape)'))])
    label_width = FloatField()
    min_label_width = FloatField()
    min_label_height = FloatField()
    labels_per_object = IntegerField()
    center_qr_ghs = BooleanField()
    qr_ghs_side_by_side = BooleanField()
    include_qr = BooleanField()


class EditPermissionsForm(FlaskForm):
    objects = HiddenField(validators=[InputRequired()])
    target_type = SelectField(validators=[InputRequired()])
    update_mode = RadioField(validators=[InputRequired()], choices=[('set-min', lazy_gettext('Set minimum Permissions')), ('set-max', lazy_gettext('Set maximum Permissions'))])
    groups = SelectField(validators=[Optional()])
    project_groups = SelectField(validators=[Optional()])
    users = SelectField(validators=[Optional()])
    permission = RadioField(validators=[InputRequired()], choices=[
                            (Permissions.NONE.name.lower(), lazy_gettext('None')),
                            (Permissions.READ.name.lower(), lazy_gettext('Read')),
                            (Permissions.WRITE.name.lower(), lazy_gettext('Write')),
                            (Permissions.GRANT.name.lower(), lazy_gettext('Grant'))
                            ])

    def __init__(self) -> None:
        super().__init__()
        target_type_choices = [
            ('signed-in-users', lazy_gettext('All Signed-In Users')),
            ('group', lazy_gettext('Basic Group')),
            ('project-group', lazy_gettext('Project Group')),
            ('user', lazy_gettext('User'))
        ]
        if flask.current_app.config["ENABLE_ANONYMOUS_USERS"]:
            target_type_choices.insert(1, ('anonymous', lazy_gettext('Anonymous Users')))

        self.target_type.choices = target_type_choices
        self.groups.choices = [(group.id, get_translated_text(group.name)) for group in get_groups()]
        self.project_groups.choices = [(project.id, get_translated_text(project.name)) for project in get_projects()]
        self.users.choices = [(user.id, f"{user.name} (#{user.id})") for user in get_users(order_by=User.id, exclude_fed=True, exclude_eln_import=True, exclude_hidden=not flask_login.current_user.is_admin or not flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN'])]
