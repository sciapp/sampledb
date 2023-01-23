"""
Background Tasks

Some tasks, such as sending mails or sending HTTP requests to other servers,
may need to be performed asynchronously to prevent the frontend from being
blocked for their duration. This module allows posting tasks to be handled
in the background, as well as querying tasks to check their status or results.

Currently, background tasks need to be enabled via the ENABLE_BACKGROUND_TASKS
configuration value. If they are not enabled, tasks will be performed
synchronously instead.
"""

import sys
import threading
import traceback
import typing

import flask

from ... import db
from ...models import BackgroundTask, BackgroundTaskStatus
from .. import errors
from .background_dataverse_export import handle_dataverse_export_task
from .send_mail import handle_send_mail_task

TASK_WAIT_TIMEOUT = 30
NUM_HANDLER_THREADS = 4

HANDLERS: typing.Dict[str, typing.Callable[[typing.Dict[str, typing.Any], typing.Optional[int]], typing.Tuple[bool, typing.Optional[dict[str, typing.Any]]]]] = {
    'send_mail': handle_send_mail_task,
    'dataverse_export': handle_dataverse_export_task
}

should_stop = False
wake_event = threading.Event()

handler_threads: typing.List[threading.Thread] = []


def get_background_tasks() -> typing.Sequence[BackgroundTask]:
    return typing.cast(typing.Sequence[BackgroundTask], BackgroundTask.query.order_by(BackgroundTask.id).all())


def get_background_task(task_id: int) -> BackgroundTask:
    task: typing.Optional[BackgroundTask] = BackgroundTask.query.filter_by(id=task_id).first()
    if task is None:
        raise errors.BackgroundTaskDoesNotExistError()
    return task


def post_background_task(
        type: str,
        data: typing.Dict[str, typing.Any],
        auto_delete: bool = True
) -> typing.Tuple[BackgroundTaskStatus, typing.Optional[BackgroundTask]]:
    """
    Create a background task and post it to be performed.

    If background tasks are disabled, the task will be performed synchronously
    instead and no BackgroundTask object will be returned. If a task does not
    have the auto_delete flag set, its ID should be stored so that the result
    can be queried later and so that it can be deleted.

    :param type: the type of the task
    :param data: data for the task
    :param auto_delete: whether the task should be deleted automatically, once
        it is done or has failed
    :return: the task status and the task object itself
    """
    if flask.current_app.config['ENABLE_BACKGROUND_TASKS']:
        task = BackgroundTask(
            type=type,
            auto_delete=auto_delete,
            data=data,
            status=BackgroundTaskStatus.POSTED
        )
        db.session.add(task)
        db.session.commit()
        wake_event.set()
        start_handler_threads(flask.current_app)
        return BackgroundTaskStatus.POSTED, task
    else:
        return _handle_background_task(type, data, None), None


def start_handler_threads(app: flask.Flask) -> None:
    """
    Start handler threads for background tasks.

    This function first cleans up all dead threads, then creates and starts
    handler threads until the desired number of handler threads has been
    reached.

    If background tasks are disabled, this function returns immediately.
    """
    if not app.config['ENABLE_BACKGROUND_TASKS']:
        return

    # remove handler threads that might have died
    for handler_thread in handler_threads.copy():
        if not handler_thread.is_alive():
            handler_threads.remove(handler_thread)

    # get actual app instead of thread local proxy from this thread to pass it to the new thread
    get_current_app = getattr(app, '_get_current_object', None)
    if get_current_app is not None:
        app = get_current_app()
    # use daemon threads during testing, as a failed test may circumvent the thread stop signal
    daemon = app.config.get('TESTING', False)
    while len(handler_threads) < NUM_HANDLER_THREADS:
        handler_thread = threading.Thread(target=_handle_background_tasks, args=[app, len(handler_threads) == 0], daemon=daemon)
        handler_thread.start()
        handler_threads.append(handler_thread)


def stop_handler_threads(app: flask.Flask) -> None:
    """
    Stop handler threads for background tasks.

    This function signals to the handle threads that they should stop
    processing tasks, then waits for them to finish before returning. If one
    of the handler threads blocks, this function will block as well.

    If background tasks are disabled, this function returns immediately.
    """
    if not app.config['ENABLE_BACKGROUND_TASKS']:
        return

    global should_stop
    should_stop = True

    # notify handler threads about having to stop
    wake_event.set()

    # then join handler threads
    # this is tried repeatedly, so that even if one thread is blocking, all others will be joined correctly
    running_threads = set(handler_threads)
    while running_threads:
        for handler_thread in running_threads.copy():
            handler_thread.join(1)
            if not handler_thread.is_alive():
                running_threads.remove(handler_thread)


def get_background_task_result(task_id: int, delete_when_final: bool = True) -> typing.Optional[dict[str, typing.Any]]:
    """
    Returns the result of a task.

    Creates a short evaluation of the specified task by returning the
    status and result as a dict. if specified, it also deletes
    the background task from the database.

    :param task_id: the id of the task
    :param delete_when_final: if true, the task will be deleted if it is in an final state (done/failed)
    :return: returns the status and the result of an background task as a dictionary
    """
    task: BackgroundTask = BackgroundTask.query.filter_by(id=task_id).first()
    if not task:
        return None

    result = {"status": task.status, "result": ""}

    if task.status.is_final():
        if task.type == 'dataverse_export':
            result["result"] = task.result["url" if task.status == BackgroundTaskStatus.DONE else "error_message"]

        if delete_when_final:
            db.session.delete(task)
            db.session.commit()

    return result


def _handle_background_tasks(app: flask.Flask, should_delete_expired_tasks: bool) -> None:
    with app.app_context():
        while not should_stop:
            if should_delete_expired_tasks:
                BackgroundTask.delete_expired_tasks()
            try:
                task = BackgroundTask.query.filter_by(status=BackgroundTaskStatus.POSTED).first()
            except Exception:
                # database might be unavailable for the moment, so no task to work on
                task = None
            if task is not None:
                if _claim_background_task(task):
                    _set_background_task_status(task, _handle_background_task(task.type, task.data, task.id))
                else:
                    # another thread might have claimed the task first
                    continue
            else:
                wake_event.clear()
                wake_event.wait(TASK_WAIT_TIMEOUT)


def _claim_background_task(
        task: BackgroundTask
) -> bool:
    try:
        stmt = (
            db.update(
                BackgroundTask
            ).where(
                BackgroundTask.id == task.id,
                BackgroundTask.status == BackgroundTaskStatus.POSTED
            ).values(
                status=BackgroundTaskStatus.CLAIMED
            )
        )
        updated_rowcount = db.session.execute(stmt).rowcount
        db.session.commit()
        return bool(updated_rowcount == 1)
    except Exception:
        # database might be temporarily unavailable, assume task was not claimed
        return False


def _handle_background_task(
        type: str,
        data: typing.Dict[str, typing.Any],
        task_id: typing.Optional[int]
) -> BackgroundTaskStatus:
    handler = HANDLERS.get(type)
    try:
        if handler is not None and handler(data, task_id)[0]:
            return BackgroundTaskStatus.DONE
    except Exception:
        print("Exception during handler for task:\n", traceback.format_exc(), file=sys.stderr)
    return BackgroundTaskStatus.FAILED


def _set_background_task_status(
        task: BackgroundTask,
        task_status: BackgroundTaskStatus
) -> None:
    try:
        task.status = task_status
        if task_status.is_final() and task.auto_delete:
            db.session.delete(task)
        else:
            db.session.add(task)
        db.session.commit()
    except Exception:
        # task status could not be updated, no way to recover?
        pass
