# coding: utf-8
"""

"""
from datetime import datetime

import flask
import pytest
import sampledb
import sampledb.logic
import sampledb.models
from sampledb.logic import webhooks, errors, actions, objects
from sampledb.models.webhooks import WebhookType


@pytest.fixture
def user1():
    user = sampledb.logic.users.create_user(name="User 1", email="example1@example.com", type=sampledb.models.UserType.PERSON)
    assert user.id is not None
    return user


@pytest.fixture
def user2():
    user = sampledb.logic.users.create_user(name="User 2", email="example2@example.com", type=sampledb.models.UserType.PERSON)
    assert user.id is not None
    return user


@pytest.fixture
def action():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Sample Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        },
        instrument_id=None
    )
    return action


@pytest.fixture
def object(user1, action):
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    return objects.create_object(user_id=user1.id, action_id=action.id, data=data)


def test_create_webhook(user1, user2):
    assert len(webhooks.get_webhooks()) == 0
    webhook = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, target_url='https://example.com', name='Webhook 1')
    assert webhook.type == WebhookType.OBJECT_LOG
    assert webhook.user_id == user1.id
    assert webhook.name == 'Webhook 1'
    assert webhook.target_url == 'https://example.com'
    assert webhook.last_contact is None
    assert len(webhook.secret) == 64
    assert len(webhooks.get_webhooks()) == 1
    webhook_2 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user2.id, secret='secret_value', target_url='https://example.com')
    assert webhook_2.secret == 'secret_value'
    assert len(webhooks.get_webhooks()) == 2
    webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, target_url='https://127.0.0.1:8080')
    assert len(webhooks.get_webhooks()) == 3
    webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, target_url='https://127.0.0.1')
    assert len(webhooks.get_webhooks()) == 4
    with pytest.raises(errors.UserDoesNotExistError):
        webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user2.id + 1, target_url='https://example.com')
    with pytest.raises(errors.InvalidComponentAddressError):
        webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, target_url='ftp://example.com')
    with pytest.raises(errors.InvalidComponentAddressError):
        webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, target_url='/example.com')
    with pytest.raises(errors.WebhookAlreadyExistsError):
        webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, target_url='https://example.com')
    with pytest.raises(errors.InsecureComponentAddressError):
        webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, target_url='http://example.com')
    flask.current_app.config['WEBHOOKS_ALLOW_HTTP'] = True
    webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, target_url='http://example.com')


def test_get_webhooks(user1, user2):
    assert len(webhooks.get_webhooks()) == 0
    wh1 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, secret='This is a secret', target_url='https://example.com')
    wh2 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user2.id, target_url='https://example.com')
    wh3 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user2.id, target_url='https://example2.com')
    assert webhooks.get_webhooks() == [wh1, wh2, wh3]
    assert webhooks.get_webhooks(type=WebhookType.OBJECT_LOG) == [wh1, wh2, wh3]
    assert webhooks.get_webhooks(user_id=user1.id) == [wh1]
    assert webhooks.get_webhooks(user_id=user2.id) == [wh2, wh3]
    assert webhooks.get_webhooks(type=WebhookType.OBJECT_LOG, user_id=user2.id) == [wh2, wh3]


def test_get_object_log_webhooks_for_object(user1, user2, object, action):
    wh1 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, target_url='https://example.com')
    wh2 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, target_url='https://example2.com')
    wh3 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user2.id, target_url='https://example.com')
    wh4 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user2.id, secret='This is a secret', target_url='https://example2.com')
    webhooks_for_object = webhooks.get_object_log_webhooks_for_object(object.id)
    assert webhooks_for_object == [wh1, wh2]
    sampledb.logic.object_permissions.set_object_permissions_for_all_users(object.id, sampledb.models.Permissions.READ)
    webhooks_for_object = webhooks.get_object_log_webhooks_for_object(object.id)
    sampledb.logic.object_permissions.set_object_permissions_for_all_users(object.id, sampledb.models.Permissions.NONE)
    assert webhooks_for_object == [wh1, wh2, wh3, wh4]
    sampledb.logic.users.set_user_administrator(user2.id, True)
    webhooks_for_object = webhooks.get_object_log_webhooks_for_object(object.id)
    assert webhooks_for_object == [wh1, wh2]
    sampledb.logic.settings.set_user_settings(user2.id, {'USE_ADMIN_PERMISSIONS': True})
    webhooks_for_object = webhooks.get_object_log_webhooks_for_object(object.id)
    assert webhooks_for_object == [wh1, wh2, wh3, wh4]


def test_update_webhook(user1):
    assert len(webhooks.get_webhooks()) == 0
    wh1 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, secret='This is a secret', target_url='https://example.com')
    assert len(webhooks.get_webhooks()) == 1
    ts = datetime.utcnow()
    webhooks.update_webhook(wh1.id, ts)
    wh1_u = webhooks.get_webhook(wh1.id)
    assert len(webhooks.get_webhooks()) == 1
    assert wh1_u.last_contact == ts
    assert wh1_u.id == wh1.id
    assert wh1_u.target_url == wh1.target_url
    assert wh1_u.secret == wh1.secret
    assert wh1_u.user_id == wh1.user_id
    with pytest.raises(errors.WebhookDoesNotExistError):
        webhooks.update_webhook(wh1.id + 1, ts)


def test_get_webhook(user1, user2):
    assert len(webhooks.get_webhooks()) == 0
    wh1 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, secret='This is a secret', target_url='https://example.com')
    wh2 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user2.id, target_url='https://example.com')
    assert webhooks.get_webhook(wh1.id) == wh1
    assert webhooks.get_webhook(wh2.id) == wh2
    with pytest.raises(errors.WebhookDoesNotExistError):
        webhooks.get_webhook(wh2.id + 1)


def test_remove_webhook(user1, user2):
    assert len(webhooks.get_webhooks()) == 0
    wh1 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user1.id, secret='This is a secret', target_url='https://example.com')
    wh2 = webhooks.create_webhook(type=WebhookType.OBJECT_LOG, user_id=user2.id, target_url='https://example.com')
    assert len(webhooks.get_webhooks()) == 2
    assert webhooks.get_webhooks() == [wh1, wh2]
    webhooks.remove_webhook(wh2.id)
    assert len(webhooks.get_webhooks()) == 1
    assert webhooks.get_webhooks() == [wh1]
    with pytest.raises(errors.WebhookDoesNotExistError):
        webhooks.get_webhook(wh2.id)
    with pytest.raises(errors.WebhookDoesNotExistError):
        webhooks.remove_webhook(wh2.id + 1)
