import bcrypt
import flask
import flask_login
import flask_mail

from flask import g
from . import utils
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
    if flask_login.current_user.is_authenticated:
        flask.flash('you are already logged in', 'danger')
        return flask.redirect(flask.url_for('main.index'))
    if flask.request.method == 'POST':
        login = flask.request.form['username']
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
                    return flask.render_template('index_old.html')
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
                        confirmed = True
                        authenticate = Authentication(log, AuthenticationType.LDAP, confirmed, user.id)
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
        return flask.render_template('index_old.html')
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
            result = utils.insert_user_and_authentication_method_to_db(u, form.password.data, email, AuthenticationType.EMAIL)
            if not result:
                flask.flash('registration failed, please contact administrator')
            else:
                flask.flash('registration successfully')
            return flask.redirect(flask.url_for('main.index'))
        else:
            flask.flash('user exists, please contact administrator')
            return flask.redirect(flask.url_for('main.index'))
    else:
        return flask.render_template('register.html', form=form)


@authentication.route('/confirm2/<token>', methods=['GET'])
def confirm2_email(token):
    data = verify_token(token, salt='edit_profile', secret_key=flask.current_app.config['SECRET_KEY'])
    if data is None:
        # TODO: Why flash?
        flask.flash('The confirmation link has expired.', 'danger')
        return flask.render_template('index_old.html')
    else:
        if(len(data)!=2):
            flask.flash('Error in confirmation email.', 'danger')
            return flask.render_template('index_old.html')
        email = data[0]
        id = data[1]
        if '@' not in email:
            # TODO: ???
            print('Bad Syntax')
        user = User.query.get(id)
        user.email = email
        db.session.add(user)
        db.session.commit()
        return flask.redirect(flask.url_for('main.index'))

@authentication.route('/confirm3/<token>', methods=['GET'])
def confirm3_email(token):
    data = verify_token(token, salt='add_login', secret_key=flask.current_app.config['SECRET_KEY'])
    if data is None:
        # TODO: Why flash?
        flask.flash('The confirmation link has expired.', 'danger')
        return flask.render_template('index.html')
    else:
        if (len(data) != 2):
            flask.flash('Error in confirmation email.', 'danger')
            return flask.render_template('index.html')
        email = data[0]
        id = data[1]
        if '@' not in email:
            # TODO: ???
            print('Bad Syntax')
        auth = Authentication.query.filter(Authentication.user_id == id, Authentication.login['login'].astext ==email).first()
        auth.confirmed = True
        db.session.add(auth)
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
           result = utils.insert_user_and_authentication_method_to_db(user, form.password.data, form.login.data, authentication_method)

           if not result:
               flask.flash('adding new user failed')
               return flask.redirect(flask.url_for('main.index'))

       else:
           flask.flash('user exists, please contact administrator')
           print('user already exists')
           return flask.redirect(flask.url_for('main.index'))
   return flask.render_template('user.html',form=form)


@authentication.route('/login/show_all', methods=['GET','POST'])
@flask_login.login_required
def show_login():
    user = flask_login.current_user
    authentication_methods = Authentication.query.filter(Authentication.user_id == user.id).all()
    for authentication_method in authentication_methods:
        print(authentication_method.type)
        print(authentication_method.login['login'])
    return flask.render_template('authentications.html', user=user, authentications=authentication_methods)


@authentication.route('/authentication/<userid>/remove/<id>', methods=['GET', 'POST'])
@flask_login.login_required
def delete_login(userid,id):
    if flask_login.current_user.is_authenticated:
        user = flask_login.current_user
        print('userid',userid)
        print('authentication_id',id)
        if(str(user.id) == userid):
            authentication_methods = Authentication.query.filter(Authentication.user_id == user.id).count()
            if (authentication_methods <= 1):
                print('one authentication-method must exist, delete not possible')
                flask.flash('one authentication-method must exist, delete not possible')
                return flask.redirect(flask.url_for('main.index'))
            else:
                authentication_methods = Authentication.query.filter(Authentication.id == id).first()
                db.session.delete(authentication_methods)
                db.session.commit()
                print('delete authentication-method')
    return flask.redirect(flask.url_for('main.index'))

@authentication.route('/authentication/add/<userid>', methods=['GET', 'POST'])
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
                print(form.login.data)
                print(form.authentication_method.data)
                if form.authentication_method.data == 'E':
                    authentication_method = AuthenticationType.EMAIL
                    #check if login looks like an email
                    if '@' not in form.login.data:
                        flask.flash('input error, login is not an email or the AuthenticationType is wrong')
                        print('input error')
                        flask.render_template('authentication_form.html', form=form)
                    else:
                        # add authentication-method to db and send confirmation email
                        confirmed = False
                        auth = Authentication(log, authentication_method, confirmed, user.id)
                        print('add to db')
                        db.session.add(auth)
                        db.session.commit()
                        # send confirm link
                        token = generate_token([form.login.data, user.id], salt='add_login',
                                               secret_key=flask.current_app.config['SECRET_KEY'])
                        subject = "Please confirm your email"
                        confirm_url = flask.url_for(".confirm3_email", token=token, _external=True)
                        html = flask.render_template('activate.html', confirm_url=confirm_url)
                        mail.send(flask_mail.Message(
                            subject,
                            sender=flask.current_app.config['MAIL_SENDER'],
                            recipients=[form.login.data],
                            html=html
                        ))
                        return flask.redirect(flask.url_for('main.index'))

                else:
                    if form.authentication_method.data == 'O':
                        authentication_method = AuthenticationType.OTHER
                        confirmed = True
                        auth = Authentication(log, authentication_method, confirmed, user.id)
                        db.session.add(auth)
                        db.session.commit()
                    else:
                        authentication_method = AuthenticationType.LDAP
                        result = validate_user(form.login.data, form.password.data)
                        confirmed = False
                        if(result):
                            confirmed = True
                            auth = Authentication(log, authentication_method, confirmed, user.id)
                            db.session.add(auth)
                            db.session.commit()
                        else:
                            print('error additional authentication-method wrong')
            else:
                print('authentication-method already exists')
                # was tun??????
#        else:
#            print(form.errors)
        return flask.render_template('authentication_form.html', form=form)
    else:
        print('error')
        return flask.redirect(flask.url_for('main.index'))

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
        # the name changes , keep the old contact email
        if (form.name.data != user.name):
            u = User(str(form.name.data), str(user.email), user.type)
            db.session.add(u)
            db.session.commit()
        # check, if contact email changes
        if(form.email.data != user.email):
            # send confirm link
            token = generate_token([form.email.data, user.id], salt='edit_profile', secret_key=flask.current_app.config['SECRET_KEY'])
            subject = "Please confirm your email"
            confirm_url = flask.url_for(".confirm2_email", token=token, _external=True)
            html = flask.render_template('activate.html', confirm_url=confirm_url)
            mail.send(flask_mail.Message(
                subject,
                sender=flask.current_app.config['MAIL_SENDER'],
                recipients=[form.email.data],
                html=html
            ))
        return flask.redirect(flask.url_for('main.index'))
    return flask.render_template('edit_user.html', form=form)
