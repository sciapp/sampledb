from demo import demo, db, models, bcrypt, lm
from flask import flash
from flask_login import login_user
from .models import User
import json

from demo.models import User, usertyps


def validate_user_db(login, password):
    try:
        print('validate_db')
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
               print(password)
               erg = bcrypt.check_password_hash(person.login['password'], password)
               print(erg)
               if erg:
                  user = User.query.get(person.user_id)
                  print("user")
                  print(user)
                  login_user(user)
                  return True
               else:
                   return False
            else:
                for person in users:
                    user = models.User.query.filter(models.User.id == person.user_id).first()
                    print(person.login)
                    print(password)
                    erg = bcrypt.check_password_hash(person.login['password'], password)
                    print(erg)
                    if erg:
                        print('in erg')
                        user = User.query.get(user.id)
                        print(user)
                        login_user(user)
                        return True
                    else:
                        print('fehler')
                        return False
            if not erg:
                print('authentification failed')
                return False
            else:
                flash('authentification successfully')
                return True
    except:
        return False
