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
from . import action_types
from . import authentication_forms
from . import dataverse_export
from . import export
from . import favicon
from . import index
from . import instruments
from . import locations
from . import markdown_images
from . import languages
from . import objects
from . import objects_forms
from . import projects
from . import status
from . import tags
from . import timezone
from . import users
from . import users_forms
from . import errors
from . import utils


__all__ = [
    'actions',
    'action_types',
    'authentication_forms',
    'dataverse_export',
    'export',
    'favicon',
    'index',
    'instruments',
    'locations',
    'markdown_images',
    'languages',
    'objects',
    'objects_forms',
    'projects',
    'status',
    'tags',
    'timezone',
    'users',
    'users_forms',
    'errors',
    'utils'
]
