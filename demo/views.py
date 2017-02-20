from demo import demo, db, lm, models, mail, bcrypt
from flask import render_template, redirect, request, url_for, request, flash, g
from flask_login import login_required, login_user, logout_user, current_user
from demo.ldap import validate_user, get_user_info, get_gidNumber
from itsdangerous import URLSafeTimedSerializer, BadTimeSignature, BadData
from demo.token import generate_confirmation_token, confirm_token
from demo.email import send_mail
from sqlalchemy import or_, and_
from .forms import RegisterForm
from .models import User, logintype
from .utils import validate_user_db
import re
s = URLSafeTimedSerializer('secret-key')

@demo.route('/')
@demo.route('/index')
def index():
    return render_template('index.html')

@lm.user_loader
def load_user(id):
    try:
        return User.query.get(int(id))
    except:
        return None

@demo.before_request
def before_request():
    g.user = current_user

@demo.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@demo.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('you are already logged in', 'danger')
        print('user exists')
        return redirect(url_for('index'))
    if request.method == 'POST':
        login = request.form['username']
        pw = request.form['password']
        # filter email + pw or username + pw or username (ldap)
        auth = models.Authenticate.query.filter(
            and_(models.Authenticate.login['login'].astext == login, models.Authenticate.logtype == 'email') | and_(
                models.Authenticate.login['login'].astext == login, models.Authenticate.logtype == 'other') | and_(
                models.Authenticate.login['login'].astext == login, models.Authenticate.logtype == 'ldap')).first()
        match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', login)
        # no authentificaton method in db
        if auth is None:
            if not match:
                # try to authenticate against ldap, if login is no email
                print('validate_user')
                result = validate_user(login, pw)
                if not result:
                    flash('authentication failed.', 'danger')
                    return render_template('index.html')
                    # if authenticate with ldap insert to db
                else:
                    newuser = get_user_info(login)
                    # look , if user in usertable without authentication method
                    erg = models.User.query.filter_by(name=str(newuser.name), email=str(newuser.email)).first()
                    # if not, add to table user
                    if erg is None:
                        u = models.User(str(newuser.name), str(newuser.email), str(newuser.usertype))
                        db.session.add(u)
                        db.session.commit()
                    # add authenticate method to table for user (old or new)
                    user = models.User.query.filter_by(name=str(newuser.name), email=str(newuser.email)).first()
                    if user is not None:
                        log = {'login': login}
                        authenticate = models.Authenticate(log, 'ldap', user.id)
                        db.session.add(authenticate)
                        db.session.commit()
                        login_user(user)
                    else:
                        flash('database error')
            else:
                print('invalid user or password')
                return render_template('index.html')
        else:
            # authentificaton method in db is ldap
            if (auth.logtype == logintype.ldap):
                result = validate_user(login, pw)
            else:
                result = validate_user_db(login,pw)
            if result:
                user = User.query.get(auth.user_id)
                login_user(user)
            else:
                result = validate_user_db(login, pw)
        # if result, user is authenticated
        if not result:
            print("user or password wrong, can't login")
        else:
            print("user is authenticated")
    return redirect(url_for('index'))

@demo.route('/invite_user', methods=['POST'])
def invite():
    if request.method == 'POST':
        mail = request.form['mail']
        token = generate_confirmation_token(mail)
        subject = "Please confirm your email"
        confirm_url = url_for("confirm_email", token=token, _external=True)
        html = render_template('activate.html', confirm_url=confirm_url)
        send_mail(mail, subject, html)
        return redirect(url_for('index'))

@demo.route('/confirm/<token>', methods=['GET', 'POST'])
def confirm_email(token):
    try:
         email_token = confirm_token(token)
         email = email_token[0]
    except:
        flash('The registration link is invalid or has expired.', 'danger')
        return render_template('index.html')
    form = RegisterForm()
    if form.validate_on_submit():
         match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email)
         if match == None:
            print('Bad Syntax')
         name = str(form.name.data)
         user = User(name,email,'person')
         erg = models.User.query.filter_by(name=str(user.name).title(), email=str(user.email)).first()
         # no user with this name and contact email in db => add to db
         if erg is None:
             u = models.User(str(user.name).title(), user.email, user.usertype)
             db.session.add(u)
             db.session.commit()
             # look for id to insert authentication method for it
             u_id = models.User.query.filter_by(name=str(user.name).title(), email=user.email).first()
             if u_id is not None:
                 pw_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
                 log = {'login': email,'password':pw_hash}
                 auth = models.Authenticate(log, 'email', u_id.id)
                 db.session.add(auth)
                 db.session.commit()
             flash('registration successfully')
             return redirect(url_for('index'))
         else:
             flash('user exists, please contact administrator')
             return redirect(url_for('index'))
    else:
        return render_template('register.html', form=form)