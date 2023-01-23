import sampledb.logic.background_tasks
import sampledb.logic.background_tasks.core
import time


def test_background_tasks(app):
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
    time.sleep(0.1)
    task = sampledb.logic.background_tasks.core.get_background_task(task.id)
    assert task.status == sampledb.logic.background_tasks.core.BackgroundTaskStatus.DONE
    assert handler_call_args == [
        {'value': 1},
        {'value': 2},
        {'value': 3}
    ]

    # other tests should proceed with background tasks off, but that way the
    # handler threads would not be stopped later on, so they need to be
    # stopped now
    sampledb.logic.background_tasks.stop_handler_threads(app)
    app.config['ENABLE_BACKGROUND_TASKS'] = False
