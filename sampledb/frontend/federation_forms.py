# coding: utf-8
"""

"""

import flask
import flask_login

from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, SelectField, BooleanField
from wtforms.validators import Length, DataRequired, ValidationError, InputRequired, AnyOf


class CreateAPITokenForm(FlaskForm):
    description = StringField('description', validators=[Length(min=1, max=100)])


class AddOwnAPITokenForm(FlaskForm):
    token = StringField('token', validators=[Length(min=1, max=100)])
    description = StringField('description', validators=[Length(min=1, max=100)])


class AuthenticationMethodForm(FlaskForm):
    id = IntegerField('Authentication_method_id', validators=[DataRequired()])
    submit = SubmitField('Remove')


class AddComponentForm(FlaskForm):
    address = StringField(validators=[Length(min=0, max=100)])
    uuid = StringField(validators=[Length(min=1, max=100)])
    name = StringField(validators=[Length(min=0, max=100)])
    description = StringField()


class EditComponentForm(FlaskForm):
    address = StringField(validators=[Length(min=0, max=100)])
    name = StringField(validators=[Length(min=0, max=100)])
    description = StringField()


class SyncComponentForm(FlaskForm):
    ignore_last_sync_time = BooleanField(default=False)


class EditAliasForm(FlaskForm):
    component = IntegerField('Component', validators=[InputRequired()])
    name = StringField('Full Name')
    use_real_name = BooleanField('Use real name')
    use_real_email = BooleanField('Use real email')
    use_real_orcid = BooleanField('Use real ORCID iD')
    affiliation = StringField('Affiliation')
    use_real_affiliation = BooleanField('Use real affiliation')
    role = StringField('Role')
    use_real_role = BooleanField('Use real role')
    submit = SubmitField('Change Alias')

    def validate_name(self, field: StringField) -> None:
        if flask.current_app.config['ENFORCE_SPLIT_NAMES'] and flask_login.current_user.type.name.lower() == "person":
            name = field.data
            if name and ', ' not in name[1:-1]:
                raise ValidationError(_('Please enter your name as: surname, given names.'))


class AddAliasForm(FlaskForm):
    component = SelectField('Database', validators=[InputRequired()])
    name = StringField('Full Name')
    use_real_name = BooleanField('Use real name')
    use_real_email = BooleanField('Use real email')
    use_real_orcid = BooleanField('Use real ORCID iD')
    affiliation = StringField('Affiliation')
    use_real_affiliation = BooleanField('Use real affiliation')
    role = StringField('Role')
    use_real_role = BooleanField('Use real role')
    submit = SubmitField('Add Alias')

    def validate_name(self, field: StringField) -> None:
        if flask.current_app.config['ENFORCE_SPLIT_NAMES'] and flask_login.current_user.type.name.lower() == "person":
            name = field.data
            if name and ', ' not in name[1:-1]:
                raise ValidationError(_('Please enter your name as: surname, given names.'))


class DeleteAliasForm(FlaskForm):
    component = IntegerField('Component', validators=[InputRequired()])


class ModifyELNIdentityForm(FlaskForm):
    type = StringField(validators=[AnyOf(["remove", "revoke", "enable"])])
    eln_user_id = IntegerField(validators=[InputRequired()])


class FederatedUserCreationForm(FlaskForm):
    username = StringField(validators=[InputRequired()])

    def validate_username(self, field: StringField) -> None:
        if flask.current_app.config['ENFORCE_SPLIT_NAMES']:
            username = field.data
            if ', ' not in username[1:-1]:
                raise ValidationError(_("Please enter your name as: surname, given names."))
