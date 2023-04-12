# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from ..utils import FlaskResponseT
from ..logic.action_permissions import get_actions_with_permissions
from ..models.permissions import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/')
def index() -> FlaskResponseT:
    action_type_ids_with_usable_actions = set()
    if flask_login.current_user.is_authenticated and not flask_login.current_user.is_readonly:
        actions = get_actions_with_permissions(flask_login.current_user.id, permissions=Permissions.READ)
        for action in actions:
            if action.type is None:
                continue
            if action.admin_only and not flask_login.current_user.is_admin:
                continue
            if action.type.admin_only and not flask_login.current_user.is_admin:
                continue
            if action.disable_create_objects:
                continue
            if action.type.disable_create_objects:
                continue
            action_type_ids_with_usable_actions.add(action.type_id)
    return flask.render_template(
        'index.html',
        action_type_ids_with_usable_actions=action_type_ids_with_usable_actions
    )
