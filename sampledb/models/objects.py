# coding: utf-8
"""

"""

from .. import db
from .users import User
from .actions import Action
from .components import Component
from .eln_imports import ELNImport
from .versioned_json_object_tables import VersionedJSONSerializableObjectTables, Object

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

__all__ = [
    'Object',
    'Objects'
]


Objects = VersionedJSONSerializableObjectTables(
    'objects',
    user_id_column=User.id,
    action_id_column=Action.id,
    action_schema_column=Action.schema,
    component_id_column=Component.id,
    eln_import_id_column=ELNImport.id,
    metadata=db.metadata
)
