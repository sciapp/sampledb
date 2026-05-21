from sampledb import db
import sampledb.logic.background_tasks
import sampledb.logic.background_tasks.core
import time

from ..conftest import wait_for_background_task


def test_background_tasks(app, enable_background_tasks):
    handler_call_args = []
    def test_handler(data, task_id):
        handler_call_args.append(data)
        return handler_return_value, None

    app.config['ENABLE_BACKGROUND_TASKS'] = False

    sampledb.logic.background_tasks.core.HANDLERS['test'] = test_handler
    handler_return_value = True
    task_status, task = sampledb.logic.background_tasks.post_background_task('test', {'value': 1}, False)
    assert task_status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.DONE
    assert task is None
    assert handler_call_args == [
        {'value': 1}
    ]

    handler_return_value = False
    task_status, task = sampledb.logic.background_tasks.post_background_task('test', {'value': 2}, False)
    assert task_status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.FAILED
    assert task is None
    assert handler_call_args == [
        {'value': 1},
        {'value': 2}
    ]

    app.config['ENABLE_BACKGROUND_TASKS'] = True

    handler_return_value = True
    task_status, task = sampledb.logic.background_tasks.post_background_task('test', {'value': 3}, False)
    assert task_status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.POSTED
    assert task is not None
    # give the background task time to be processed
    wait_for_background_task(task)
    assert task.status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.DONE
    assert handler_call_args == [
        {'value': 1},
        {'value': 2},
        {'value': 3}
    ]


def test_background_tasks_result_success(enable_background_tasks):
    def test_handler_success(data, task_id):
        return True, {'result': 'success'}

    sampledb.logic.background_tasks.core.HANDLERS['test'] = test_handler_success

    task_status, task = sampledb.logic.background_tasks.post_background_task('test', {}, False)
    assert task_status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.POSTED
    assert task is not None

    wait_for_background_task(task)

    assert task.status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.DONE
    assert task.result == {'result': 'success'}


def test_background_tasks_result_failed(enable_background_tasks):
    def test_handler_fails(data, task_id):
        return False, {'result': 'failed'}

    sampledb.logic.background_tasks.core.HANDLERS['test'] = test_handler_fails

    task_status, task = sampledb.logic.background_tasks.post_background_task('test', {'value': 1}, False)
    assert task_status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.POSTED
    assert task is not None

    wait_for_background_task(task)

    assert task.status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.FAILED
    assert task.result == {'result': 'failed'}


def test_background_tasks_result_exception(enable_background_tasks):
    def test_handler_exception(data, task_id):
        raise Exception('test exception')

    sampledb.logic.background_tasks.core.HANDLERS['test'] = test_handler_exception

    task_status, task = sampledb.logic.background_tasks.post_background_task('test', {'value': 1}, False)
    assert task_status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.POSTED
    assert task is not None

    wait_for_background_task(task)

    assert task.status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.FAILED
    assert task.result is None


def test_reset_claimed_background_tasks(app):
    posted_task = sampledb.models.BackgroundTask(
        type='test',
        auto_delete=False,
        data={},
        status=sampledb.models.BackgroundTaskStatus.POSTED
    )
    claimed_task = sampledb.models.BackgroundTask(
        type='test',
        auto_delete=False,
        data={},
        status=sampledb.models.BackgroundTaskStatus.CLAIMED
    )
    done_task = sampledb.models.BackgroundTask(
        type='test',
        auto_delete=False,
        data={},
        status=sampledb.models.BackgroundTaskStatus.DONE
    )
    db.session.add_all([posted_task, claimed_task, done_task])
    db.session.commit()

    sampledb.logic.background_tasks.reset_claimed_background_tasks()

    assert posted_task.status == sampledb.models.BackgroundTaskStatus.POSTED
    assert claimed_task.status == sampledb.models.BackgroundTaskStatus.POSTED
    assert done_task.status == sampledb.models.BackgroundTaskStatus.DONE
