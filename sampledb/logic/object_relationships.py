# coding: utf-8
"""

"""
from __future__ import annotations

import dataclasses
import datetime
import itertools
import typing
import sys

import flask

from .actions import get_action, Action
from .files import get_files_for_object, File
from .objects import get_object, find_object_references
from .object_permissions import get_user_permissions_for_multiple_objects, get_objects_with_permissions
from ..models import ObjectLogEntryType, ObjectLogEntry, Permissions, Object
from .. import db
from .utils import get_translated_text

# limit tree depth to avoid hitting the recursion limit in the frontend
_MAXIMUM_TREE_DEPTH = sys.getrecursionlimit() - 100


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


@dataclasses.dataclass(kw_only=True, frozen=True)
class ObjectRef:
    object_id: int
    component_uuid: typing.Optional[str]
    eln_source_url: typing.Optional[str]
    eln_object_url: typing.Optional[str]

    @property
    def is_local(self) -> bool:
        return (self.component_uuid is None or self.component_uuid == flask.current_app.config['FEDERATION_UUID']) and self.eln_source_url is None and self.eln_object_url is None


@dataclasses.dataclass(kw_only=True)
class RelatedObjectsTree:
    object_ref: ObjectRef
    path: typing.List[typing.Union[int, ObjectRef]]
    object: typing.Optional[Object]
    object_name: typing.Optional[str]
    referenced_objects: typing.Optional[typing.List[RelatedObjectsTree]]
    referencing_objects: typing.Optional[typing.List[RelatedObjectsTree]]

    @property
    def object_id(self) -> int:
        return self.object_ref.object_id

    @property
    def component_uuid(self) -> typing.Optional[str]:
        return self.object_ref.component_uuid

    @property
    def eln_source_url(self) -> typing.Optional[str]:
        return self.object_ref.eln_source_url

    @property
    def eln_object_url(self) -> typing.Optional[str]:
        return self.object_ref.eln_object_url


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
    object_ref = ObjectRef(
        object_id=object_id,
        component_uuid=None,
        eln_source_url=None,
        eln_object_url=None
    )
    subtrees = _gather_subtrees(
        object_ref=object_ref
    )

    object_ids = tuple(
        object_ref.object_id
        for object_ref in subtrees
        if object_ref.is_local
    )
    objects = get_objects_with_permissions(user_id=user_id, permissions=Permissions.READ, object_ids=object_ids, name_only=True)
    objects_by_id = {
        object.object_id: object
        for object in objects
    }
    return _assemble_tree(subtrees[object_ref][0], objects_by_id, subtrees)


def get_referencing_object_ids(
        object_ids: typing.Set[int]
) -> typing.Dict[int, typing.Set[ObjectRef]]:
    if not object_ids:
        return {}
    referencing_object_ids_by_id: typing.Dict[int, typing.Set[ObjectRef]] = {
        object_id: set()
        for object_id in object_ids
    }
    for object_id, referencing_object_id, referencing_component_uuid, referencing_eln_source_url, referencing_eln_object_url in db.session.execute(db.text("""
        SELECT DISTINCT object_id, coalesce(data -> 'object_id', data -> 'sample_id', data -> 'measurement_id', NULL)::text::integer AS referencing_object_id, NULL AS referencing_component_uuid, NULL AS eln_source_url, NULL AS eln_object_url
        FROM object_log_entries
        WHERE object_id IN :object_ids AND type IN ('USE_OBJECT_IN_MEASUREMENT', 'USE_OBJECT_IN_SAMPLE_CREATION', 'REFERENCE_OBJECT_IN_METADATA')
    """), {'object_ids': tuple(object_ids)}).fetchall():
        referencing_object_ids_by_id[object_id].add(ObjectRef(object_id=referencing_object_id, component_uuid=referencing_component_uuid, eln_source_url=referencing_eln_source_url, eln_object_url=referencing_eln_object_url))
    return referencing_object_ids_by_id


