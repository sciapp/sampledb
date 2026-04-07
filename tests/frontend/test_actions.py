# coding: utf-8
"""

"""

import requests
import pytest
from selenium.webdriver.common.by import By

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
    mutable_template_action_translations = sampledb.models.ActionTranslation.query.filter_by(action_id=template_action.id).all()
    for mutable_template_action_translation in mutable_template_action_translations:
        sampledb.db.session.delete(mutable_template_action_translation)
    mutable_template_action = sampledb.models.Action.query.filter_by(id=template_action.id).first()
    sampledb.db.session.delete(mutable_template_action)
    sampledb.db.session.commit()
    sampledb.logic.utils.clear_cache_functions()

    r = session.get(flask_server.base_url + f'actions/{action.id}?mode=edit')
    assert r.status_code == 400

def test_external_links(flask_server, app, driver, user):
    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    action1 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema,
        user_id=user.id
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action1.id,
        name='Action 1',
        description=''
    )
    action2 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema,
        user_id=user.id
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action2.id,
        name='Action 2',
        description=''
    )

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')

    sampledb.frontend.utils.merge_external_links.cache_clear()
    flask_server.app.config['ACTION_LINKS_BY_ACTION_ID'] = {
        '*': [
            {
                'links': [
                    {
                        'name': {'en': 'Example Link 1'},
                        'url': 'http://example.org/link1'
                    },
                    {
                        'name': {'en': 'Example Link 2'},
                        'url': 'http://example.org/link2'
                    }
                ],
                'label': {'en': 'Links'},
                'icon': 'fa-external-link',
                'id_placeholder': '<ID>'
            }
        ],
        action1.id: [
            {
                'links': [
                    {
                        'name': {'en': 'Example Link 3'},
                        'url': 'http://example.org/link3'
                    }
                ],
                'label': {'en': 'Links'},
                'icon': 'fa-external-link',
                'id_placeholder': '<ID>'
            }
        ]
    }

    driver.get(flask_server.base_url + f'actions/{action1.id}')
    external_links = driver.find_elements(By.CSS_SELECTOR, 'ul[aria-labelledby="linksDropdownMenuButton"] li a')
    assert {(external_link.get_attribute("textContent"), external_link.get_attribute('href')) for external_link in external_links} == {
        (
            'Example Link 1',
            'http://example.org/link1'
        ),
        (
            'Example Link 2',
            'http://example.org/link2'
        ),
        (
            'Example Link 3',
            'http://example.org/link3'
        ),
    }

    driver.get(flask_server.base_url + f'actions/{action2.id}')
    external_links = driver.find_elements(By.CSS_SELECTOR, 'ul[aria-labelledby="linksDropdownMenuButton"] li a')
    assert {(external_link.get_attribute("textContent"), external_link.get_attribute('href')) for external_link in external_links} == {
        (
            'Example Link 1',
            'http://example.org/link1'
        ),
        (
            'Example Link 2',
            'http://example.org/link2'
        ),
    }
    sampledb.frontend.utils.merge_external_links.cache_clear()
