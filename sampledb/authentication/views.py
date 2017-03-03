import bcrypt
import flask
import flask_login
import flask_mail

from flask import g
from . import utils
from .ldap import validate_user, get_user_info
from .models import AuthenticationType, Authentication, UserType, User
from .forms import RegisterForm, NewUserForm, ChangeUserForm, LoginForm
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
    print('login')
    if flask_login.current_user.is_authenticated:
        flask.flash('you are already logged in', 'danger')
        print('user exists')
        return flask.redirect(flask.url_for('main.index'))
    if flask.request.method == 'POST':
        login = flask.request.form['username']
        print(login)
        password = flask.request.form['password']
        # filter email + password or username + password or username (ldap)
        authentication_methods = Authentication.query.filter(
            db.or_(
                db.and_(Authentication.login['login'].astext == login, Authentication.type == AuthenticationType.EMAIL),
                db.and_(Authentication.login['login'].astext == login, Authentication.type == AuthenticationType.LDAP),
                db.and_(Authentication.login['login'].astext == login, Authentication.type == AuthenticationType.OTHER)
            )
        ).all()

        result = False
        for authentication_method in authentication_methods:
            # authentificaton method in db is ldap
            if authentication_method.type == AuthenticationType.LDAP:
                print('ldap in db')
                result = validate_user(login, password)
            else:
                result = utils.validate_user_db(login, password)
            if result:
                user = authentication_method.user
                flask_login.login_user(user)
                break

        # no authentificaton method in db
        if not authentication_methods:
            if '@' not in login:
                # try to authenticate against ldap, if login is no email
                result = validate_user(login, password)
                if not result:
                    flask.flash('authentication failed.', 'danger')
                    return flask.render_template('index.html')
                    # if authenticate with ldap insert to db
                else:
                    newuser = get_user_info(login)
                    # TODO: mehrer user können gleiche mail haben, aber nur einen login
                    # ein user kann mehrere logins haben (experiment-account, normaler account z.B. henkel und lido)
                    # look , if user in usertable without authentication method or other authentication method
                    erg = User.query.filter_by(name=str(newuser.name), email=str(newuser.email)).first()
                    # if not, add user to table
                    if erg is None:
                        u = User(str(newuser.name), str(newuser.email), newuser.type)
                        db.session.add(u)
                        db.session.commit()
                    # add authenticate method to table for user (old or new)
                    user = User.query.filter_by(name=str(newuser.name), email=str(newuser.email)).first()
                    if user is not None:
                        log = {'login': login}
                        authenticate = Authentication(log, AuthenticationType.LDAP, user.id)
                        db.session.add(authenticate)
                        db.session.commit()
                        flask_login.login_user(user)
                    else:
                        flask.flash('database error')
            else:
                print('invalid user or password')
                return flask.render_template('login.html')
        # TODO: ???
        # if result, user is authenticated
        if not result:
            flask.flash('xxx')
            print("user or password wrong, can't login")
        else:
            print("user is authenticated")
#    return flask.redirect(flask.url_for('main.index'))
    form = LoginForm()
    return flask.render_template('login.html',form=form)


@authentication.route('/invite_user', methods=['POST'])
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
    return flask.redirect(flask.url_for('main.index'))


@authentication.route('/confirm/<token>', methods=['GET', 'POST'])
def confirm_email(token):
    email = verify_token(token, salt='invitation', secret_key=flask.current_app.config['SECRET_KEY'])
    if email is None:
        # TODO: Why flash?
        flask.flash('The registration link has expired.', 'danger')
        return flask.render_template('index.html')
    form = RegisterForm()
    if form.validate_on_submit():
        if '@' not in email:
            # TODO: ???
            print('Bad Syntax')
        name = str(form.name.data)
        user = User(name, email, UserType.PERSON)
        # check, if user sent confirmation email and registered himself
        erg = User.query.filter_by(name=str(user.name).title(), email=str(user.email)).first()
        # no user with this name and contact email in db => add to db
        if erg is None:
            u = User(str(user.name).title(), user.email, user.type)
            result = utils.insert_user_and_authentication_method_to_db(u, form.password.data, email,AuthenticationType.EMAIL)
            if not result:
                flask.flash('registration failed, please contact administrator')
            else:
                flask.flash('registration successfully')
            return flask.redirect(flask.url_for('main.index'))
        else:
            print('user exists')
            flask.flash('user exists, please contact administrator')
            return flask.redirect(flask.url_for('main.index'))
    else:
        return flask.render_template('register.html', form=form)

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
               result = utils.insert_user_and_authentication_method_to_db(user, form.password.data, form.login.data,
                                                                          AuthenticationType.EMAIL)
           else:
               result = utils.insert_user_and_authentication_method_to_db(user, form.password.data, form.login.data,
                                                                          AuthenticationType.OTHER)
           if not result:
               flask.flash('adding new user failed')
               return flask.redirect(flask.url_for('main.index'))

       else:
           flask.flash('user exists, please contact administrator')
           print('user already exists')
           return flask.redirect(flask.url_for('main.index'))
#   else:
#       print(form.errors)
   return flask.render_template('user.html',form=form)

@authentication.route('/edit_user', methods=['GET', 'POST'])
@flask_login.login_required
def useredit():
   user = flask_login.current_user
   print(user.id)
   login = Authentication.query.filter(Authentication.user_id == user.id).first()
   user.login = login.login['login']
   user.authentification_method = login.type
   print(login.type)
   form = ChangeUserForm( obj=user)
   if form.authentication_method.data is None:
       form.authentication_method.data = login.type
   if form.validate_on_submit():
       # check, if login  exists
       login = Authentication.query.filter(Authentication.login['login'].astext == form.login.data).first()
       if login is None:
           flask.flash("user doesn't exists, please contact administrator")
           return False
       else:
           if(form.type.data=='O'):
               type = UserType.OTHER
           else:
               type = UserType.PERSON
           user = User(str(form.name.data).title(),str(form.email.data),type)
           if form.authentication_method.data == 'E':
               result = utils.insert_user_and_authentication_method_to_db(user, form.password.data, form.login.data,
                                                                          AuthenticationType.EMAIL)
           else:
               result = utils.insert_user_and_authentication_method_to_db(user, form.password.data, form.login.data,
                                                                          AuthenticationType.OTHER)
           if not result:
               flask.flash('changing user failed')
           else:
               flask.flash('changing user successfully')
       return flask.redirect(flask.url_for('main.index'))
   else:
       print(form.errors)
   return flask.render_template('edit_user.html', form=form, AuthenticationType=AuthenticationType)