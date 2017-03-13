# coding: utf-8
"""

"""

import flask

rest_api = flask.Blueprint('rest_api', __name__)


from . import instruments
from . import objects
from . import permissions
