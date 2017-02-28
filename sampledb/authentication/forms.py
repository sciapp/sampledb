from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, RadioField

from wtforms.validators import DataRequired, EqualTo, Length, Email


class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=3),
        EqualTo('password2', message='Passwords must match')
    ])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Register')


class NewUserForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Contact Email', validators=[DataRequired("Please enter the contact email."),
                                            Email("Please enter your contact email.")])
    password = PasswordField('Password', validators=[DataRequired(),Length(min=3)])
    authenticationmethod = RadioField('method', choices=[('E','Email'),('O','Other')])
    login = StringField('Login', validators=[DataRequired()])
    type = RadioField('usertype', choices=[('P','Person'),('O','Other')])
#    admin = RadioField('admin', choices=['0', '1'])
    submit = SubmitField('Register')
