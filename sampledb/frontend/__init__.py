# coding: utf-8
"""

"""

import os
import flask

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

frontend = flask.Blueprint(
    'frontend',
    __name__,
    template_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
)


from . import actions
from . import authentication_forms
from . import export
from . import index
from . import instruments
from . import locations
from . import objects
from . import objects_forms
from . import projects
from . import status
from . import tags
from . import users
from . import users_forms
from . import errors
from . import utils


__all__ = [
    'actions',
    'authentication_forms',
    'export',
    'index',
    'instruments',
    'locations',
    'objects',
    'objects_forms',
    'projects',
    'status',
    'tags',
    'users',
    'users_forms',
    'errors',
    'utils'
]
