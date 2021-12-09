# coding: utf-8
"""

"""

from . import actions
from . import action_permissions
from . import action_translations
from . import action_type_translations
from . import api_log
from . import authentication
from . import comments
from . import datatypes
from . import dataverse_export
from . import errors
from . import export
from . import favorites
from . import files
from . import groups
from . import instruments
from . import instrument_log_entries
from . import languages
from . import ldap
from . import locale
from . import locations
from . import markdown_images
from . import markdown_to_html
from . import notebook_templates
from . import notifications
from . import objects
from . import object_log
from . import object_relationships
from . import object_search
from . import object_permissions
from . import object_sorting
from . import projects
from . import publications
from . import rdf
from . import schemas
from . import security_tokens
from . import settings
from . import tags
from . import units
from . import users
from . import user_log
from . import utils
from . import where_filters

from ..models.objects import Objects

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


__all__ = [
    'actions',
    'action_permissions',
    'action_translations',
    'action_type_translations',
    'api_log',
    'authentication',
    'comments',
    'datatypes',
    'dataverse_export',
    'errors',
    'export',
    'favorites',
    'files',
    'groups',
    'instruments',
    'instrument_translations',
    'instrument_log_entries',
    'languages',
    'ldap',
    'locale',
    'locations',
    'markdown_images',
    'markdown_to_html',
    'notebook_templates',
    'notifications',
    'objects',
    'object_log',
    'object_relationships',
    'object_search',
    'object_permissions',
    'object_sorting',
    'projects',
    'publications',
    'rdf',
    'security_tokens',
    'settings',
    'tags',
    'units',
    'users',
    'user_log',
    'utils',
    'where_filters',
]

Objects._data_validator = schemas.validate
Objects._schema_validator = schemas.validate_schema
