# coding: utf-8
"""

"""

import functools

import flask
import flask_login

from ..object_database.models import Objects
from .models import Permissions
from . import logic


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

# TODO: REST APIs should use HTTP basic auth instead of cookies, etc.


def object_permissions_required(required_object_permissions: Permissions):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(**kwargs):
            assert 'object_id' in kwargs
            object_id = kwargs['object_id']
            user = flask_login.current_user
            if Objects.get_current_object(object_id) is None:
                return flask.abort(404)
            if not logic.object_is_public(object_id):
                if user.is_active and user.is_authenticated:
                    user_id = flask_login.current_user.id
                    user_object_permissions = logic.get_user_object_permissions(object_id=object_id, user_id=user_id)
                    if required_object_permissions not in user_object_permissions:
                        # TODO: handle lack of permissions better
                        return flask.abort(403)
                else:
                    return flask_login.login_required(func)(**kwargs)
            return func(**kwargs)
        return wrapper
    return decorator
