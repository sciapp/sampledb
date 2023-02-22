
from http import HTTPStatus

import flask
import flask_login

from . import frontend
from ..logic.background_tasks import get_background_tasks
from ..utils import FlaskResponseT


@frontend.route('/admin/background_tasks/')
@flask_login.login_required
def background_tasks() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(HTTPStatus.FORBIDDEN)
    return flask.render_template(
        'admin/background_tasks.html',
        tasks=get_background_tasks()
    )
