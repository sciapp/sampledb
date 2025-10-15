# coding: utf-8
"""

"""

from http import HTTPStatus
import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import Email, Length, InputRequired, ValidationError, EqualTo

from .. import frontend
from ...logic import users, authentication
from ...utils import FlaskResponseT
from ...models import UserType


class CreateOtherUserForm(FlaskForm):
    name = StringField(validators=[InputRequired()])
    email = StringField(validators=[Email()])
    password = PasswordField(validators=[Length(min=3)])
    password_confirmation = PasswordField(validators=[EqualTo('password', message='Please enter the same password as above.')])

    def validate_name(form, field: StringField) -> None:
        if len(field.data) < 1:
            raise ValidationError(_('Please enter a valid user name.'))
        if not all(c in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in field.data):
            raise ValidationError(_('The name may only contain lower case characters, digits and underscores.'))
        if not authentication.is_login_available(field.data):
            raise ValidationError(_('This name is already being used.'))

    def validate_password(self, field: PasswordField) -> None:
        if field.data and len(field.data.encode('utf-8')) > authentication.MAX_BCRYPT_PASSWORD_LENGTH:
            raise ValidationError(_('The password must be at most %(max_bcrypt_password_length)s bytes long.', max_bcrypt_password_length=authentication.MAX_BCRYPT_PASSWORD_LENGTH))


@frontend.route('/users/create_other_user', methods=['GET', 'POST'])
@flask_login.login_required
def create_other_user() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(HTTPStatus.UNAUTHORIZED)
    create_other_user_form = CreateOtherUserForm()
    if create_other_user_form.validate_on_submit():
        user = users.create_user(
            name=create_other_user_form.name.data,
            email=create_other_user_form.email.data,
            type=UserType.OTHER
        )
        authentication.add_other_authentication(
            user_id=user.id,
            name=create_other_user_form.name.data,
            password=create_other_user_form.password.data
        )
        flask.flash(_('The user has been created successfully.'), 'success')
        return flask.redirect(flask.url_for('.user_profile', user_id=user.id))
    return flask.render_template(
        'create_other_user.html',
        create_other_user_form=create_other_user_form
    )
