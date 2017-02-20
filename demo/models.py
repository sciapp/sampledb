from sqlalchemy import *
from demo import db
from sqlalchemy.orm import relationship
import sqlalchemy.dialects.postgresql as postgresql
from flask_login import UserMixin



import enum
class usertyps(enum.Enum):
    person = 'single person'
    group  = 'project group'
    instrument = 'instrument'

class logintype(enum.Enum):
    ldap = "ldap authentification"
    email = "email authentification against DB"
    other = "username and passwort against DB"


class User(db.Model,UserMixin):
    __tablename__='users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    usertype = db.Column(db.Enum(usertyps), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    auth_method = relationship('Authenticate', backref="User")


    def __init__(self, name, email, usertype):
        self.name = name
        self.email = email
        self.usertype = usertype

    def get_id(self):
        return self.id

    def __repr__(self):
        return '<User %r>' % (self.name)


class Authenticate(db.Model):
    __tablename__="authenticate"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'))
    login = db.Column(postgresql.JSONB)
    logtype = db.Column(db.Enum(logintype))

    def __init__(self, login, logtype, user_id):
        self.login = login
        self.logtype = logtype
        self.user_id = user_id

    @property
    def get_login(self):
        return self.login

    @property
    def get_logtype(self):
        return self.logtype


    def __repr__(self):
        return '<ID %s>' % (self.id)
