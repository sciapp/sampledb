# coding: utf-8
"""

"""
import datetime
import flask
import flask_login

from .. import frontend
from ...logic.action_types import get_action_types
from ...logic.action_permissions import get_sorted_actions_for_user
from ...logic.object_permissions import get_objects_with_permissions
from ...logic.users import get_users
from ..utils import get_search_paths
from ...utils import FlaskResponseT
from ...models import Permissions


@frontend.route('/objects/search/')
@flask_login.login_required
def search() -> FlaskResponseT:
    actions = get_sorted_actions_for_user(
        user_id=flask_login.current_user.id
    )

    action_types = get_action_types(filter_fed_defaults=True)

    search_paths, search_paths_by_action, search_paths_by_action_type = get_search_paths(actions, action_types)

    if None in search_paths_by_action_type:
        del search_paths_by_action_type[None]

    if not flask.current_app.config["LOAD_OBJECTS_IN_BACKGROUND"]:
        referencable_objects = get_objects_with_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.READ
        )
    else:
        referencable_objects = []
    return flask.render_template(
        'search.html',
        search_paths=search_paths,
        search_paths_by_action=search_paths_by_action,
        search_paths_by_action_type=search_paths_by_action_type,
        actions=actions,
        action_types=action_types,
        datetime=datetime,
        users=get_users(exclude_hidden=not flask_login.current_user.is_admin or not flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN']),
        referencable_objects=referencable_objects
    ), 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
