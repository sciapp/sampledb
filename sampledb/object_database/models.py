# coding: utf-8
"""

"""

from ..authentication.models import User
from .versioned_json_object_tables import VersionedJSONSerializableObjectTables

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class Object(VersionedJSONSerializableObjectTables.VersionedJSONSerializableObject):
    pass


Objects = VersionedJSONSerializableObjectTables(
    'objects', object_type=Object, user_id_column=User.id
)
