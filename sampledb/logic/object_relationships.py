# coding: utf-8
"""

"""
from __future__ import annotations

import dataclasses
import datetime
import itertools
import typing
import sys
import operator

import flask

from .actions import get_action, Action
from .files import get_files_for_object, File
from .objects import get_object, find_object_references
from .object_permissions import get_user_permissions_for_multiple_objects, get_objects_with_permissions
from ..models import ObjectLogEntryType, ObjectLogEntry, Permissions, Object
from .. import db

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
        for referenced_object_id, _previously_referenced_object_id, _schema_type in find_object_references(object_id=object.object_id, version_id=object.version_id, object_data=object.data, include_fed_references=True):
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
class RelatedObjectsSubTree:
    referenced_objects: typing.List[ObjectRef]
    referencing_objects: typing.List[ObjectRef]


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


def gather_related_object_subtrees(
        object_id: int
) -> typing.Dict[ObjectRef, RelatedObjectsSubTree]:
    object_ref = ObjectRef(
        object_id=object_id,
        component_uuid=None,
        eln_source_url=None,
        eln_object_url=None,
    )
    subtrees: typing.Dict[ObjectRef, RelatedObjectsSubTree] = {}
    object_ref_stack: typing.List[typing.Tuple[ObjectRef, typing.Optional[ObjectRef]]] = [
        (object_ref, None)
    ]
    referencing_object_ids_by_id: typing.Dict[int, typing.Set[ObjectRef]] = {}
    referenced_object_ids_by_id: typing.Dict[int, typing.Set[ObjectRef]] = {}
    while object_ref_stack:
        object_ref, parent_object_ref = object_ref_stack.pop()
        if object_ref not in subtrees:
            subtrees[object_ref] = RelatedObjectsSubTree(referenced_objects=[], referencing_objects=[])

            if object_ref.is_local:
                referencing_object_ids = referencing_object_ids_by_id.get(object_ref.object_id)
                referenced_object_ids = referenced_object_ids_by_id.get(object_ref.object_id)
                if referencing_object_ids is None:
                    referencing_object_ids = get_referencing_object_ids({object_ref.object_id})[object_ref.object_id]
                if referenced_object_ids is None:
                    referenced_object_ids = _get_referenced_object_ids({object_ref.object_id})[object_ref.object_id]

                for child_object_list, filtered_child_object_list in [
                    (referenced_object_ids, subtrees[object_ref].referenced_objects),
                    (referencing_object_ids, subtrees[object_ref].referencing_objects)
                ]:
                    for child_object_ref in child_object_list:
                        if child_object_ref != parent_object_ref:
                            filtered_child_object_list.append(child_object_ref)
                            object_ref_stack.append((child_object_ref, object_ref))
                local_child_object_ids = {
                    child_object_ref.object_id
                    for child_object_ref in itertools.chain(subtrees[object_ref].referenced_objects, subtrees[object_ref].referencing_objects)
                    if child_object_ref.is_local and child_object_ref not in subtrees
                }
                referencing_object_ids_by_id.update(get_referencing_object_ids(local_child_object_ids))
                referenced_object_ids_by_id.update(_get_referenced_object_ids(local_child_object_ids))
    return subtrees


@dataclasses.dataclass(frozen=True)
class WorkflowElement:
    object_id: int
    object: typing.Optional[Object]
    action: typing.Optional[Action]
    is_referencing: bool
    is_referenced: bool
    files: typing.List[File]
    is_current_referenced: bool = True
    is_current_referencing: bool = True
    path: typing.Optional[typing.List[WorkflowElement]] = None
    duplicate: bool = False


@dataclasses.dataclass(frozen=True)
class ActionFilter:
    action_ids: typing.Optional[typing.List[int]] = None
    action_type_ids: typing.Optional[typing.List[int]] = None
    filter_operator: typing.Callable[[bool, bool], bool] = operator.and_

    @property
    def is_none(self) -> bool:
        return self.action_ids is None and self.action_type_ids is None

    def __call__(self, action: typing.Optional[Action]) -> bool:
        return self.filter_operator(
            self.action_ids is None or
            (
                action is not None and
                action.id in self.action_ids
            ),
            self.action_type_ids is None or
            (
                action is not None and
                action.type is not None and
                (
                    action.type.id in self.action_type_ids or
                    (
                        action.type.fed_id is not None and
                        action.type.fed_id < 0 and
                        action.type.fed_id in self.action_type_ids
                    )
                )
            )
        )


