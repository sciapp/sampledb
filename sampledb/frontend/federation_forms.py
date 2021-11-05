# coding: utf-8
"""

"""

import flask
import flask_login
import re

from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, SelectField
from wtforms.validators import Length, DataRequired, ValidationError, InputRequired


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
    pass


class EditAliasForm(FlaskForm):
    component = IntegerField('Component')
    name = StringField('Full Name')
    email = StringField('Contact Email')
    orcid = StringField('ORCID iD')
    affiliation = StringField('Affiliation')
    role = StringField()
    submit = SubmitField('Change Alias')

    def __init_(self, name=None, email=None):
        super(EditAliasForm, self).__init__()

    def validate_name(self, field):
        if flask.current_app.config['ENFORCE_SPLIT_NAMES'] and flask_login.current_user.type.name.lower() == "person":
            name = field.data
            if ', ' not in name[1:-1]:
                raise ValidationError(_('Please enter your name as: surname, given names.'))

    def validate_orcid(self, field):
        orcid = field.data
        # accept empty ORCID iDs
        if orcid is None:
            return
        orcid = orcid.strip()
        if not orcid:
            return
        # accept full ORCID iDs
        orcid_prefix = 'https://orcid.org/'
        if orcid.startswith(orcid_prefix):
            orcid = orcid[len(orcid_prefix):]
        # check ORCID iD syntax
        if not re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{4}', orcid, flags=re.ASCII):
            raise ValidationError(_('Please enter a valid ORCID iD.'))
        # keep sanitized ORCID iD on success
        field.data = orcid


class AddAliasForm(FlaskForm):
    component = SelectField('Database', validators=[InputRequired()])
    name = StringField('Full Name')
    email = StringField('Contact Email')
    orcid = StringField('ORCID iD')
    affiliation = StringField('Affiliation')
    role = StringField('Role')
    submit = SubmitField('Add Alias')

    def __init_(self, name=None, email=None):
        super(AddAliasForm, self).__init__()

    def validate_name(self, field):
        if flask.current_app.config['ENFORCE_SPLIT_NAMES'] and flask_login.current_user.type.name.lower() == "person":
            name = field.data
            if ', ' not in name[1:-1]:
                raise ValidationError(_('Please enter your name as: surname, given names.'))

    def validate_orcid(self, field):
        orcid = field.data
        # accept empty ORCID iDs
        if orcid is None:
            return
        orcid = orcid.strip()
        if not orcid:
            return
        # accept full ORCID iDs
        orcid_prefix = 'https://orcid.org/'
        if orcid.startswith(orcid_prefix):
            orcid = orcid[len(orcid_prefix):]
        # check ORCID iD syntax
        if not re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{4}', orcid, flags=re.ASCII):
            raise ValidationError(_('Please enter a valid ORCID iD.'))
        # keep sanitized ORCID iD on success
        field.data = orcid
