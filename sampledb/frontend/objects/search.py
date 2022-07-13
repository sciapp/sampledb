# coding: utf-8
"""

"""
import datetime
import flask
import flask_login

from .. import frontend
from ...logic.action_type_translations import get_action_types_with_translations_in_language
from ...logic.action_permissions import get_sorted_actions_for_user
from ...logic.object_permissions import Permissions, get_objects_with_permissions
from ...logic.users import get_users
from ...logic.languages import get_user_language
from ..utils import get_search_paths


@frontend.route('/objects/search/')
@flask_login.login_required
def search():
    actions = get_sorted_actions_for_user(
        user_id=flask_login.current_user.id
    )
    user_language_id = get_user_language(flask_login.current_user).id

    action_types = get_action_types_with_translations_in_language(user_language_id, filter_fed_defaults=True)

    search_paths, search_paths_by_action, search_paths_by_action_type = get_search_paths(actions, action_types)

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
        users=get_users(exclude_hidden=True),
        referencable_objects=referencable_objects
    ), 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
