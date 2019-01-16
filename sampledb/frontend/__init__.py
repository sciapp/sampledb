# coding: utf-8
"""

"""

import flask

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

frontend = flask.Blueprint('frontend', __name__, template_folder='templates')


from . import actions
from . import authentication_forms
from . import index
from . import instruments
from . import locations
from . import objects
from . import objects_forms
from . import projects
from . import status
from . import users
from . import users_forms
from . import errors
from . import utils
