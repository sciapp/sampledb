# coding: utf-8
"""

"""

import flask
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import InputRequired, Email, Length, EqualTo, DataRequired, ValidationError


class SigninForm(FlaskForm):
    username = StringField(validators=[InputRequired()])
    password = PasswordField(validators=[InputRequired()])
    remember_me = BooleanField()


class SignoutForm(FlaskForm):
    pass


class InvitationForm(FlaskForm):
    email = StringField(validators=[InputRequired()])


class RequestPasswordResetForm(FlaskForm):
    email = StringField(validators=[InputRequired()])


class RegistrationForm(FlaskForm):
    email = StringField('Contact Email', validators=[
        InputRequired(message=_("Please enter your contact email.")),
        Email(message=_("Please enter your contact email."))
    ])
    name = StringField('Name', validators=[InputRequired()])
    password = PasswordField('New Password', validators=[
        InputRequired(),
        Length(min=3),
        EqualTo('password2', message=_('Passwords must match'))
    ])
    password2 = PasswordField('Confirm password', validators=[InputRequired()])
    submit = SubmitField('Register')

    def validate_name(self, field):
        if flask.current_app.config['ENFORCE_SPLIT_NAMES']:
            name = field.data
            if ', ' not in name[1:-1]:
                raise ValidationError(_("Please enter your name as: surname, given names."))


class PasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        InputRequired(),
        Length(min=3)
    ])
    submit = SubmitField('Change Password')


class AuthenticationPasswordForm(FlaskForm):
    id = IntegerField('Authentication_method_id', validators=[DataRequired()])
    password = PasswordField('New Password', validators=[
        InputRequired(),
        Length(min=3)
    ])
    password_confirmation = PasswordField(validators=[
        InputRequired(),
        Length(min=3),
        EqualTo('password')
    ])
    submit = SubmitField('Change Password')
