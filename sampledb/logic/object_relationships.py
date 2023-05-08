# coding: utf-8
"""

"""
from __future__ import annotations

import copy
import dataclasses
import typing

import flask

from .objects import get_object, find_object_references
from .object_permissions import get_user_permissions_for_multiple_objects
from ..models import ObjectLogEntryType, ObjectLogEntry, Permissions
from .. import db


def get_related_object_ids(
        object_id: int,
        include_referenced_objects: bool,
        include_referencing_objects: bool,
        user_id: typing.Optional[int] = None,
        filter_referencing_objects_by_permissions: bool = True
) -> typing.Tuple[
    typing.List[typing.Tuple[int, typing.Optional[str]]], typing.List[typing.Tuple[int, typing.Optional[str]]]
]:
    """
    Get IDs of objects related to a given object.

    An object is considered to be related, if it is:
    - a previous object of the given object (include_referenced_objects)
    - a measurement created using the given object (include_referencing_objects)
    - a sample created using the given object (include_referencing_objects)
    - any object referencing the given object in its metadata (include_referencing_objects)

    :param object_id: the ID of an existing object
    :param include_referenced_objects: whether to include referenced objects
    :param include_referencing_objects: whether to include referencing objects
    :param user_id: the ID of an existing user (optional)
    :param filter_referencing_objects_by_permissions: whether the referencing
        object ID list should only contain objects for which the given user has
        READ permissions
    :return: lists of previous object IDs, measurement IDs and sample IDs
    """
    referenced_object_ids: typing.Set[typing.Tuple[int, typing.Optional[str]]] = set()
    referencing_object_ids: typing.Set[typing.Tuple[int, typing.Optional[str]]] = set()
    if include_referenced_objects:
        object = get_object(object_id)
        for referenced_object_id, _previously_referenced_object_id, _schema_type in find_object_references(object, include_fed_references=True):
            if referenced_object_id is not None:
                referenced_object_ids.add(referenced_object_id)
    if include_referencing_objects:
        object_log_entries = ObjectLogEntry.query.filter(
            db.and_(
                ObjectLogEntry.object_id == object_id,
                ObjectLogEntry.type.in_((
                    ObjectLogEntryType.USE_OBJECT_IN_MEASUREMENT,
                    ObjectLogEntryType.USE_OBJECT_IN_SAMPLE_CREATION,
                    ObjectLogEntryType.REFERENCE_OBJECT_IN_METADATA
                ))
            )
        ).all()
        object_id_key_map = {
            ObjectLogEntryType.USE_OBJECT_IN_MEASUREMENT: 'measurement_id',
            ObjectLogEntryType.USE_OBJECT_IN_SAMPLE_CREATION: 'sample_id',
            ObjectLogEntryType.REFERENCE_OBJECT_IN_METADATA: 'object_id',
        }
        for object_log_entry in object_log_entries:
            object_id_key = object_id_key_map.get(object_log_entry.type, 'object_id')
            referencing_object_id = object_log_entry.data.get(object_id_key)
            if referencing_object_id is not None:
                referencing_object_ids.add((referencing_object_id, None))
        if filter_referencing_objects_by_permissions:
            object_permissions = get_user_permissions_for_multiple_objects(user_id, [referencing_object_id[0] for referencing_object_id in referencing_object_ids])
            referencing_object_ids = {
                referencing_object_id
                for referencing_object_id in referencing_object_ids
                if Permissions.READ in object_permissions[referencing_object_id[0]]
            }
    return list(referencing_object_ids), list(referenced_object_ids)


@dataclasses.dataclass(kw_only=True)
class RelatedObjectsTree:
    object_id: int
    component_uuid: typing.Optional[str]
    path: typing.List[typing.Union[typing.Tuple[int, typing.Optional[str]], int]]
    permissions: str
    referenced_objects: typing.Optional[typing.List[RelatedObjectsTree]]
    referencing_objects: typing.Optional[typing.List[RelatedObjectsTree]]


