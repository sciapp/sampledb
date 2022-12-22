# coding: utf-8
"""

"""

import requests
import pytest

import sampledb
import sampledb.models
import sampledb.logic

from sampledb.models import User, Action


@pytest.fixture
def user(flask_server):
    return sampledb.logic.users.create_user(
        name="Basic User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )


def test_edit_action_using_template(flask_server, user: User):
    template_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.TEMPLATE,
        schema={
            'title': 'Example Template',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'test': {
                    'title': 'Test',
                    'type': 'text'
                }
            },
            'required': ['name']
        },
        user_id=user.id
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=template_action.id,
        name='Example Template',
        description=''
    )

    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.TEMPLATE,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'test': {
                    'title': 'Test',
                    'type': 'object',
                    'template': template_action.id
                }
            },
            'required': ['name']
        },
        user_id=user.id
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
    )

    session = requests.session()
    assert session.get(flask_server.base_url + f'users/{user.id}/autologin').status_code == 200
    r = session.get(flask_server.base_url + f'actions/{action.id}?mode=edit')
    assert r.status_code == 200

    # simulate a template action not existing, e.g. if action was imported
    # via federation but the template action was not
    mutable_template_action = sampledb.models.Action.query.filter_by(id=template_action.id).first()
    sampledb.db.session.delete(mutable_template_action)
    sampledb.db.session.commit()
    sampledb.logic.utils.clear_cache_functions()

    r = session.get(flask_server.base_url + f'actions/{action.id}?mode=edit')
    assert r.status_code == 400
