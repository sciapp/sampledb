# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from ..logic.actions import get_action, get_actions, ActionType
from ..logic.favorites import get_user_favorite_action_ids
from ..logic import errors
from .users.forms import ToggleFavoriteActionForm

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/actions/')
@flask_login.login_required
def actions():
    # TODO: instrument permissions
    action_type = flask.request.args.get('t', None)
    action_type = {
        'samples': ActionType.SAMPLE_CREATION,
        'measurements': ActionType.MEASUREMENT,
        'simulations': ActionType.SIMULATION
    }.get(action_type, None)
    if action_type is not None:
        actions = get_actions(action_type)
    else:
        actions = get_actions()
    user_favorite_action_ids = get_user_favorite_action_ids(flask_login.current_user.id)
    # Sort by: favorite / not favorite, instrument name (independent actions first), action name
    actions.sort(key=lambda action: (
        0 if action.id in user_favorite_action_ids else 1,
        action.instrument.name.lower() if action.instrument else '',
        action.name.lower()
    ))
    toggle_favorite_action_form = ToggleFavoriteActionForm()
    return flask.render_template(
        'actions/actions.html',
        actions=actions, ActionType=ActionType,
        user_favorite_action_ids=user_favorite_action_ids,
        toggle_favorite_action_form=toggle_favorite_action_form
    )


@frontend.route('/actions/<int:action_id>')
@flask_login.login_required
def action(action_id):
    try:
        action = get_action(action_id)
    except errors.ActionDoesNotExistError:
        return flask.abort(404)
    return flask.render_template('actions/action.html', action=action, ActionType=ActionType)
