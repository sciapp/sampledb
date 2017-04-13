import bcrypt
import flask
import flask_login
import flask_mail

from .authentication_forms import  NewUserForm, ChangeUserForm, LoginForm, AuthenticationForm
from .users_forms import  RegistrationForm
from .. import logic
from sampledb.logic.authentication import insert_user_and_authentication_method_to_db
from ..logic.security_tokens import  verify_token
from .. import mail, db, login_manager
from ..models import AuthenticationType, Authentication, UserType, User

from . import frontend


@login_manager.user_loader
def load_user(user_id):
    try:
        user_id = int(user_id)
    except ValueError:
        return None
    return User.query.get(user_id)


@frontend.route('/add_user', methods=['GET', 'POST'])
def useradd():
    form = NewUserForm()
    if form.validate_on_submit():
        print('validate')
        # check, if login already exists
        login = Authentication.query.filter(Authentication.login['login'].astext == form.login.data).first()
        print(login)
        if login is None:
            if (form.type.data == 'O'):
                type = UserType.OTHER
            else:
                type = UserType.PERSON
            user = User(str(form.name.data).title(), str(form.email.data), type)
            if form.authentication_method.data == 'E':
                authentication_method = AuthenticationType.EMAIL
            else:
                authentication_method = AuthenticationType.OTHER
            insert_user_and_authentication_method_to_db(user, form.password.data, form.login.data,
                                                        authentication_method)
        else:
            flask.flash('user exists, please contact administrator')
            return flask.redirect(flask.url_for('frontend.index'))
    return flask.render_template('user.html', form=form)





