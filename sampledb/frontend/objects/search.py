# coding: utf-8
"""

"""
import datetime
import flask
import flask_login

from .. import frontend
from ...logic.action_types import get_action_types
from ...logic.action_permissions import get_sorted_actions_for_user
from ...logic.users import get_users
from ...logic.topics import get_topics
from ..utils import get_search_paths
from ...utils import FlaskResponseT


@frontend.route('/objects/search/')
@flask_login.login_required
def search() -> FlaskResponseT:
    actions = get_sorted_actions_for_user(
        user_id=flask_login.current_user.id
    )

    sorted_action_topics = []
    if not flask.current_app.config['DISABLE_TOPICS']:
        sorted_topics = get_topics()
        for topic in sorted_topics:
            for action in actions:
                if topic in action.topics:
                    sorted_action_topics.append(topic)
                    break

    action_types = [
        action_type
        for action_type in get_action_types(filter_fed_defaults=True)
        if action_type.show_in_object_filters
    ]

    search_paths, search_paths_by_action, search_paths_by_action_type = get_search_paths(actions, action_types, include_file_name=True)

    if None in search_paths_by_action_type:
        del search_paths_by_action_type[None]

    return flask.render_template(
        'search.html',
        search_paths=search_paths,
        search_paths_by_action=search_paths_by_action,
        search_paths_by_action_type=search_paths_by_action_type,
        actions=actions,
        action_types=action_types,
        sorted_action_topics=sorted_action_topics,
        datetime=datetime,
        users=get_users(exclude_hidden=not flask_login.current_user.is_admin or not flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN']),
    ), 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
