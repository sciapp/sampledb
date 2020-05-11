# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import InputRequired, Email, Length, EqualTo, DataRequired


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
    email = StringField('Contact Email', validators=[InputRequired("Please enter the contact email."),
                                                     Email("Please enter your contact email.")])
    name = StringField('Name', validators=[InputRequired()])
    password = PasswordField('New Password', validators=[
        InputRequired(),
        Length(min=3),
        EqualTo('password2', message='Passwords must match')
    ])
    password2 = PasswordField('Confirm password', validators=[InputRequired()])
    submit = SubmitField('Register')


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