@dataclasses.dataclass(frozen=True)
class ActionFilters:
    referencing_objects_filter: ActionFilter = ActionFilter()
    referenced_objects_filter: ActionFilter = ActionFilter()

    @property
    def is_none(self) -> bool:
        return self.referencing_objects_filter.is_none and self.referenced_objects_filter.is_none


def get_workflow_references(object: Object, user_id: int, actions_by_id: typing.Optional[typing.Dict[int, Action]] = None) -> typing.List[typing.List[WorkflowElement]]:
    """
    Creates a list describing all direct object relations for workflow views as configured in an object's schema.

    :param object: The object for which workflow views are to be created
    :param user_id: User ID of the user viewing the workflow views taking into account the access permissions
    :param actions_by_id: A dict containing cached actions by ID
    :return: List of lists of WorkflowElements containing, object ID, object data, action data and if the object is referenced
            and/or referencing the object the view is created for
    """
    if object.schema is None or ('workflow_view' not in object.schema.keys() and 'workflow_views' not in object.schema.keys()):
        return []

    if 'workflow_view' in object.schema:
        workflow_views = [object.schema['workflow_view']]
    else:
        workflow_views = object.schema['workflow_views']

    if actions_by_id is None:
        actions_by_id = {}

    initial_object_version_by_id = {}
    objects_by_id: typing.Dict[int, Object] = {}
    files_by_object_id: typing.Dict[int, typing.List[File]] = {}

    workflows: typing.List[typing.List[WorkflowElement]] = [
        []
        for _ in workflow_views
    ]

    def _handle_object(
        object: Object,
        workflow_index: int,
        path: typing.List[WorkflowElement],
        actions_by_id: typing.Dict[int, Action],
        workflow_action_filters: ActionFilters,
        recursion_action_filters: ActionFilters,
        max_depth: typing.Optional[int]
    ) -> None:
        if path is None:
            path = []

        wf = workflow_action_filters
        rf = recursion_action_filters

        referencing_object_ids = {
            object_ref.object_id
            for object_ref in get_referencing_object_ids({object.object_id})[object.object_id]
            if object_ref.is_local
        }

        referencing_objects_current = {}
        for referencing_object_id in referencing_object_ids:
            referencing_objects_current[referencing_object_id] = False
            referencing_object = get_object(referencing_object_id)
            for referenced_object_id, _previously_referenced_object_id, _schema_type in find_object_references(
                    object_id=referencing_object.object_id,
                    version_id=referencing_object.version_id,
                    object_data=referencing_object.data
            ):
                if referenced_object_id == object.object_id:
                    referencing_objects_current[referencing_object_id] = True
                    break

        referenced_object_ids = {
            object_ref.object_id
            for object_ref in _get_referenced_object_ids({object.object_id})[object.object_id]
            if object_ref.is_local
        }

        object_ids = list(referencing_object_ids.union(referenced_object_ids))

        new_object_ids = list(set(object_ids).difference(set(objects_by_id.keys())))
        if new_object_ids:
            new_objects = get_objects_with_permissions(user_id, Permissions.READ, object_ids=new_object_ids)
        else:
            new_objects = []

        objects_by_id.update({
            object.object_id: object
            for object in new_objects
        })

        for object_id in new_object_ids:
            current_object_version = objects_by_id.get(object_id)
            if current_object_version is not None and current_object_version.version_id == 0:
                initial_object_version_by_id[object_id] = current_object_version
            else:
                initial_object_version_by_id[object_id] = get_object(object_id, version_id=0)

        for object_id in object_ids:
            action_id = initial_object_version_by_id[object_id].action_id
            action = None
            if action_id:
                if action_id in actions_by_id:
                    action = actions_by_id[action_id]
                else:
                    action = get_action(action_id)
                    actions_by_id[action_id] = action

            if (
                wf.is_none or
                (
                    object_id in referencing_object_ids and wf.referencing_objects_filter(action)
                ) or (
                    object_id in referenced_object_ids and wf.referenced_objects_filter(action)
                )
            ):
                if object_id in objects_by_id:
                    if object_id not in files_by_object_id:
                        files_by_object_id[object_id] = get_files_for_object(object_id)
                    files = files_by_object_id[object_id]
                else:
                    files = []
                elem_object = objects_by_id.get(object_id)
                welem = WorkflowElement(
                    object_id=object_id,
                    object=elem_object,
                    action=action,
                    is_referenced=object_id in referenced_object_ids,
                    is_referencing=object_id in referencing_object_ids,
                    files=files,
                    is_current_referenced=object_id in referenced_object_ids,
                    is_current_referencing=referencing_objects_current.get(object_id, False),
                    path=path,
                    duplicate=object_id in objects_in_workflow
                )
                objects_in_workflow.add(object_id)
                workflows[workflow_index].append(welem)

                if ((welem.is_referenced and welem.is_current_referenced) or (welem.is_referencing and welem.is_current_referencing)) and elem_object and (max_depth is None or len(path) < max_depth) and not welem.duplicate and (
                    rf.is_none or (
                        object_id in referenced_object_ids and elem_object.action_id and rf.referenced_objects_filter(get_action(elem_object.action_id))
                    ) or (
                        object_id in referencing_object_ids and elem_object.action_id and rf.referencing_objects_filter(get_action(elem_object.action_id))
                    )
                ):
                    _handle_object(elem_object, workflow_index, path + [welem], actions_by_id, workflow_action_filters, recursion_action_filters, max_depth)

    def _get_action_filter_lists(dictionary: typing.Dict[str, typing.Any], default_filter_operator: typing.Callable[[bool, bool], bool]) -> ActionFilters:
        return ActionFilters(
            referenced_objects_filter=ActionFilter(
                action_ids=[dictionary['referenced_action_id']] if isinstance(dictionary.get('referenced_action_id'), int) else dictionary.get('referenced_action_id'),
                action_type_ids=[dictionary['referenced_action_type_id']] if isinstance(dictionary.get('referenced_action_type_id'), int) else dictionary.get('referenced_action_type_id'),
                filter_operator={'or': operator.or_, 'and': operator.and_}.get(typing.cast(str, dictionary.get('referenced_filter_operator', '')), default_filter_operator)
            ),
            referencing_objects_filter=ActionFilter(
                action_ids=[dictionary['referencing_action_id']] if isinstance(dictionary.get('referencing_action_id'), int) else dictionary.get('referencing_action_id'),
                action_type_ids=[dictionary['referencing_action_type_id']] if isinstance(dictionary.get('referencing_action_type_id'), int) else dictionary.get('referencing_action_type_id'),
                filter_operator={'or': operator.or_, 'and': operator.and_}.get(typing.cast(str, dictionary.get('referencing_filter_operator', '')), default_filter_operator)
            )
        )

    for workflow_index, workflow_view in enumerate(workflow_views):
        objects_in_workflow = {object.object_id}

        workflow_action_filters = _get_action_filter_lists(workflow_view, operator.and_)

        recursion_filters = workflow_view.get('recursion_filters')
        if recursion_filters:
            max_depth = recursion_filters.get('max_depth', None)
            recursion_action_filters = _get_action_filter_lists(recursion_filters, operator.or_)
        else:
            max_depth = 0  # No filters defined -> no recursion
            recursion_action_filters = ActionFilters()

        _handle_object(object, workflow_index, [], actions_by_id, workflow_action_filters, recursion_action_filters, max_depth)

    # sorting key to sort by datetime
    def creation_time_key(workflow_element: WorkflowElement) -> datetime.datetime:
        object_id = workflow_element.object_id
        current_object_version = objects_by_id.get(object_id)
        if current_object_version is not None and current_object_version.data is not None:
            for datetime_attribute in workflow_views[0].get('sorting_properties', []):
                if isinstance(current_object_version.data.get(datetime_attribute), dict) and current_object_version.data[datetime_attribute].get('_type') == 'datetime':
                    return datetime.datetime.strptime(current_object_version.data[datetime_attribute]['utc_datetime'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
        initital_object_version = initial_object_version_by_id.get(object_id)
        if initital_object_version is None or initital_object_version.utc_datetime is None:
            return datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
        return initital_object_version.utc_datetime

    # sort by the sorting key
    for workflow in workflows:
        workflow.sort(key=creation_time_key)

    return workflows
