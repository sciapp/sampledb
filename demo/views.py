from demo import demo, db, ldap, models, mail, forms, bcrypt
from flask import render_template, redirect, request, url_for, request, flash
from demo.ldap import validate_user, get_user_info, get_gidNumber
from itsdangerous import URLSafeTimedSerializer, BadTimeSignature, BadData
from demo.token import generate_confirmation_token, confirm_token
from flask_mail import Mail, Message
from demo.email import send_mail
from sqlalchemy import or_, and_, Unicode, String
from sqlalchemy.sql.expression import cast
from .forms import RegisterForm
from .models import User
from .utils import validate_user_db
import re
s = URLSafeTimedSerializer('secret-key')
import sqlalchemy


@demo.route('/')
@demo.route('/index')
def index():
    return render_template('index.html')

@demo.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['username']
        log = {'login': login}
        pw = request.form['password']
        pw_hash = bcrypt.generate_password_hash(pw).decode('utf-8')
        print(login)
        print([(a.login['login']) for a in models.Authenticate.query.all()])
        print([a.name for a in models.User.query.all()])
        # filter email + pw or username + pw or username (ldap)
        user = models.Authenticate.query.filter(
            and_(models.Authenticate.login['login'].astext == login, models.Authenticate.logtype == 'email') | and_(
                models.Authenticate.login['login'].astext == login, models.Authenticate.logtype == 'other') | and_(
                models.Authenticate.login['login'].astext == login, models.Authenticate.logtype == 'ldap')).first()
        print(user)
        # no authentificaton method in db
        if user is None:
            # try to authenticate against ldap
            result = validate_user(login, pw)
            if not result:
                flash('authentication failed.', 'danger')
                return render_template('index.html')
            # if authenticate with ldap insert to db
            else:
                newuser = get_user_info(login)
                # look , if user in usertable without authentication metho
                erg = models.User.query.filter_by(name=str(newuser.name),email=str(newuser.email)).first()
                if erg is None:
                    u = models.User(str(newuser.name),str(newuser.email),str(newuser.usertype))
                    db.session.add(u)
                    db.session.commit()

                u_id = models.User.query.filter_by(name=newuser.name,email=newuser.email).first()
                if u_id is not None:
                    auth = models.Authenticate(log, 'ldap', u_id.id)
                    db.session.add(auth)
                    db.session.commit()

        else:
            # authentificaton method in db is ldap
            if (user.logtype == 'ldap'):
                result = validate_user(login, pw)
            else:
                result = validate_user_db(login,pw)
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
        #return render_template('activate.html',errors="Your link has been expired")
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

@demo.route('/send-mail/')
def send_mail1():
    msg = Message(
        'Send Mail tutorial!',
        sender='iffsamples@fz-juelich.de',
        recipients=['d.henkel@fz-juelich.de'],
        body = "Hello Flask message sent from Flask-Mail"
    )
    mail.send(msg)
    return "sent"
