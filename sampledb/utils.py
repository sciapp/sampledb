# coding: utf-8
"""

"""

import base64
import binascii
import functools

import flask
import flask_login

from sampledb import logic
from sampledb.logic.authentication import login
from sampledb.models import Permissions, Objects
from . import login_manager

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def admin_required(func):
    @flask_login.login_required
    @functools.wraps(func)
    def wrapper(**kwargs):
        user = flask_login.current_user
        if not user.is_admin:
            return flask.abort(403)
        return func(**kwargs)
    return wrapper


@login_manager.request_loader
def basic_auth_loader(request):
    auth_header = request.headers.get('Authorization', None)
    if not auth_header:
        return None
    if not auth_header.startswith('Basic '):
        return None
    try:
        auth_data = base64.b64decode(auth_header.replace('Basic ', '', 1), validate=True).decode('utf-8')
    except (TypeError, binascii.Error, UnicodeDecodeError):
        return None
    if ':' not in auth_data:
        return None
    username, password = auth_data.split(':', 1)
    # Prevent cookies?
    if login(username, password):
        return flask_login.current_user
    return None


def object_permissions_required(required_object_permissions: Permissions):
    # TODO: REST APIs should use HTTP basic auth instead of cookies, etc.
    def decorator(func):
        @flask_login.login_required
        @functools.wraps(func)
        def wrapper(**kwargs):
            assert 'object_id' in kwargs
            object_id = kwargs['object_id']
            if Objects.get_current_object(object_id) is None:
                return flask.abort(404)
            if not logic.permissions.object_is_public(object_id):
                user_id = flask_login.current_user.id
                user_object_permissions = logic.permissions.get_user_object_permissions(object_id=object_id, user_id=user_id)
                if required_object_permissions not in user_object_permissions:
                    # TODO: handle lack of permissions better
                    return flask.abort(403)
            return func(**kwargs)
        return wrapper
    return decorator