def _get_referenced_object_ids(
        object_ids: typing.Set[int]
) -> typing.Dict[int, typing.Set[ObjectRef]]:
    if not object_ids:
        return {}
    referenced_object_ids_by_id: typing.Dict[int, typing.Set[ObjectRef]] = {
        object_id: set()
        for object_id in object_ids
    }
    for object_id, referenced_object_id, referenced_component_uuid, referenced_eln_source_url, referenced_eln_object_url in db.session.execute(db.text("""
        WITH RECURSIVE properties(object_id, value) AS (
            SELECT objects_current.object_id, data.value
            FROM objects_current, jsonb_each(objects_current.data) AS data
            WHERE objects_current.object_id IN :object_ids AND jsonb_typeof(objects_current.data) = 'object'
        UNION ALL
            SELECT properties.object_id, coalesce(object_data.value, array_data.value)
            FROM properties
            LEFT OUTER JOIN jsonb_each(CASE
                WHEN jsonb_typeof(properties.value) = 'object' THEN properties.value
                ELSE '{}'::jsonb
            END) AS object_data ON jsonb_typeof(properties.value) = 'object'
            LEFT OUTER JOIN jsonb_array_elements(CASE
                WHEN jsonb_typeof(properties.value) = 'array' THEN properties.value
                ELSE '[]'::jsonb
            END) AS array_data ON jsonb_typeof(properties.value) = 'array'
            WHERE jsonb_typeof(properties.value) = 'object' OR jsonb_typeof(properties.value) = 'array'
        )
        SELECT object_id, (properties.value -> 'object_id')::integer, properties.value ->> 'component_uuid', properties.value ->> 'eln_source_url', properties.value ->> 'eln_object_url'
        FROM properties
        WHERE jsonb_typeof(properties.value) = 'object' AND properties.value ? '_type' AND properties.value ? 'object_id' AND properties.value ->> '_type' IN ('object_reference', 'sample', 'measurement')
    """), {'object_ids': tuple(object_ids)}).fetchall():
        referenced_object_ids_by_id[object_id].add(ObjectRef(object_id=referenced_object_id, component_uuid=referenced_component_uuid, eln_source_url=referenced_eln_source_url, eln_object_url=referenced_eln_object_url))
    return referenced_object_ids_by_id


def _gather_subtrees(
        object_ref: ObjectRef,
) -> typing.Dict[ObjectRef, typing.Tuple[RelatedObjectsTree, typing.List[ObjectRef], typing.List[ObjectRef]]]:
    subtrees: typing.Dict[ObjectRef, typing.Tuple[RelatedObjectsTree, typing.List[ObjectRef], typing.List[ObjectRef]]] = {}
    object_ref_stack: typing.List[typing.Tuple[ObjectRef, typing.Optional[ObjectRef]]] = [
        (object_ref, None)
    ]
    referencing_object_ids_by_id: typing.Dict[int, typing.Set[ObjectRef]] = {}
    referenced_object_ids_by_id: typing.Dict[int, typing.Set[ObjectRef]] = {}
    while object_ref_stack:
        object_ref, parent_object_ref = object_ref_stack.pop()
        if object_ref not in subtrees:
            tree = RelatedObjectsTree(
                object_ref=object_ref,
                path=[],
                object=None,
                object_name=None,
                referenced_objects=None,
                referencing_objects=None,
            )
            subtrees[object_ref] = (tree, [], [])

            if object_ref.is_local:
                referencing_object_ids = referencing_object_ids_by_id.get(object_ref.object_id)
                referenced_object_ids = referenced_object_ids_by_id.get(object_ref.object_id)
                if referencing_object_ids is None:
                    referencing_object_ids = get_referencing_object_ids({object_ref.object_id})[object_ref.object_id]
                if referenced_object_ids is None:
                    referenced_object_ids = _get_referenced_object_ids({object_ref.object_id})[object_ref.object_id]

                for child_object_list, filtered_child_object_list in [
                    (referenced_object_ids, subtrees[object_ref][1]),
                    (referencing_object_ids, subtrees[object_ref][2])
                ]:
                    for child_object_ref in child_object_list:
                        if child_object_ref != parent_object_ref:
                            filtered_child_object_list.append(child_object_ref)
                            object_ref_stack.append((child_object_ref, object_ref))
                local_child_object_ids = {
                    child_object_ref.object_id
                    for child_object_ref in itertools.chain(subtrees[object_ref][1], subtrees[object_ref][2])
                    if child_object_ref.is_local and child_object_ref not in subtrees
                }
                referencing_object_ids_by_id.update(get_referencing_object_ids(local_child_object_ids))
                referenced_object_ids_by_id.update(_get_referenced_object_ids(local_child_object_ids))
    return subtrees


