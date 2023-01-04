import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from urllib.parse import urlparse, parse_qs

import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def _element_stopped_moving(element, element_locations):
    previous_element_location = element_locations.get(element)
    element_locations[element] = element.location
    return element.location == previous_element_location


def test_object_list_filters_settings(flask_server, driver, user):
    user_settings = sampledb.logic.settings.get_user_settings(user.id)
    assert user_settings['DEFAULT_OBJECT_LIST_FILTERS'] == {}

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.XPATH, '//button[contains(text(), "Filters")]').click()

    filters_modal = driver.find_element(By.ID, 'filtersModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: _element_stopped_moving(filters_modal, element_locations))

    filters_modal.find_element(By.CSS_SELECTOR, '[data-id="filter_permissions"]').click()
    filters_modal.find_element(By.XPATH, '//select[@id="filter_permissions"]/parent::div/descendant::span[contains(text(), "Write")]').click()

    filters_modal.find_element(By.CLASS_NAME, 'btn-primary').click()

    user_settings = sampledb.logic.settings.get_user_settings(user.id)
    assert user_settings['DEFAULT_OBJECT_LIST_FILTERS'] == {}

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['user'] == [str(user.id)]
    assert query_params['user_permissions'] == ['write']

    driver.find_element(By.XPATH, '//button[contains(text(), "Filters")]').click()

    filters_modal = driver.find_element(By.ID, 'filtersModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: _element_stopped_moving(filters_modal, element_locations))

    filters_modal.find_element(By.XPATH, '//div[@id="filtersModal"]/descendant::button[contains(text(), "Save")]').click()

    user_settings = sampledb.logic.settings.get_user_settings(user.id)
    assert user_settings['DEFAULT_OBJECT_LIST_FILTERS'] == {
        'filter_location_ids': None,
        'filter_action_type_ids': None,
        'filter_action_ids': None,
        'filter_doi': None,
        'filter_origin_ids': None,
        'filter_anonymous_permissions': None,
        'filter_all_users_permissions': None,
        'filter_user_id': user.id,
        'filter_user_permissions': 'write',
    }

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert 'user' not in query_params
    assert 'user_permissions' not in query_params

    driver.find_element(By.XPATH, '//button[contains(text(), "Filters")]').click()

    filters_modal = driver.find_element(By.ID, 'filtersModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: _element_stopped_moving(filters_modal, element_locations))

    filters_modal.find_element(By.CLASS_NAME, 'btn-primary').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['user'] == [str(user.id)]
    assert query_params['user_permissions'] == ['write']

    driver.find_element(By.XPATH, '//button[contains(text(), "Filters")]').click()

    filters_modal = driver.find_element(By.ID, 'filtersModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: _element_stopped_moving(filters_modal, element_locations))

    filters_modal.find_element(By.XPATH, '//div[@id="filtersModal"]/descendant::button[contains(text(), "Clear")]').click()

    user_settings = sampledb.logic.settings.get_user_settings(user.id)
    assert user_settings['DEFAULT_OBJECT_LIST_FILTERS'] == {}

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert 'user' not in query_params
    assert 'user_permissions' not in query_params

    driver.find_element(By.XPATH, '//button[contains(text(), "Filters")]').click()

    filters_modal = driver.find_element(By.ID, 'filtersModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: _element_stopped_moving(filters_modal, element_locations))

    filters_modal.find_element(By.CLASS_NAME, 'btn-primary').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert 'user' not in query_params or query_params['user'] == [str(user.id)]
    assert 'user_permissions' not in query_params or query_params['user_permissions'] == ['read']


def test_object_list_filters_options(flask_server, driver, user):
    user_settings = sampledb.logic.settings.get_user_settings(user.id)
    assert user_settings['DEFAULT_OBJECT_LIST_FILTERS'] == {}

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.XPATH, '//button[contains(text(), "Options")]').click()

    options_modal = driver.find_element(By.ID, 'optionsModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: _element_stopped_moving(options_modal, element_locations))

    options_modal.find_element(By.CSS_SELECTOR, 'input[name="creation_info"][value="date"]').click()
    options_modal.find_element(By.CSS_SELECTOR, 'input[name="last_edit_info"][value="user"]').click()
    options_modal.find_element(By.CSS_SELECTOR, 'input[name="action_info"][value="instrument"]').click()

    options_modal.find_element(By.CLASS_NAME, 'btn-primary').click()

    user_settings = sampledb.logic.settings.get_user_settings(user.id)
    assert user_settings['DEFAULT_OBJECT_LIST_OPTIONS'] == {}

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['creation_info'] == ['user']
    assert query_params['last_edit_info'] == ['date']
    assert query_params['action_info'] == ['action']
    assert 'other_databases_info' not in query_params
    assert 'location_info' not in query_params
    assert 'display_properties' not in query_params

    driver.find_element(By.XPATH, '//button[contains(text(), "Options")]').click()

    options_modal = driver.find_element(By.ID, 'optionsModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: _element_stopped_moving(options_modal, element_locations))

    options_modal.find_element(By.XPATH, '//div[@id="optionsModal"]/descendant::button[contains(text(), "Save")]').click()

    user_settings = sampledb.logic.settings.get_user_settings(user.id)
    assert user_settings['DEFAULT_OBJECT_LIST_OPTIONS'] == {
        "creation_info": ["user"],
        "last_edit_info": ["date"],
        "action_info": ["action"],
        "other_databases_info": False,
        "location_info": [],
        "display_properties": [],
    }

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert 'creation_info' not in query_params
    assert 'last_edit_info' not in query_params
    assert 'action_info' not in query_params
    assert 'display_properties' not in query_params
    assert 'location_info' not in query_params

    driver.find_element(By.XPATH, '//button[contains(text(), "Options")]').click()

    options_modal = driver.find_element(By.ID, 'optionsModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: _element_stopped_moving(options_modal, element_locations))

    options_modal.find_element(By.CLASS_NAME, 'btn-primary').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['creation_info'] == ['user']
    assert query_params['last_edit_info'] == ['date']
    assert query_params['action_info'] == ['action']
    assert 'display_properties' not in query_params
    assert 'location_info' not in query_params

    driver.find_element(By.XPATH, '//button[contains(text(), "Options")]').click()

    options_modal = driver.find_element(By.ID, 'filtersModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: _element_stopped_moving(options_modal, element_locations))

    options_modal.find_element(By.XPATH, '//div[@id="optionsModal"]/descendant::button[contains(text(), "Clear")]').click()

    user_settings = sampledb.logic.settings.get_user_settings(user.id)
    assert user_settings['DEFAULT_OBJECT_LIST_OPTIONS'] == {}

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert 'creation_info' not in query_params
    assert 'last_edit_info' not in query_params
    assert 'action_info' not in query_params
    assert 'other_databases_info' not in query_params
    assert 'location_info' not in query_params
    assert 'display_properties' not in query_params
