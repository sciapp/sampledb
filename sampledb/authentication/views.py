import bcrypt
import flask
import flask_login
import flask_mail

from . import logic
from .ldap import validate_user, get_user_info
from .models import AuthenticationType, Authentication, UserType, User
from .forms import RegisterForm, NewUserForm, ChangeUserForm, LoginForm, AuthenticationForm
from .. import mail, db, login_manager
from ..security_tokens import generate_token, verify_token

authentication = flask.Blueprint('authentication', __name__, template_folder='templates')
login_manager.login_view = 'authentication.login'



@login_manager.user_loader
def load_user(user_id):
    try:
        user_id = int(user_id)
    except ValueError:
        return None
    return User.query.get(user_id)


@authentication.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for('main.index'))


@authentication.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm
    if flask_login.current_user.is_authenticated:
        flask.flash('you are already logged in', 'danger')
        return flask.redirect(flask.url_for('main.index'))
    if flask.request.method == 'POST':
        login = flask.request.form['username']
        password = flask.request.form['password']
        if not logic.login(login,password):
            flask.abort(401)
        else:
            flask.flash('login is successfully')
            return flask.redirect(flask.url_for('main.index'))

    return flask.render_template('login.html',form=form)


@authentication.route('/invite_user', methods=['POST'])
def invite():
    email = flask.request.form['mail']
    # send confirm link
    logic.send_confirm_email(email, None, 'invitation')
    return flask.redirect(flask.url_for('main.index'))

@authentication.route('/confirm', methods=['GET', 'POST'])
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
            logic.insert_user_and_authentication_method_to_db(u, form.password.data, email,AuthenticationType.EMAIL)
            flask.flash('registration successfully')
            return flask.redirect(flask.url_for('main.index'))
        else:
            flask.flash('user exists, please contact administrator')
            return flask.redirect(flask.url_for('main.index'))
    else:
        return flask.render_template('register.html', form=form)


@authentication.route('/confirm-email', methods=['GET'])
def confirm_email():
    salt = flask.request.args.get('salt')
    token = flask.request.args.get('token')
    data = verify_token(token, salt=salt, secret_key=flask.current_app.config['SECRET_KEY'])
    if data is None:
        if(len(data)!=2):
            flask.flash('Error in confirmation email.', 'danger')
            return flask.render_template('index_old.html')
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
        return flask.redirect(flask.url_for('main.index'))


@authentication.route('/add_user', methods=['GET', 'POST'])
def useradd():
   form = NewUserForm()
   if form.validate_on_submit():
       # check, if login already exists
       login = Authentication.query.filter(Authentication.login['login'].astext == form.login.data).first()
       if login is None:
           if(form.type.data=='O'):
               type = UserType.OTHER
           else:
               type = UserType.PERSON
           user = User(str(form.name.data).title(),str(form.email.data),type)
           if form.authentication_method.data == 'E':
               authentication_method = AuthenticationType.EMAIL
           else:
               authentication_method = AuthenticationType.OTHER
           logic.insert_user_and_authentication_method_to_db(user, form.password.data, form.login.data, authentication_method)

       else:
           flask.flash('user exists, please contact administrator')
           return flask.redirect(flask.url_for('main.index'))
   return flask.render_template('user.html',form=form)


@authentication.route('/login/show_all', methods=['GET','POST'])
@flask_login.login_required
def show_login():
    user = flask_login.current_user
    authentication_methods = Authentication.query.filter(Authentication.user_id == user.id).all()
    return flask.render_template('authentications.html', user=user, authentications=authentication_methods)


@authentication.route('/authentication/<userid>/remove/<id>', methods=['GET', 'POST'])
@flask_login.login_required
def delete_login(userid,id):
    if flask_login.current_user.is_authenticated:
        user = flask_login.current_user
        if str(user.id) == userid:
            authentication_methods = Authentication.query.filter(Authentication.user_id == user.id).count()
            if authentication_methods <= 1:
                flask.flash('one authentication-method must exist, delete not possible')
                return flask.redirect(flask.url_for('main.index'))
            else:
                authentication_methods = Authentication.query.filter(Authentication.id == id).first()
                db.session.delete(authentication_methods)
                db.session.commit()
    return flask.redirect(flask.url_for('main.index'))

@authentication.route('/authentication/add/<int:userid>', methods=['GET', 'POST'])
@flask_login.login_required
def add_login(userid):
    user = flask_login.current_user
    if user.id == userid:
        form = AuthenticationForm()
        if form.validate_on_submit():
            # check, if login already exists
            authentication_methods = {
                'E': AuthenticationType.EMAIL,
                'L': AuthenticationType.LDAP,
                'O': AuthenticationType.OTHER
            }
            if form.authentication_method.data not in authentication_methods:
                return flask.abort(400)
            authentication_method = authentication_methods[form.authentication_method.data]

            if not logic.add_login(userid, form.login.data, form.password.data, authentication_method):
                return flask.abort(400)

        return flask.render_template('authentication_form.html', form=form)
    else:
        return flask.abort(400)

@authentication.route('/edit_profile', methods=['GET', 'POST'])
@flask_login.login_required
def editprofile():
    user = flask_login.current_user
    form = ChangeUserForm()
    if form.name.data is None:
        form.name.data = user.name
    if form.email.data is None:
        form.email.data = user.email
    if form.validate_on_submit():
        if (form.name.data != user.name):
            u = user
            u.name = str(form.name.data)
            db.session.add(u)
            db.session.commit()
        if(form.email.data != user.email):
            # send confirm link
            logic.send_confirm_email(form.email.data, user.id, 'edit_profile')
        return flask.redirect(flask.url_for('main.index'))
    return flask.render_template('edit_user.html', form=form)
