from demo import demo, db, models, bcrypt
from flask import flash
from .models import User
import json

from demo.models import User, usertyps


def validate_user_db(login, password):
    try:
        print(login)
        users = models.Authenticate.query.filter(models.Authenticate.login['login'].astext == login).all()
        print(users)
        if users is None:
            print('invalid authentification')
            return False
        else:
            if len(users) == 1:
               person = models.Authenticate.query.filter(models.Authenticate.login['login'].astext == login).first()
               print(person.login['login'])
               erg = bcrypt.check_password_hash(person.login['password'], password)
            else:
                for person in users:
                    user = models.User.query.filter(models.User.id == person.user_id).first()
                    erg = bcrypt.check_password_hash(person.login['password'], password)
                    if erg:
                        return True
            if not erg:
                print('authentification failed')
                return False
            else:
                flash('authentification successfully')
                return True
    except:
        return False
