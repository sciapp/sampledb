import bcrypt
import flask
import flask_login
import flask_mail

from .authentication_forms import RegisterForm, NewUserForm, ChangeUserForm, LoginForm, AuthenticationForm
from .. import logic
from ..logic.ldap import validate_user
from ..logic.security_tokens import generate_token, verify_token
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


@frontend.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for('frontend.index'))


@frontend.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm
    if flask_login.current_user.is_authenticated:
        flask.flash('you are already logged in', 'danger')
        return flask.redirect(flask.url_for('frontend.index'))
    if flask.request.method == 'POST':
        login = flask.request.form['username']
        password = flask.request.form['password']
        result = logic.authentication.login(login, password)
        print('result', result)
        if not result:
            flask.abort(401)
        else:
            flask.flash('login is successfully')
            return flask.redirect(flask.url_for('frontend.index'))

    return flask.render_template('login.html', form=form)


@frontend.route('/invite_user', methods=['POST'])
def invite():
    email = flask.request.form['mail']
    token = generate_token(email, salt='invitation', secret_key=flask.current_app.config['SECRET_KEY'])
    subject = "Please confirm your email"
    confirm_url = flask.url_for(".confirm_email", token=token, _external=True)
    html = flask.render_template('activate.html', confirm_url=confirm_url)
    mail.send(flask_mail.Message(
        subject,
        sender=flask.current_app.config['MAIL_SENDER'],
        recipients=[email],
        html=html
    ))
    return flask.redirect(flask.url_for('frontend.index'))


@frontend.route('/confirm/<token>', methods=['GET', 'POST'])
def confirm_email(token):
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
            result = logic.authentication.insert_user_and_authentication_method_to_db(u, form.password.data, email, AuthenticationType.EMAIL)
            if not result:
                return flask.abort(400)
            else:
                flask.flash('registration successfully')
                return flask.redirect(flask.url_for('frontend.index'))
        else:
            flask.flash('user exists, please contact administrator')
            return flask.redirect(flask.url_for('frontend.index'))
    else:
        return flask.render_template('register.html', form=form)


@frontend.route('/confirm-email/<token>/<salt>', methods=['GET'])
def confirm_email_without_form(token, salt):
    data = verify_token(token, salt=salt, secret_key=flask.current_app.config['SECRET_KEY'])
    if data is None:
        if(len(data)!=2):
            flask.flash('Error in confirmation email.', 'danger')
            return flask.render_template('index_old.html')
        return flask.abort(404)
    else:
        if(len(data)!=2):
            return flask.abort(400)
        email = data[0]
        id    = data[1]
        if(salt=='edit_profile'):
            user = User.query.get(id)
            user.email = email
            db.session.add(user)
        else:
            auth = Authentication.query.filter(Authentication.user_id == id,
                                               Authentication.login['login'].astext == email).first()
            auth.confirmed = True
            db.session.add(auth)
        db.session.commit()
        return flask.redirect(flask.url_for('frontend.index'))


@frontend.route('/add_user', methods=['GET', 'POST'])
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
           result = logic.authentication.insert_user_and_authentication_method_to_db(user, form.password.data, form.login.data, authentication_method)

           if not result:
               return flask.abort(400)
       else:
           flask.flash('user exists, please contact administrator')
           return flask.redirect(flask.url_for('frontend.index'))
   return flask.render_template('user.html', form=form)


@frontend.route('/login/show_all', methods=['GET','POST'])
@flask_login.login_required
def show_login():
    user = flask_login.current_user
    authentication_methods = Authentication.query.filter(Authentication.user_id == user.id).all()
    return flask.render_template('authentications.html', user=user, authentications=authentication_methods)


@frontend.route('/authentication/<userid>/remove/<id>', methods=['GET', 'POST'])
@flask_login.login_required
def delete_login(userid,id):
    if flask_login.current_user.is_authenticated:
        user = flask_login.current_user
        if(str(user.id) == userid):
            authentication_methods = Authentication.query.filter(Authentication.user_id == user.id).count()
            if (authentication_methods <= 1):
                print('one authentication-method must exist, delete not possible')
                flask.flash('one authentication-method must exist, delete not possible')
                return flask.redirect(flask.url_for('frontend.index'))
            else:
                authentication_methods = Authentication.query.filter(Authentication.id == id).first()
                db.session.delete(authentication_methods)
                db.session.commit()
    return flask.redirect(flask.url_for('frontend.index'))

@frontend.route('/authentication/add/<userid>', methods=['GET', 'POST'])
@flask_login.login_required
def add_login(userid):
    user = flask_login.current_user
    if(str(user.id) == userid):
        form = AuthenticationForm()
        if form.validate_on_submit():
            # check, if login already exists
            login = Authentication.query.filter(Authentication.login['login'].astext == form.login.data, Authentication.user_id == userid).first()
            if login is None:
                pw_hash = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                log = {
                    'login': form.login.data,
                    'bcrypt_hash': pw_hash
                }
                if form.authentication_method.data == 'E':
                    authentication_method = AuthenticationType.EMAIL
                    #check if login looks like an email
                    if '@' not in form.login.data:
                        return flask.abort(400)
                    else:
                        # add authentication-method to db and send confirmation email
                        logic.authentication.add_authentication_to_db(log, authentication_method, False, user.id)

                        # send confirm link
                        logic.utils.send_confirm_email(form.login.data, user.id, 'add_login')
                        return flask.redirect(flask.url_for('frontend.index'))

                else:
                    if form.authentication_method.data == 'O':
                        logic.authentication.add_authentication_to_db(log, AuthenticationType.OTHER, True, user.id)

                    else:
                        result = validate_user(form.login.data, form.password.data)
                        if(result):
                            logic.authentication.add_authentication_to_db(log, AuthenticationType.LDAP, True, user.id)
                        else:
                            return flask.abort(400)
            else:
                # authentication-method already exists
                return flask.abort(400)
        return flask.render_template('authentication_form.html', form=form)
    else:
        return flask.abort(400)

@frontend.route('/edit_profile', methods=['GET', 'POST'])
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
            logic.utils.send_confirm_email(form.email.data, user.id, 'edit_profile')
        return flask.redirect(flask.url_for('frontend.index'))
    return flask.render_template('edit_user.html', form=form)
