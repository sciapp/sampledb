import typing

import flask

from ... import db, logic
from . import core
from ...models import BackgroundTask, BackgroundTaskStatus, UpdatableObjectsCheckStatus, AutomaticSchemaUpdateStatus, Objects
from ..automatic_schema_updates import get_updatable_objects_check, set_updatable_objects_check_status, get_automatic_schema_update, set_automatic_schema_update_status


def post_check_for_automatic_schema_updates_task(
        *,
        updatable_objects_check_id: int
) -> typing.Tuple[BackgroundTaskStatus, typing.Optional[BackgroundTask]]:
    return core.post_background_task(
        type='check_for_automatic_schema_updates',
        data={
            'updatable_objects_check_id': updatable_objects_check_id
        },
        auto_delete=False
    )


def post_perform_automatic_schema_updates_task(
        automatic_schema_update_id: int,
        auto_delete: bool = True
) -> typing.Tuple[BackgroundTaskStatus, typing.Optional[BackgroundTask]]:
    return core.post_background_task(
        type='perform_automatic_schema_updates',
        data={
            'automatic_schema_update_id': automatic_schema_update_id,
        },
        auto_delete=auto_delete
    )


def handle_check_for_automatic_schema_updates_task(
        data: typing.Dict[str, typing.Any],
        task_id: typing.Optional[int]
) -> typing.Tuple[bool, typing.Optional[dict[str, typing.Any]]]:
    updatable_objects_check_id = typing.cast(int, data['updatable_objects_check_id'])
    updatable_objects_check = get_updatable_objects_check(updatable_objects_check_id)
    previous_object_id = -1
    automatically_updatable_objects = []
    manually_updatable_objects = []
    if updatable_objects_check.status == UpdatableObjectsCheckStatus.POSTED:
        set_updatable_objects_check_status(
            updatable_objects_check_id=updatable_objects_check_id,
            status=UpdatableObjectsCheckStatus.IN_PROGRESS,
            result={
                'previous_object_id': previous_object_id,
                'automatically_updatable_objects': [],
                'manually_updatable_objects': [],
            }
        )
    elif updatable_objects_check.status == UpdatableObjectsCheckStatus.IN_PROGRESS:
        if updatable_objects_check.result:
            previous_object_id = updatable_objects_check.result.get('previous_object_id', -1)
            automatically_updatable_objects = updatable_objects_check.result.get('automatically_updatable_objects', [])
            manually_updatable_objects = updatable_objects_check.result.get('manually_updatable_objects', [])
    else:
        return True, None
    num_objects_to_handle = 100 if flask.current_app.config['ENABLE_BACKGROUND_TASKS'] else None
    num_objects_found_list = [0]

    objects = logic.objects.get_objects(
        filter_func=lambda data: db.and_(
            db.and_(
                Objects.current_table.c.action_id.in_(updatable_objects_check.action_ids) if updatable_objects_check.action_ids else db.true(),
                Objects.current_table.c.object_id > previous_object_id,
            ),
            db.and_(
                Objects.current_table.c.fed_object_id == db.null(),
                Objects.current_table.c.eln_object_id == db.null()
            )
        ),
        sorting_func=lambda current_columns, original_columns: db.sql.asc(current_columns.object_id),
        limit=num_objects_to_handle,
        num_objects_found=num_objects_found_list,
    )
    cached_actions = {}
    for object in objects:
        if object.data is None:
            continue
        if object.schema is None:
            continue
        if object.action_id is None:
            continue
        if object.action_id not in cached_actions:
            cached_actions[object.action_id] = logic.actions.get_action(action_id=object.action_id)
        action = cached_actions[object.action_id]
        if action.schema is None:
            continue
        if action.schema != object.schema:
            converting_necessary, messages = logic.schemas.is_converting_to_schema_necessary(object.data, object.schema, action.schema)
            if converting_necessary:
                manually_updatable_objects.append((object.object_id, object.version_id, messages))
            else:
                automatically_updatable_objects.append((object.object_id, object.version_id, messages))
    num_objects_found = num_objects_found_list[0]
    set_updatable_objects_check_status(
        updatable_objects_check_id=updatable_objects_check_id,
        status=UpdatableObjectsCheckStatus.IN_PROGRESS if num_objects_to_handle and num_objects_found > num_objects_to_handle else UpdatableObjectsCheckStatus.DONE,
        result={
            'previous_object_id': max(
                object.object_id
                for object in objects
            ),
            'automatically_updatable_objects': automatically_updatable_objects,
            'manually_updatable_objects': manually_updatable_objects
        }
    )
    if num_objects_to_handle and num_objects_found > num_objects_to_handle:
        post_check_for_automatic_schema_updates_task(
            updatable_objects_check_id=updatable_objects_check_id
        )
    return True, None


