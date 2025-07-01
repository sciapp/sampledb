# coding: utf-8
"""

"""


import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import none_of, visibility_of_element_located

import sampledb
import sampledb.models
import sampledb.logic


@pytest.fixture
def user(flask_server):
    return sampledb.logic.users.create_user(
        name="Basic User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )


@pytest.fixture
def actions(flask_server, instruments):
    instrument = instruments[0]
    actions = [sampledb.models.Action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            }, 'required': ['name']
        },
        instrument_id=instrument.id
    ) for i in range(2)]
    for i, action in enumerate(actions, start=1):
        sampledb.db.session.add(action)
        sampledb.db.session.commit()
        sampledb.logic.action_translations.set_action_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            action_id=action.id,
            name=f'Action {i}',
            description=''
        )
        # force attribute refresh
        assert action.id is not None
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)
    return actions


@pytest.fixture
def instruments(flask_server):
    instruments = [sampledb.models.Instrument() for i in range(2)]
    for i, instrument in enumerate(instruments, start=1):
        sampledb.db.session.add(instrument)
        sampledb.db.session.commit()
        sampledb.logic.instrument_translations.set_instrument_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            instrument_id=instrument.id,
            name=f"Instrument {i}",
            description=''
        )
        # force attribute refresh
        assert instrument.id is not None
    return instruments


def test_favorite_actions(actions, flask_server, user, driver):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    for url, heading_level in [
        (f'{flask_server.base_url}actions/', 'h2'),
        (f'{flask_server.base_url}instruments/{actions[0].instrument_id}', 'h3')
    ]:
        driver.get(url)
        action_headings = [heading for heading in driver.find_elements(By.TAG_NAME, heading_level) if heading.find_elements(By.CSS_SELECTOR, 'button[data-action-id]')]
        favorite_action_headings = []
        other_action_headings = []
        for heading in action_headings:
            if heading.find_elements(By.CLASS_NAME, 'fav-star-on'):
                favorite_action_headings.append(heading.text.split(' — ')[-1])
            else:
                other_action_headings.append(heading.text.split(' — ')[-1])
        assert favorite_action_headings == []
        assert other_action_headings == ['Action 1', 'Action 2']

        # Add favorite action
        driver.find_element(By.CSS_SELECTOR, f'button.fav-star-off[data-action-id="{actions[1].id}"]').click()
        WebDriverWait(driver, 10).until(none_of(visibility_of_element_located((By.CSS_SELECTOR, '.fav-star-loading'))))
        driver.find_element(By.CSS_SELECTOR, f'button.fav-star-on[data-action-id="{actions[1].id}"]')
        assert sampledb.logic.favorites.get_user_favorite_action_ids(user.id) == [actions[1].id]

        driver.get(url)
        action_headings = [heading for heading in driver.find_elements(By.TAG_NAME, heading_level) if heading.find_elements(By.CSS_SELECTOR, 'button[data-action-id]')]
        favorite_action_headings = []
        other_action_headings = []
        for heading in action_headings:
            if heading.find_elements(By.CLASS_NAME, 'fav-star-on'):
                favorite_action_headings.append(heading.text.split(' — ')[-1])
            else:
                other_action_headings.append(heading.text.split(' — ')[-1])
        assert favorite_action_headings == ['Action 2']
        assert other_action_headings == ['Action 1']

        # Remove favorite action
        driver.find_element(By.CSS_SELECTOR, f'button.fav-star-on[data-action-id="{actions[1].id}"]').click()
        WebDriverWait(driver, 10).until(none_of(visibility_of_element_located((By.CSS_SELECTOR, '.fav-star-loading'))))
        driver.find_element(By.CSS_SELECTOR, f'button.fav-star-off[data-action-id="{actions[1].id}"]')
        assert sampledb.logic.favorites.get_user_favorite_action_ids(user.id) == []

        driver.get(url)
        action_headings = [heading for heading in driver.find_elements(By.TAG_NAME, heading_level) if heading.find_elements(By.CSS_SELECTOR, 'button[data-action-id]')]
        favorite_action_headings = []
        other_action_headings = []
        for heading in action_headings:
            if heading.find_elements(By.CLASS_NAME, 'fav-star-on'):
                favorite_action_headings.append(heading.text.split(' — ')[-1])
            else:
                other_action_headings.append(heading.text.split(' — ')[-1])
        assert favorite_action_headings == []
        assert other_action_headings == ['Action 1', 'Action 2']


def test_favorite_instruments(instruments, flask_server, user, driver):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'instruments/')
    instrument_headings = [heading for heading in driver.find_elements(By.TAG_NAME, 'h2') if heading.find_elements(By.CSS_SELECTOR, 'button[data-instrument-id]')]
    favorite_instrument_headings = []
    other_instrument_headings = []
    for heading in instrument_headings:
        if heading.find_elements(By.CLASS_NAME, 'fav-star-on'):
            favorite_instrument_headings.append(heading.find_element(By.TAG_NAME, 'a').text)
        else:
            other_instrument_headings.append(heading.find_element(By.TAG_NAME, 'a').text)
    assert favorite_instrument_headings == []
    assert other_instrument_headings == ['Instrument 1', 'Instrument 2']

    # Add favorite instrument
    driver.find_element(By.CSS_SELECTOR, f'button.fav-star-off[data-instrument-id="{instruments[1].id}"]').click()
    WebDriverWait(driver, 10).until(none_of(visibility_of_element_located((By.CSS_SELECTOR, '.fav-star-loading'))))
    driver.find_element(By.CSS_SELECTOR, f'button.fav-star-on[data-instrument-id="{instruments[1].id}"]')
    assert sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id) == [instruments[1].id]

    driver.get(flask_server.base_url + 'instruments/')
    instrument_headings = [heading for heading in driver.find_elements(By.TAG_NAME, 'h2') if heading.find_elements(By.CSS_SELECTOR, 'button[data-instrument-id]')]
    favorite_instrument_headings = []
    other_instrument_headings = []
    for heading in instrument_headings:
        if heading.find_elements(By.CLASS_NAME, 'fav-star-on'):
            favorite_instrument_headings.append(heading.find_element(By.TAG_NAME, 'a').text)
        else:
            other_instrument_headings.append(heading.find_element(By.TAG_NAME, 'a').text)
    assert favorite_instrument_headings == ['Instrument 2']
    assert other_instrument_headings == ['Instrument 1']

    # Remove favorite instrument
    driver.find_element(By.CSS_SELECTOR, f'button.fav-star-on[data-instrument-id="{instruments[1].id}"]').click()
    WebDriverWait(driver, 10).until(none_of(visibility_of_element_located((By.CSS_SELECTOR, '.fav-star-loading'))))
    driver.find_element(By.CSS_SELECTOR, f'button.fav-star-off[data-instrument-id="{instruments[1].id}"]')
    assert sampledb.logic.favorites.get_user_favorite_instrument_ids(user.id) == []

    driver.get(flask_server.base_url + 'instruments/')
    instrument_headings = [heading for heading in driver.find_elements(By.TAG_NAME, 'h2') if heading.find_elements(By.CSS_SELECTOR, 'button[data-instrument-id]')]
    favorite_instrument_headings = []
    other_instrument_headings = []
    for heading in instrument_headings:
        if heading.find_elements(By.CLASS_NAME, 'fav-star-on'):
            favorite_instrument_headings.append(heading.find_element(By.TAG_NAME, 'a').text)
        else:
            other_instrument_headings.append(heading.find_element(By.TAG_NAME, 'a').text)
    assert favorite_instrument_headings == []
    assert other_instrument_headings == ['Instrument 1', 'Instrument 2']
