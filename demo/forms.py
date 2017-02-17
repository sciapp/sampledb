from flask_wtf import FlaskForm
from wtforms import Field, StringField, PasswordField, SubmitField

from wtforms import ValidationError
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp


class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    password = PasswordField('New Password', validators=[
        Regexp(r'[A-Za-z0-9@#$%^&+=]',
               message='Password contains invalid characters'),
        DataRequired(), Length(min=3), EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Register')

