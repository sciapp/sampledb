# coding: utf-8
"""

"""

import flask
import flask_login

from .. import frontend
from ...logic.users import get_users


@frontend.route('/users/')
@flask_login.login_required
def users():
    return flask.render_template(
        'users.html',
        users=get_users()
    )
