# coding: utf-8
"""

"""

import typing

from .objects import get_object, find_object_references
from .object_log import get_object_log_entries, ObjectLogEntryType
from .object_permissions import get_user_object_permissions, Permissions


def get_related_object_ids(
        object_id: int,
        include_referenced_objects: bool,
        include_referencing_objects: bool,
        user_id: typing.Optional[int] = None
) -> typing.Tuple[
    typing.List[int], typing.List[int]
]:
    """
    Get IDs of objects related to a given object.

    An object is considered to be related, if it is:
    - a previous object of the given object (include_referenced_objects)
    - a measurement created using the given object (include_referencing_objects)
    - a sample created using the given object (include_referencing_objects)
    - any object referencing the given object in its metadata (include_referencing_objects)

    If user_id is not None, only objects which the given user has READ
    permissions for will be included in the result.

    :param object_id: the ID of an existing object
    :param include_referenced_objects: whether to include referenced objects
    :param include_referencing_objects: whether to include referencing objects
    :param user_id: the ID of an existing user (optional)
    :return: lists of previous object IDs, measurement IDs and sample IDs
    """
    referenced_object_ids = []
    referencing_object_ids = []
    if include_referenced_objects:
        object = get_object(object_id)
        for referenced_object_id, previously_referenced_object_id, schema_type in find_object_references(object):
            if user_id is None or Permissions.READ in get_user_object_permissions(referenced_object_id, user_id):
                referenced_object_ids.append(referenced_object_id)
    if include_referencing_objects:
        object_log_entries = get_object_log_entries(object_id, user_id)
        for object_log_entry in object_log_entries:
            if object_log_entry.type == ObjectLogEntryType.USE_OBJECT_IN_MEASUREMENT:
                measurement_id = object_log_entry.data.get('measurement_id')
                if measurement_id is not None:
                    referencing_object_ids.append(measurement_id)
            if object_log_entry.type == ObjectLogEntryType.USE_OBJECT_IN_SAMPLE_CREATION:
                sample_id = object_log_entry.data.get('sample_id')
                if sample_id is not None:
                    referencing_object_ids.append(sample_id)
            if object_log_entry.type == ObjectLogEntryType.REFERENCE_OBJECT_IN_METADATA:
                referencing_object_id = object_log_entry.data.get('object_id')
                if referencing_object_id is not None:
                    referencing_object_ids.append(referencing_object_id)
    return referencing_object_ids, referenced_object_ids


def build_related_objects_tree(
        object_id: int,
        user_id: typing.Optional[int] = None,
        path: typing.Optional[typing.List[int]] = None,
        visited_paths: typing.Dict[int, typing.List[int]] = None
) -> typing.Any:
    """
    Get the tree of related objects for a given object.

    Each node in the tree contains:
    - the ID of an object
    - one possible path from the given object to this object

    All nodes for an object contain the same path to it, and the node at this
    path also contains lists of nodes for previous objects, measurements and
    samples.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user (optional)
    :param path: the path leading to this object (internal)
    :param visited_paths: all previously visited paths (internal)
    :return: the related objects tree as a nested dictionary of lists
    """
    if path is None:
        path = [object_id]
    else:
        path = path + [object_id]
    if visited_paths is None:
        visited_paths = {}
    if object_id in visited_paths:
        tree = {
            'object_id': object_id,
            'path': visited_paths[object_id]
        }
    else:
        visited_paths[object_id] = path
        referencing_object_ids, referenced_object_ids = get_related_object_ids(
            object_id=object_id,
            include_referenced_objects=True,
            include_referencing_objects=True,
            user_id=user_id
        )
        tree = {
            'object_id': object_id,
            'path': path,
            'referenced_objects': [
                build_related_objects_tree(referenced_object_id, user_id, path + [-1], visited_paths)
                for referenced_object_id in referenced_object_ids
                if len(path) == 1 or referenced_object_id != path[-3]
            ],
            'referencing_objects': [
                build_related_objects_tree(referencing_object_id, user_id, path + [-2], visited_paths)
                for referencing_object_id in referencing_object_ids
                if len(path) == 1 or referencing_object_id != path[-3]
            ]
        }

    return tree
