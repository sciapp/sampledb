# coding: utf-8
"""

"""
import typing

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, RadioField, PasswordField, SubmitField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, Email, ValidationError

from .utils import validate_orcid


class NewUserForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Contact Email', validators=[DataRequired("Please enter the contact email."), Email("Please enter your contact email.")])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=3)])
    authentication_method = RadioField('Authentication Method', choices=[('E', 'Email'), ('O', 'Other')], default='O')
    login = StringField('Login', validators=[DataRequired()])
    type = RadioField('Usertype', choices=[('P', 'Person'), ('O', 'Other')], default='O')
    admin = RadioField('Admin', choices=[('0', 'No'), ('1', 'Yes')], default='0')
    submit = SubmitField('Register')


class ChangeUserForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=1)])
    email = StringField('Contact Email', validators=[DataRequired("Please enter the contact email."), Email("Please enter your contact email.")])
    orcid = StringField('ORCID iD')
    affiliation = StringField('Affiliation')
    role = StringField()
    submit = SubmitField('Change Settings')

    def validate_name(self, field: StringField) -> None:
        if flask.current_app.config['ENFORCE_SPLIT_NAMES'] and flask_login.current_user.type.name.lower() == "person":
            name = field.data
            if ', ' not in name[1:-1]:
                raise ValidationError("Please enter your name as: surname, given names.")

    def validate_orcid(self, field: StringField) -> None:
        orcid = field.data
        # accept empty ORCID iDs
        if orcid is None:
            return
        orcid = orcid.strip()
        if not orcid:
            return
        # check ORCID iD syntax
        is_valid, orcid = validate_orcid(orcid)
        if not is_valid:
            raise ValidationError("Please enter a valid ORCID iD.")
        # keep sanitized ORCID iD on success
        field.data = orcid


class LoginForm(FlaskForm):
    username = StringField('Login', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=3)])
    submit = SubmitField('Login')


class AuthenticationForm(FlaskForm):
    login = StringField('Login')
    password = PasswordField('Password')
    description = StringField()
    fido2_passkey_credentials = HiddenField()
    authentication_method = RadioField('Authentication Method', choices=[('E', 'Email'), ('L', 'LDAP')], default='E')
    submit = SubmitField('Login')

    def validate(self, *args: typing.Any, **kwargs: typing.Any) -> bool:
        is_valid = bool(super().validate(*args, **kwargs))
        if not is_valid:
            return False
        if self.authentication_method.data in ('E', 'L'):
            if not self.login.data:
                is_valid = False
                self.login.errors.append(_('Please enter at least 1 character.'))
            if not self.password.data or len(self.password.data) < 3:
                is_valid = False
                self.password.errors.append(_('Please enter at least 3 characters.'))
        if self.authentication_method.data == 'FIDO2_PASSKEY':
            if not self.description.data:
                is_valid = False
                self.description.errors.append(_('Please enter at least 1 character.'))
        return is_valid


class AuthenticationMethodForm(FlaskForm):
    id = IntegerField('Authentication_method_id', validators=[DataRequired()])
    submit = SubmitField('Remove')
