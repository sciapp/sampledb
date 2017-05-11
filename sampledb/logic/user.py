import flask

from .. import logic, db
from .. models import User


def get_user(user_id):
    if user_id is None:
        return None
    if user_id <= 0:
        return None
    user = User.query.get(user_id)
    return user