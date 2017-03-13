# coding: utf-8
"""

"""

import flask

from sampledb.utils import object_permissions_required
from ..models import Permissions
from .. import logic
from . import rest_api

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@rest_api.route('/objects/<int:object_id>/permissions/')
@object_permissions_required(Permissions.READ)
def get_object_permissions(object_id):
    object_permissions = logic.permissions.get_object_permissions(object_id)
    return flask.jsonify({
         (str(user_id) if user_id is not None else 'all'): permissions.name.lower() for user_id, permissions in object_permissions.items()
    })


@rest_api.route('/objects/<int:object_id>/permissions/all')
@object_permissions_required(Permissions.READ)
def get_public_object_permissions(object_id):
    permissions = Permissions.NONE
    if logic.permissions.object_is_public(object_id):
        permissions = Permissions.READ
    return flask.jsonify(str(permissions))


@rest_api.route('/objects/<int:object_id>/permissions/<int:user_id>')
@object_permissions_required(Permissions.READ)
def get_user_object_permissions(object_id, user_id):
    permissions = logic.permissions.get_user_object_permissions(object_id=object_id, user_id=user_id)
    return flask.jsonify(str(permissions))


@rest_api.route('/objects/<int:object_id>/permissions/<int:user_id>', methods=['PUT'])
@object_permissions_required(Permissions.GRANT)
def set_user_object_permissions(object_id, user_id):
    if not flask.request.is_json:
        return flask.abort(400)
    try:
        permissions = Permissions.from_name(flask.request.json)
    except ValueError:
        return flask.abort(400)
    logic.permissions.set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=permissions)
    return flask.redirect(flask.url_for('.get_user_object_permissions', object_id=object_id, user_id=user_id))


@rest_api.route('/objects/<int:object_id>/permissions/all', methods=['PUT'])
@object_permissions_required(Permissions.GRANT)
def set_public_object_permissions(object_id):
    if not flask.request.is_json:
        return flask.abort(400)
    if flask.request.json not in ('none', 'read'):
        return flask.abort(400)
    should_be_public = (flask.request.json == 'read')
    logic.permissions.set_object_public(object_id, should_be_public)
    return flask.redirect(flask.url_for('.get_public_object_permissions', object_id=object_id))
