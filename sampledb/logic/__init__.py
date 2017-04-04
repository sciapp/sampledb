# coding: utf-8
"""

"""

from . import instruments
from . import permissions
from . import authentication
from . import utils
from . import security_tokens
from . import where_filters
from . import schemas

from ..models.objects import Objects

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

Objects._data_validator = schemas.validate
Objects._schema_validator = schemas.validate_schema