def build_related_objects_tree(
        object_id: int,
        user_id: typing.Optional[int],
) -> RelatedObjectsTree:
    """
    Get the tree of related objects for a given object.

    Each node in the tree contains:
    - the ID of an object
    - one possible path from the given object to this object

    All nodes for an object contain the same path to it, and the node at this
    path also contains lists of nodes for previous objects, measurements and
    samples.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :return: the related objects tree
    """
    subtrees: typing.Dict[typing.Tuple[int, typing.Optional[str]], typing.Tuple[RelatedObjectsTree, typing.List[typing.Tuple[int, typing.Optional[str]]], typing.List[typing.Tuple[int, typing.Optional[str]]]]] = {}
    _gather_subtrees(
        object_id=object_id,
        component_uuid=None,
        user_id=user_id,
        subtrees=subtrees
    )

    object_ids = tuple(
        object_id
        for object_id, component_uuid in subtrees
        if component_uuid is None or component_uuid == flask.current_app.config['FEDERATION_UUID']
    )
    objects_permissions = get_user_permissions_for_multiple_objects(user_id, object_ids)

    return _assemble_tree(subtrees[(object_id, None)][0], objects_permissions, subtrees)


def _gather_subtrees(
        object_id: int,
        component_uuid: typing.Optional[str],
        user_id: typing.Optional[int],
        subtrees: typing.Dict[typing.Tuple[int, typing.Optional[str]], typing.Tuple[RelatedObjectsTree, typing.List[typing.Tuple[int, typing.Optional[str]]], typing.List[typing.Tuple[int, typing.Optional[str]]]]],
        parent_object_id: typing.Optional[int] = None,
        parent_component_id: typing.Optional[str] = None
) -> None:
    if (object_id, component_uuid) in subtrees:
        return
    tree = RelatedObjectsTree(
        object_id=object_id,
        component_uuid=component_uuid,
        path=[],
        permissions='none',
        referenced_objects=None,
        referencing_objects=None,
    )
    subtrees[object_id, component_uuid] = (tree, [], [])
    if component_uuid is None or component_uuid == flask.current_app.config['FEDERATION_UUID']:
        referencing_object_ids, referenced_object_ids = get_related_object_ids(
            object_id=object_id,
            include_referenced_objects=True,
            include_referencing_objects=True,
            user_id=user_id,
            filter_referencing_objects_by_permissions=False
        )
        for child_object_list, filtered_child_object_list in [
            (referenced_object_ids, subtrees[object_id, component_uuid][1]),
            (referencing_object_ids, subtrees[object_id, component_uuid][2])
        ]:
            for child_object_id, child_component_uuid in child_object_list:
                if (child_object_id, child_component_uuid) != (parent_object_id, parent_component_id):
                    _gather_subtrees(
                        object_id=child_object_id,
                        component_uuid=child_component_uuid,
                        user_id=user_id,
                        subtrees=subtrees,
                        parent_object_id=object_id,
                        parent_component_id=component_uuid
                    )
                    filtered_child_object_list.append((child_object_id, child_component_uuid))


def _assemble_tree(
        tree: RelatedObjectsTree,
        objects_permissions: typing.Dict[int, Permissions],
        subtrees: typing.Dict[typing.Tuple[int, typing.Optional[str]], typing.Tuple[RelatedObjectsTree, typing.List[typing.Tuple[int, typing.Optional[str]]], typing.List[typing.Tuple[int, typing.Optional[str]]]]],
        path_prefix: typing.Optional[typing.List[typing.Union[int, typing.Tuple[int, typing.Optional[str]]]]] = None
) -> RelatedObjectsTree:
    if path_prefix is None:
        path_prefix = []

    tree, referenced_object_ids, referencing_object_ids = subtrees[(tree.object_id, tree.component_uuid)]
    if not tree.path:
        tree.path = path_prefix + [(tree.object_id, tree.component_uuid)]
        if tree.component_uuid is None or tree.component_uuid == flask.current_app.config['FEDERATION_UUID']:
            if Permissions.READ in objects_permissions[tree.object_id]:
                tree.permissions = objects_permissions[tree.object_id].name.lower()
                # create a copy that will contain subtrees
                tree = copy.deepcopy(tree)
                tree.referenced_objects = [
                    _assemble_tree(subtrees[referenced_object_id][0], objects_permissions, subtrees, tree.path + [-1])
                    for referenced_object_id in referenced_object_ids
                ]
                tree.referencing_objects = [
                    _assemble_tree(subtrees[referencing_object_id][0], objects_permissions, subtrees, tree.path + [-2])
                    for referencing_object_id in referencing_object_ids
                    if Permissions.READ in objects_permissions[referencing_object_id[0]]
                ]
    return tree
