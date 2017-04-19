# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import InputRequired, Email, Length, EqualTo


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


class EmailPasswordForm(FlaskForm):
    email = StringField(validators=[InputRequired()])
    username = StringField(validators=[InputRequired()])
    password = PasswordField('New Password', validators=[
        InputRequired(),
        Length(min=3),
        EqualTo('password2', message='Passwords must match')
    ])
    password2 = PasswordField('Confirm password', validators=[InputRequired()])
    submit = SubmitField('Change Password')


class LoginPasswordForm(FlaskForm):
    login = StringField(validators=[InputRequired()])
    username = StringField(validators=[InputRequired()])
    password = PasswordField('New Password', validators=[
        InputRequired(),
        Length(min=3),
        EqualTo('password2', message='Passwords must match')
    ])
    password2 = PasswordField('Confirm password', validators=[InputRequired()])
    submit = SubmitField('Change Password')