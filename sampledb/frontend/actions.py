# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from ..models import Action, ActionType

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/actions/')
@flask_login.login_required
def actions():
    # TODO: instrument permissions
    actions = Action.query.all()
    return flask.render_template('actions/actions.html', actions=actions, ActionType=ActionType)


@frontend.route('/actions/<int:action_id>')
@flask_login.login_required
def action(action_id):
    action = Action.query.get(action_id)
    return flask.render_template('actions/action.html', action=action, ActionType=ActionType)
