# coding: utf-8
"""
Logic module for webhooks

Webhooks allow users to subscribe to the creation of new object log entries.
"""

import dataclasses
import datetime
import hashlib
import hmac
import json
import secrets
import typing

import flask
import requests

from . import errors
from .components import validate_address
from .users import check_user_exists
from .. import db
from ..models import webhooks as whmodel

WEBHOOK_TIMEOUT = 10


@dataclasses.dataclass(frozen=True)
class Webhook:
    """
    This class provides an immutable wrapper around models.webhooks.Webhook.
    """
    id: int
    user_id: int
    type: whmodel.WebhookType
    target_url: str
    secret: str
    name: typing.Optional[str]
    last_contact: typing.Optional[datetime.datetime]

    @classmethod
    def from_database(cls, webhook: whmodel.Webhook) -> 'Webhook':
        return Webhook(
            id=webhook.id,
            user_id=webhook.user_id,
            type=webhook.type,
            target_url=webhook.target_url,
            name=webhook.name,
            secret=webhook.secret,
            last_contact=webhook.last_contact
        )

    def send_data(self, data: typing.Dict[str, typing.Any]) -> None:
        data_str = json.dumps(data)
        headers = {
            'X-SampleDB-Event-Type': str(self.type.name),
            'X-Sampledb-Signature': self.get_signature(data_str)
        }
        try:
            requests.post(
                self.target_url,
                data=data_str,
                timeout=WEBHOOK_TIMEOUT,
                headers=headers
            )
            update_webhook(self.id, datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None))
        except requests.RequestException:
            raise errors.WebhookConnectionException()

    def get_signature(self, data: str) -> str:
        hash_object = hmac.new(self.secret.encode('utf-8'), msg=data.encode('utf-8'), digestmod=hashlib.sha256)
        return "sha256=" + hash_object.hexdigest()


def _get_mutable_webhook(webhook_id: int) -> whmodel.Webhook:
    webhook = whmodel.Webhook.query.filter_by(id=webhook_id).first()
    if webhook is None:
        raise errors.WebhookDoesNotExistError()
    return webhook


def get_webhook(webhook_id: int) -> Webhook:
    """
    Returns the webhooks matching the given webhook ID.

    :param webhook_id: The ID of the Webhook to get
    :return: The Webhook with the given ID
    :raise WebhookDoesNotExistError: If a Webhook with the given ID does not exist
    """
    return Webhook.from_database(_get_mutable_webhook(webhook_id))


def get_webhooks(type: typing.Optional[whmodel.WebhookType] = None, user_id: typing.Optional[int] = None) -> typing.List[Webhook]:
    """
    Returns all webhooks matching the (optionally) given webhook type and user ID.

    :param type: Webhook types to return
    :param user_id: The ID of the user who registered the webhooks
    :return: A list of Webhooks
    """
    webhooks_q = whmodel.Webhook.query
    if user_id:
        check_user_exists(user_id)
        webhooks_q = webhooks_q.filter_by(user_id=user_id)
    if type:
        webhooks_q = webhooks_q.filter_by(type=type)
    webhooks = webhooks_q.order_by(whmodel.Webhook.id).all()
    return [
        Webhook.from_database(webhook)
        for webhook in webhooks
    ]


def update_webhook(webhook_id: int, last_contact: datetime.datetime) -> None:
    """
    Updates a Webhook.

    :param webhook_id: ID of the Webhook to update
    :param last_contact: Last contact with this webhook'S target
    :raise WebhookDoesNotExistError: If a Webhook with the given ID does not exist
    """
    webhook = _get_mutable_webhook(webhook_id)
    webhook.last_contact = last_contact
    db.session.add(webhook)
    db.session.commit()


def remove_webhook(webhook_id: int) -> None:
    """
    Removes a webhook

    :param webhook_id: The ID of the Webhook to remove
    :raise WebhookDoesNotExistError: If a Webhook with the given ID does not exist
    """
    webhook = _get_mutable_webhook(webhook_id)
    db.session.delete(webhook)
    db.session.commit()


def create_webhook(
    type: whmodel.WebhookType,
    user_id: int,
    target_url: str,
    secret: typing.Optional[str] = None,
    name: typing.Optional[str] = None
) -> Webhook:
    """
    Creates/registers a new webhook.

    :param type: Type of the new Webhook
    :param user_id: ID of the user to register the Webhook for
    :param target_url: The Webhook's target URL
    :param name: An optional name for the Webhook
    :param secret: An optional secret for the Webhook
    :return: The created webhook
    :raise WebhookAlreadyExistsError: If a WebHook of same type with the same target defined by the same user already exists
    """
    check_user_exists(user_id)
    target_url = validate_address(target_url, allow_http=flask.current_app.config['WEBHOOKS_ALLOW_HTTP'])
    if db.session.query(db.exists().where(whmodel.Webhook.user_id == user_id, whmodel.Webhook.type == type, whmodel.Webhook.target_url == target_url)).scalar():
        raise errors.WebhookAlreadyExistsError()
    if secret is None:
        secret = secrets.token_hex(32)
    webhook = whmodel.Webhook(
        user_id=user_id,
        type=type,
        target_url=target_url,
        secret=secret,
        name=name,
        last_contact=None
    )
    db.session.add(webhook)
    db.session.commit()
    return Webhook.from_database(webhook)


def get_object_log_webhooks_for_object(object_id: int) -> typing.List[Webhook]:
    stmt = db.text("""
        SELECT DISTINCT user_id
        FROM (
            SELECT DISTINCT user_id
            FROM user_object_permissions_by_all
            WHERE (object_id = :object_id) AND (requires_anonymous_users IS FALSE OR :enable_anonymous_users IS TRUE) AND (requires_instruments IS FALSE OR :enable_instruments IS TRUE)
            UNION
            SELECT id as user_id
            FROM users
            JOIN settings ON settings.user_id = users.id
            WHERE users.is_admin = TRUE AND settings.data ->> 'USE_ADMIN_PERMISSIONS' = 'true'
        ) as users_with_access_dupl
    """).columns(db.column('user_id')).subquery('users_with_access')
    stmt = db.select(whmodel.Webhook).distinct().join(stmt, db.or_(stmt.c.user_id.is_(None), whmodel.Webhook.user_id == stmt.c.user_id)).order_by(whmodel.Webhook.id)
    webhooks = db.session.execute(stmt, {
        'object_id': object_id,
        'enable_anonymous_users': flask.current_app.config['ENABLE_ANONYMOUS_USERS'],
        'enable_instruments': not flask.current_app.config['DISABLE_INSTRUMENTS']
    }).all()
    return [Webhook.from_database(row[0]) for row in webhooks]
