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


def http_auth_required(func):
    func = flask_login.login_required(func)

    @functools.wraps(func)
    def wrapper(**kwargs):
        auth_header = flask.request.headers.get('Authorization', None)
        if not auth_header:
            return flask.abort(401)
        if not auth_header.startswith('Basic '):
            return flask.abort(401)
        try:
            auth_data = base64.b64decode(auth_header.replace('Basic ', '', 1), validate=True).decode('utf-8')
        except (TypeError, binascii.Error, UnicodeDecodeError):
            return flask.abort(401)
        if ':' not in auth_data:
            return flask.abort(401)
        username, password = auth_data.split(':', 1)
        user = login(username, password)
        if user is None:
            return flask.abort(401)
        flask_login.login_user(user, remember=False)
        if not flask_login.current_user.is_authenticated or not flask_login.current_user.is_active:
            return flask.abort(401)
        return func(**kwargs)
    return wrapper


def object_permissions_required(required_object_permissions: Permissions):
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
