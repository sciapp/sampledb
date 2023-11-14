import typing

import flask

from . import core
from .. import errors
from ... import logic
from ...models import ObjectLogEntry


def post_trigger_object_log_webhooks(
    object_log_entry: ObjectLogEntry
) -> None:
    if flask.current_app.config["ENABLE_BACKGROUND_TASKS"]:
        core.post_background_task(
            type='trigger_object_log_webhooks',
            data={'object_log_entry_id': object_log_entry.id, 'object_id': object_log_entry.object_id},
            auto_delete=True
        )
    else:
        handle_trigger_object_log_webhooks({'object_log_entry_id': object_log_entry.id, 'object_id': object_log_entry.object_id}, None)


def post_webhook_send(
    data: typing.Dict[str, typing.Any],
    webhook_id: int
) -> None:
    if flask.current_app.config["ENABLE_BACKGROUND_TASKS"]:
        core.post_background_task(
            type='webhook_send',
            data={'webhook_id': webhook_id, 'data': data},
            auto_delete=True
        )
    else:
        handle_webhook_send({'webhook_id': webhook_id, 'data': data}, None)


def handle_trigger_object_log_webhooks(
    data: typing.Dict[str, typing.Any],
    task_id: typing.Optional[int]
) -> typing.Tuple[bool, typing.Optional[dict[str, typing.Any]]]:
    webhooks = logic.webhooks.get_object_log_webhooks_for_object(data['object_id'])
    for webhook in webhooks:
        user = logic.users.get_user(webhook.user_id)
        if flask.current_app.config['ENABLE_WEBHOOKS_FOR_USERS'] or user.is_admin:
            object_log_entry = logic.object_log.get_object_log_entry(data['object_log_entry_id'], webhook.user_id)
            object_log_entry_json = logic.object_log.object_log_entry_to_json(object_log_entry)
            post_webhook_send(object_log_entry_json, webhook.id)

    return True, {}


def handle_webhook_send(
    data: typing.Dict[str, typing.Any],
    task_id: typing.Optional[int]
) -> typing.Tuple[bool, typing.Optional[dict[str, typing.Any]]]:
    try:
        webhook = logic.webhooks.get_webhook(data['webhook_id'])
        webhook.send_data(data['data'])
    except errors.WebhookConnectionException:
        return False, {}
    return True, {}