def _assemble_tree(
        tree: RelatedObjectsTree,
        objects_by_id: typing.Dict[int, Object],
        subtrees: typing.Dict[ObjectRef, typing.Tuple[RelatedObjectsTree, typing.List[ObjectRef], typing.List[ObjectRef]]],
        path_prefix: typing.Optional[typing.List[typing.Union[int, ObjectRef]]] = None
) -> RelatedObjectsTree:
    if path_prefix is None:
        path_prefix = []
    root_object_ref = tree.object_ref
    root_tree = tree
    tree_stack: typing.List[typing.Tuple[ObjectRef, typing.List[typing.Union[int, ObjectRef]], typing.Optional[RelatedObjectsTree]]] = [
        (root_object_ref, path_prefix, None)
    ]
    while tree_stack:
        object_ref, path_prefix, parent_tree = tree_stack.pop()

        tree, referenced_object_ids, referencing_object_ids = subtrees[object_ref]
        if not tree.path:

            tree.path = path_prefix + [object_ref]
            if len(path_prefix) // 2 < _MAXIMUM_TREE_DEPTH:
                if object_ref.is_local and object_ref.object_id in objects_by_id:
                    object = objects_by_id[object_ref.object_id]
                    tree.object = object
                    if object is not None and object.name is not None:
                        tree.object_name = get_translated_text(object.name)
                    # create a copy that will contain subtrees
                    tree = dataclasses.replace(
                        tree,
                        referenced_objects=[],
                        referencing_objects=[]
                    )
                    if object_ref == root_object_ref:
                        root_tree = tree
                    for referenced_object_id in referenced_object_ids:
                        tree_stack.append((referenced_object_id, tree.path + [-1], tree))
                    for referencing_object_id in referencing_object_ids:
                        if referencing_object_id.is_local and referencing_object_id.object_id in objects_by_id:
                            tree_stack.append((referencing_object_id, tree.path + [-2], tree))
        if parent_tree is not None:
            if path_prefix[-1] == -1 and parent_tree.referenced_objects is not None:
                parent_tree.referenced_objects.append(tree)
            if path_prefix[-1] == -2 and parent_tree.referencing_objects is not None:
                parent_tree.referencing_objects.append(tree)
    return root_tree


@dataclasses.dataclass(frozen=True)
class WorkflowElement:
    object_id: int
    object: typing.Optional[Object]
    action: typing.Optional[Action]
    is_referencing: bool
    is_referenced: bool
    files: typing.List[File]


