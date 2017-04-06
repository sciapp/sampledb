import bcrypt
import flask
import flask_login
import flask_mail

from .authentication_forms import RegisterForm, NewUserForm, ChangeUserForm, LoginForm, AuthenticationForm
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


@frontend.route('/invite_user', methods=['POST'])
def invite():
    email = flask.request.form['mail']
    # send confirm link
    logic.utils.send_confirm_email(email, None, 'invitation')
    return flask.redirect(flask.url_for('frontend.index'))


@frontend.route('/confirm', methods=['GET', 'POST'])
def confirm_registration():
    token = flask.request.args.get('token')
    email = verify_token(token, salt='invitation', secret_key=flask.current_app.config['SECRET_KEY'])
    if email is None:
        return flask.abort(404)
    form = RegisterForm()
    if form.validate_on_submit():
        name = str(form.name.data)
        user = User(name, email, UserType.PERSON)
        # check, if user sent confirmation email and registered himself
        erg = User.query.filter_by(name=str(user.name).title(), email=str(user.email)).first()
        # no user with this name and contact email in db => add to db
        if erg is None:
            u = User(str(user.name).title(), user.email, user.type)
            insert_user_and_authentication_method_to_db(u, form.password.data, email, AuthenticationType.EMAIL)
            flask.flash('registration successfully')
            return flask.redirect(flask.url_for('frontend.index'))
        else:
            flask.flash('user exists, please contact administrator')
            return flask.redirect(flask.url_for('frontend.index'))
    else:
        return flask.render_template('register.html', form=form)


@frontend.route('/confirm-email', methods=['GET'])
def confirm_email():
    salt = flask.request.args.get('salt')
    token = flask.request.args.get('token')
    data = verify_token(token, salt=salt, secret_key=flask.current_app.config['SECRET_KEY'])
    if data is None:
        return flask.abort(404)
    else:
        if len(data) != 2:
            return flask.abort(400)
        email = data[0]
        id = data[1]
        if salt == 'edit_profile':
            user = User.query.get(id)
            user.email = email
            db.session.add(user)
        elif salt == 'add_login':
            auth = Authentication.query.filter(Authentication.user_id == id,
                                               Authentication.login['login'].astext == email).first()
            auth.confirmed = True
            db.session.add(auth)
        else:
            return flask.abort(400)
        db.session.commit()
        return flask.redirect(flask.url_for('frontend.index'))


@frontend.route('/add_user', methods=['GET', 'POST'])
def useradd():
    form = NewUserForm()
    print('xxxxxxxx')
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





