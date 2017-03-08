# coding: utf-8
"""

"""

import flask

from ..object_database.models import Objects
from . import logic
from .models import Permissions
from .utils import object_permissions_required

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


permissions_api = flask.Blueprint('permissions_api', __name__)


@permissions_api.route('/<int:object_id>/permissions/')
@object_permissions_required(Permissions.READ)
def get_object_permissions(object_id):
    object_permissions = logic.get_object_permissions(object_id)
    return flask.jsonify({
         (str(user_id) if user_id is not None else 'all'): permissions.name.lower() for user_id, permissions in object_permissions.items()
    })


@permissions_api.route('/<int:object_id>/permissions/all')
@permissions_api.route('/<int:object_id>/permissions/<int:user_id>')
@object_permissions_required(Permissions.READ)
def get_user_object_permissions(object_id, user_id=None):
    permissions = logic.get_user_object_permissions(object_id=object_id, user_id=user_id)
    return flask.jsonify(str(permissions))


@permissions_api.route('/<int:object_id>/permissions/<int:user_id>', methods=['PUT'])
@object_permissions_required(Permissions.GRANT)
def set_user_object_permissions(object_id, user_id):
    if not flask.request.is_json:
        return flask.abort(400)
    try:
        permissions = Permissions.from_name(flask.request.json)
    except ValueError:
        return flask.abort(400)
    logic.set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=permissions)
    return flask.redirect(flask.url_for('permissions_api.get_user_object_permissions', object_id=object_id, user_id=user_id))


@permissions_api.route('/<int:object_id>/permissions/all', methods=['PUT'])
@object_permissions_required(Permissions.GRANT)
def set_public_object_permissions(object_id):
    if not flask.request.is_json:
        return flask.abort(400)
    if flask.request.json not in ('none', 'read'):
        return flask.abort(400)
    should_be_public = (flask.request.json == 'read')
    logic.set_object_public(object_id, should_be_public)
    return flask.redirect(flask.url_for('permissions_api.get_user_object_permissions', object_id=object_id))