def get_workflow_references(object: Object, user_id: int, actions_by_id: typing.Optional[typing.Dict[int, Action]] = None) -> typing.List[WorkflowElement]:
    """
    Creates a list describing all direct object relations for a workflow view as configured in an object's schema.


    :param object: The object for which the workflow view is to be created
    :param user_id: User ID of the user viewing the workflow view taking into account the access permissions
    :param actions_by_id: A dict containing cached actions by ID
    :return: List of WorkflowElements containing, object ID, object data, action data and if the object is referenced
            and/or referencing the object the view is created for
    """
    if object.schema is None or 'workflow_view' not in object.schema.keys():
        return []

    if actions_by_id is None:
        actions_by_id = {}

    referencing_objects = {
        object_ref.object_id
        for object_ref in get_referencing_object_ids({object.object_id})[object.object_id]
        if object_ref.is_local}
    referenced_objects = {
        object_ref.object_id
        for object_ref in _get_referenced_object_ids({object.object_id})[object.object_id]
        if object_ref.is_local
    }

    referencing_workflow_action_ids = None if 'referencing_action_id' not in object.schema['workflow_view'] else [object.schema['workflow_view']['referencing_action_id']] if isinstance(object.schema['workflow_view']['referencing_action_id'], int) else object.schema['workflow_view']['referencing_action_id']
    referencing_workflow_action_type_ids = None if 'referencing_action_type_id' not in object.schema['workflow_view'] else [object.schema['workflow_view']['referencing_action_type_id']] if isinstance(object.schema['workflow_view']['referencing_action_type_id'], int) else object.schema['workflow_view']['referencing_action_type_id']

    referenced_workflow_action_ids = None if 'referenced_action_id' not in object.schema['workflow_view'] else [object.schema['workflow_view']['referenced_action_id']] if isinstance(object.schema['workflow_view']['referenced_action_id'], int) else object.schema['workflow_view']['referenced_action_id']
    referenced_workflow_action_type_ids = None if 'referenced_action_type_id' not in object.schema['workflow_view'] else [object.schema['workflow_view']['referenced_action_type_id']] if isinstance(object.schema['workflow_view']['referenced_action_type_id'], int) else object.schema['workflow_view']['referenced_action_type_id']

    object_ids = list(referencing_objects.union(referenced_objects))
    objects = get_objects_with_permissions(user_id, Permissions.READ, object_ids=object_ids)
    objects_by_id = {
        object.object_id: object
        for object in objects
    }
    initital_object_version_by_id = {}
    for object_id in object_ids:
        current_object_version = objects_by_id.get(object_id)
        if current_object_version is not None and current_object_version.version_id == 0:
            initital_object_version_by_id[object_id] = current_object_version
        else:
            initital_object_version_by_id[object_id] = get_object(object_id, version_id=0)

    def creation_time_key(object_id: int) -> datetime.datetime:
        initital_object_version = initital_object_version_by_id.get(object_id)
        if initital_object_version is None or initital_object_version.utc_datetime is None:
            return datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
        return initital_object_version.utc_datetime

    object_ids.sort(key=creation_time_key)

    workflow = []
    for object_id in object_ids:
        action_id = initital_object_version_by_id[object_id].action_id
        if action_id:
            if action_id in actions_by_id:
                action = actions_by_id[action_id]
            else:
                action = get_action(action_id)
                actions_by_id[action_id] = action
        else:
            action = None

        if (
            (referencing_workflow_action_ids is None and referenced_workflow_action_ids is None and referencing_workflow_action_type_ids is None and referenced_workflow_action_type_ids is None) or
            (
                object_id in referencing_objects and
                (
                    (referencing_workflow_action_ids is None or action_id in referencing_workflow_action_ids) and
                    (
                        referencing_workflow_action_type_ids is None or
                        (
                            action and action.type and (
                                action.type.id in referencing_workflow_action_type_ids or
                                (action.type.fed_id and action.type.fed_id < 0 and action.type.fed_id in referencing_workflow_action_type_ids)
                            )
                        )
                    )
                )
            ) or (
                object_id in referenced_objects and
                (
                    (referenced_workflow_action_ids is None or action_id in referenced_workflow_action_ids) and
                    (
                        referenced_workflow_action_type_ids is None or
                        (
                            action and action.type and
                            (
                                action.type.id in referenced_workflow_action_type_ids or
                                (action.type.fed_id and action.type.fed_id < 0 and action.type.fed_id in referenced_workflow_action_type_ids)
                            )
                        )
                    )
                )
            )
        ):
            if object_id in objects_by_id:
                files = get_files_for_object(object_id)
            else:
                files = []
            workflow.append(WorkflowElement(
                object_id=object_id,
                object=objects_by_id.get(object_id),
                action=action,
                is_referenced=object_id in referenced_objects,
                is_referencing=object_id in referencing_objects,
                files=files
            ))
    return workflow
