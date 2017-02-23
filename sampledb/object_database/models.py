# coding: utf-8
"""

"""

from sampledb.object_database.versioned_json_object_tables import VersionedJSONSerializableObjectTables

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class Object(VersionedJSONSerializableObjectTables.VersionedJSONSerializableObject):
    pass


Objects = VersionedJSONSerializableObjectTables(
    'objects', object_type=Object
)
