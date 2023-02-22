# coding: utf-8
"""

"""
import typing

import flask
import flask_login

from .. import frontend
from ...logic.components import get_component
from ...logic.users import get_users
from ...utils import FlaskResponseT


@frontend.route('/users/')
@flask_login.login_required  # type: ignore[misc]
def users() -> FlaskResponseT:
    return flask.render_template(
        'users.html',
        users=sorted(get_users(exclude_hidden=not flask_login.current_user.is_admin), key=lambda u: typing.cast(int, u.id)),
        get_component=get_component
    )