def handle_perform_automatic_schema_updates_task(
        data: typing.Dict[str, typing.Any],
        task_id: typing.Optional[int]
) -> typing.Tuple[bool, typing.Optional[dict[str, typing.Any]]]:
    automatic_schema_update_id = typing.cast(int, data['automatic_schema_update_id'])
    automatic_schema_update = get_automatic_schema_update(automatic_schema_update_id=automatic_schema_update_id)
    object_ids = automatic_schema_update.object_ids
    object_ids_success: typing.List[int] = []
    object_ids_failure: typing.List[int] = []
    if automatic_schema_update.status == AutomaticSchemaUpdateStatus.POSTED:
        set_automatic_schema_update_status(
            automatic_schema_update_id=automatic_schema_update_id,
            status=AutomaticSchemaUpdateStatus.IN_PROGRESS,
            result={
                'object_ids_success': object_ids_success,
                'object_ids_failure': object_ids_failure,
            }
        )
    elif automatic_schema_update.status == AutomaticSchemaUpdateStatus.IN_PROGRESS:
        if automatic_schema_update.result:
            object_ids_success = automatic_schema_update.result.get('object_ids_success', object_ids_success)
            object_ids_failure = automatic_schema_update.result.get('object_ids_failure', object_ids_failure)
    else:
        return True, None

    if object_ids_success or object_ids_failure:
        object_ids = [
            object_id
            for object_id in object_ids
            if object_id not in object_ids_success and object_id not in object_ids_failure
        ]
    if not object_ids:
        set_automatic_schema_update_status(
            automatic_schema_update_id=automatic_schema_update_id,
            status=AutomaticSchemaUpdateStatus.DONE,
            result=automatic_schema_update.result,
        )
        return True, None
    num_objects_to_handle = 100 if flask.current_app.config['ENABLE_BACKGROUND_TASKS'] else None

    if num_objects_to_handle is None:
        unhandled_object_ids = []
    else:
        unhandled_object_ids = object_ids[num_objects_to_handle:]
        object_ids = object_ids[:num_objects_to_handle]
    objects = logic.objects.get_objects(
        filter_func=lambda data: db.and_(
            Objects.current_table.c.object_id.in_(object_ids),
            db.and_(
                Objects.current_table.c.fed_object_id == db.null(),
                Objects.current_table.c.eln_object_id == db.null()
            )
        ),
        sorting_func=lambda current_columns, original_columns: db.sql.asc(current_columns.object_id),
    )
    cached_actions = {}
    for object in objects:
        if object.data is None:
            object_ids_failure.append(object.object_id)
            continue
        if object.schema is None:
            object_ids_failure.append(object.object_id)
            continue
        if object.action_id is None:
            object_ids_failure.append(object.object_id)
            continue
        if object.action_id not in cached_actions:
            cached_actions[object.action_id] = logic.actions.get_action(action_id=object.action_id)
        action = cached_actions[object.action_id]
        if action.schema is None:
            object_ids_failure.append(object.object_id)
            continue
        if action.schema != object.schema:
            converting_to_schema_necessary, conversion_messages = logic.schemas.is_converting_to_schema_necessary(object.data, object.schema, action.schema)
            if converting_to_schema_necessary or conversion_messages:
                object_ids_failure.append(object.object_id)
                continue
            try:
                logic.objects.update_object(
                    object_id=object.object_id,
                    data=object.data,
                    schema=action.schema,
                    user_id=automatic_schema_update.user_id,
                )
                object_ids_success.append(object.object_id)
            except Exception:
                object_ids_failure.append(object.object_id)
    set_automatic_schema_update_status(
        automatic_schema_update_id=automatic_schema_update_id,
        status=AutomaticSchemaUpdateStatus.IN_PROGRESS if unhandled_object_ids else AutomaticSchemaUpdateStatus.DONE,
        result={
            'object_ids_success': object_ids_success,
            'object_ids_failure': object_ids_failure
        }
    )
    if unhandled_object_ids:
        post_perform_automatic_schema_updates_task(
            automatic_schema_update_id=automatic_schema_update_id
        )
    return True, None
