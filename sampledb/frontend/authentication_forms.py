# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import StringField, RadioField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, Email


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
    submit = SubmitField('Change Settings')

    def __init_(self, name=None, email=None):
        super(ChangeUserForm, self).__init__()


class LoginForm(FlaskForm):
    username = StringField('Login', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=3)])
    submit = SubmitField('Login')


class AuthenticationForm(FlaskForm):
    login = StringField('Login', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=3)])
    authentication_method = RadioField('Authentication Method', choices=[('E', 'Email'), ('L', 'LDAP')], default='E')
    submit = SubmitField('Login')


class AuthenticationMethodForm(FlaskForm):
    id = IntegerField('Authentication_method_id', validators=[DataRequired()])
    submit = SubmitField('Remove')
