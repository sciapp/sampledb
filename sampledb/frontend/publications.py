# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from ..logic.publications import get_publications_for_user
from ..utils import FlaskResponseT


@frontend.route('/publications/')
@flask_login.login_required
def publications() -> FlaskResponseT:
    return flask.render_template(
        'publications.html',
        publications=get_publications_for_user(flask_login.current_user.id)
    )
