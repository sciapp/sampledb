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
from . import admin_warnings
from . import authentication_forms
from . import background_tasks
from . import dataverse_export
from . import download_service
from . import export
from . import favicon
from . import group_categories
from . import index
from . import instruments
from . import locations
from . import location_types
from . import markdown_images
from . import languages
from . import objects
from . import projects
from . import publications
from . import scicat_export
from . import status
from . import tags
from . import timezone
from . import users
from . import users_forms
from . import errors
from . import utils
from . import federation


__all__ = [
    'actions',
    'action_types',
    'admin_warnings',
    'authentication_forms',
    'background_tasks',
    'dataverse_export',
    'download_service',
    'export',
    'favicon',
    'group_categories',
    'index',
    'instruments',
    'locations',
    'location_types',
    'markdown_images',
    'languages',
    'objects',
    'projects',
    'publications',
    'scicat_export',
    'status',
    'tags',
    'timezone',
    'users',
    'users_forms',
    'errors',
    'utils',
    'federation'
]
