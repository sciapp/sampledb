# coding: utf-8
"""

"""

from . import errors
from .. models import User


def get_user(user_id: int) -> User:
    user = User.query.get(user_id)
    if user is None:
        raise errors.UserDoesNotExistError()
    return user
