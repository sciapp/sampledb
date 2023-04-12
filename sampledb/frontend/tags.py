# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from ..logic.tags import get_tags
from ..utils import FlaskResponseT


@frontend.route('/tags/')
@flask_login.login_required
def tags() -> FlaskResponseT:
    return flask.render_template(
        'tags.html',
        tags=list(sorted(get_tags(), key=lambda tag: (tag.name, tag.uses, tag.id)))
    )
