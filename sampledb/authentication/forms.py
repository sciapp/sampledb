from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, RadioField, HiddenField

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
    authentication_method = RadioField('Authentication Method', choices=[('E','Email'),('O','Other')], default='O')
    login = StringField('Login', validators=[DataRequired()])
    type = RadioField('Usertype', choices=[('P','Person'),('O','Other')], default='O')
    admin = RadioField('Admin', choices=[('0','No'),('1','Yes')], default='0')
    submit = SubmitField('Register')

class ChangeUserForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Contact Email', validators=[DataRequired("Please enter the contact email."),
                                            Email("Please enter your contact email.")])
    submit = SubmitField('Change Settings')

    def __init_(self, name=None, email=None):
        super(ChangeUserForm,self).__init__()


class LoginForm(FlaskForm):
    username = StringField('Login', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=3)])
    submit = SubmitField('Login')

class ConfirmForm(FlaskForm):
    uid = HiddenField('ID')
    submit = SubmitField('Confirm')
