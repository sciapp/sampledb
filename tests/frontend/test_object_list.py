from io import FileIO

from bs4 import BeautifulSoup
import pypdf
import pytest
import requests
from flask import current_app
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from urllib.parse import urlparse, parse_qs
from reportlab.lib.pagesizes import A4, LETTER

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


@pytest.fixture
def object(user):
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    object = sampledb.logic.objects.create_object(
        action_id=action.id,
        data = {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        },
        user_id=user.id
    )
    return object


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
        'filter_instrument_ids': None,
        'filter_doi': None,
        'filter_origin_ids': None,
        'filter_anonymous_permissions': None,
        'filter_all_users_permissions': None,
        'filter_user_id': user.id,
        'filter_user_permissions': 'write',
        'filter_related_user_ids': None
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


def test_object_list_generate_multiple_labels_mixed_formats(object, flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Generate Labels")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['generate_labels'] == ['True']
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.ID, 'checkbox-select-overall').click()
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    quantity_field = driver.find_element(By.ID, 'input-mf-labels-per-object')
    quantity_field.clear()
    quantity_field.send_keys(-1)
    quantity_field.send_keys(Keys.TAB)
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    quantity_field.clear()
    quantity_field.send_keys(1)
    quantity_field.send_keys(Keys.TAB)
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    document = BeautifulSoup(driver.page_source, "html.parser")

    user_session = requests.session()
    user_session.get(flask_server.base_url + f"users/{user.id}/autologin")

    response = user_session.get(flask_server.base_url + "objects/?generate_labels=True")
    csrf_token = BeautifulSoup(response.text, "html.parser").find('input', {'name': 'csrf_token', 'type': 'hidden'})['value']
    request_params = {
        'csrf_token': csrf_token,
        'objects': f"{object.id}",
        'form_variant': document.find('select', {'name': 'form_variant'}).find('option', {'selected': 'selected'})['value'],
        'paper_size': document.find('select', {'name': 'paper_size'}).find('option', {'selected': 'selected'})['value'],
        'labels_per_object': document.find('input', {'name': 'labels_per_object'})['value']
    }

    response = user_session.get(flask_server.base_url + "multiselect_labels", params=request_params)

    assert response.status_code == 200
    assert len(response.content) > 0
    assert response.headers["Content-Type"] == 'application/pdf'

    with FileIO('multiselect_labels.pdf', 'w+') as file:
        file.write(response.content)

        reader = pypdf.PdfReader(file)
        assert len(reader.pages) == 1
        assert reader.pages[0].extract_text().count(object.name) == 6
        assert float(reader.pages[0].mediabox.width) == round(A4[0], 4)
        assert float(reader.pages[0].mediabox.height) == round(A4[1], 4)


def test_object_list_generate_multiple_labels_fixed_widths(object, flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Generate Labels")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['generate_labels'] == ['True']
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.ID, 'checkbox-select-overall').click()
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.XPATH, "//select[@id='select-label-variant']/following-sibling::button").click()
    driver.find_element(By.XPATH, "//select[@id='select-label-variant']/following-sibling::div/div/ul/li/a/span[text()=' Fixed-width labels']/parent::a/parent::li").click()

    paper_size_select = driver.find_element(By.XPATH, "//select[@id='select-fw-paper-size']/following-sibling::button").click()
    a4_landscape_option = driver.find_element(By.XPATH, "//select[@id='select-fw-paper-size']/following-sibling::div/div/ul/li/a/span[text()=' DIN A4 (Landscape)']/parent::a/parent::li").click()

    label_width_field = driver.find_element(By.ID, 'input-fw-label-width')
    label_width_field.clear()
    label_width_field.send_keys(20)
    label_width_field.send_keys(Keys.TAB)
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    label_width_field.clear()
    label_width_field.send_keys(40)
    label_width_field.send_keys(Keys.TAB)
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    min_label_height_field = driver.find_element(By.ID, 'input-fw-label-min-height')
    min_label_height_field.clear()
    min_label_height_field.send_keys(-1)
    min_label_height_field.send_keys(Keys.TAB)
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    min_label_height_field.clear()
    min_label_height_field.send_keys(0)
    min_label_height_field.send_keys(Keys.TAB)
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    quantity_field = driver.find_element(By.ID, 'input-fw-labels-per-object')
    quantity_field.clear()
    quantity_field.send_keys(-1)
    quantity_field.send_keys(Keys.TAB)
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    quantity_field.clear()
    quantity_field.send_keys(5)
    quantity_field.send_keys(Keys.TAB)
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    document = BeautifulSoup(driver.page_source, "html.parser")

    user_session = requests.session()
    user_session.get(flask_server.base_url + f"users/{user.id}/autologin")

    response = user_session.get(flask_server.base_url + "objects/?generate_labels=True")
    csrf_token = BeautifulSoup(response.text, "html.parser").find('input', {'name': 'csrf_token', 'type': 'hidden'})['value']
    request_params = {
        'csrf_token': csrf_token,
        'objects': f"{object.id}",
        'form_variant': driver.execute_script("return $('#select-label-variant').val();"),
        'paper_size': driver.execute_script("return $('#select-fw-paper-size').val();"),
        'label_width': driver.execute_script("return $('#input-fw-label-width').val();"),
        'min_label_height': driver.execute_script("return $('#input-fw-label-min-height').val();"),
        'labels_per_object': driver.execute_script("return $('#input-fw-labels-per-object').val();")
    }

    response = user_session.get(flask_server.base_url + "multiselect_labels", params=request_params)

    assert response.status_code == 200
    assert len(response.content) > 0
    assert response.headers["Content-Type"] == 'application/pdf'

    with FileIO('multiselect_labels.pdf', 'w+') as file:
        file.write(response.content)

        reader = pypdf.PdfReader(file)
        assert len(reader.pages) == 1
        assert reader.pages[0].extract_text().count(object.name) == 5
        assert float(reader.pages[0].mediabox.width) == round(A4[1], 4)
        assert float(reader.pages[0].mediabox.height) == round(A4[0], 4)


def test_object_list_generate_multiple_labels_minimal_height(object, flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Generate Labels")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['generate_labels'] == ['True']
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.ID, 'checkbox-select-overall').click()
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.XPATH, "//select[@id='select-label-variant']/following-sibling::button").click()
    driver.find_element(By.XPATH, "//select[@id='select-label-variant']/following-sibling::div/div/ul/li/a/span[text()=' Minimal-height labels']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//select[@id='select-mh-paper-size']/following-sibling::button").click()
    driver.find_element(By.XPATH, "//select[@id='select-mh-paper-size']/following-sibling::div/div/ul/li/a/span[text()=' Letter / ANSI A (Portrait)']/parent::a/parent::li").click()

    min_label_width_field = driver.find_element(By.ID, 'input-mh-min-label-width')
    min_label_width_field.clear()
    min_label_width_field.send_keys(-1)
    min_label_width_field.send_keys(Keys.TAB)
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    min_label_width_field.clear()
    min_label_width_field.send_keys(0)
    min_label_width_field.send_keys(Keys.TAB)
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    quantity_field = driver.find_element(By.ID, 'input-mh-labels-per-object')
    quantity_field.clear()
    quantity_field.send_keys(-1)
    quantity_field.send_keys(Keys.TAB)
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    quantity_field.clear()
    quantity_field.send_keys(5)
    quantity_field.send_keys(Keys.TAB)
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    document = BeautifulSoup(driver.page_source, "html.parser")

    user_session = requests.session()
    user_session.get(flask_server.base_url + f"users/{user.id}/autologin")

    response = user_session.get(flask_server.base_url + "objects/?generate_labels=True")
    csrf_token = BeautifulSoup(response.text, "html.parser").find('input', {'name': 'csrf_token', 'type': 'hidden'})['value']
    request_params = {
        'csrf_token': csrf_token,
        'objects': f"{object.id}",
        'form_variant': driver.execute_script("return $('#select-label-variant').val();"),
        'paper_size': driver.execute_script("return $('#select-mh-paper-size').val();"),
        'min_label_width': driver.execute_script("return $('#input-mh-min-label-width').val();"),
        'labels_per_object': driver.execute_script("return $('#input-mh-labels-per-object').val();")
    }

    response = user_session.get(flask_server.base_url + "multiselect_labels", params=request_params)

    assert response.status_code == 200
    assert len(response.content) > 0
    assert response.headers["Content-Type"] == 'application/pdf'

    with FileIO('multiselect_labels.pdf', 'w+') as file:
        file.write(response.content)

        reader = pypdf.PdfReader(file)
        assert len(reader.pages) == 1
        assert reader.pages[0].extract_text().count(object.name) == 5
        assert float(reader.pages[0].mediabox.width) == round(LETTER[0], 4)
        assert float(reader.pages[0].mediabox.height) == round(LETTER[1], 4)


def test_object_list_change_signed_in_min_permission(object, flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Edit Permissions")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['edit_permissions'] == ['True']
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.ID, 'checkbox-select-overall').click()
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='read']").click()

    assert not driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='write']").is_enabled()
    assert not driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='grant']").is_enabled()

    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']/div/div/div").text == 'All Signed-In Users'
    assert driver.execute_script("return $('input:radio[name=\"update_mode\"]:checked').val()") == 'set-min'
    assert driver.execute_script("return $('input:radio[name=\"permission\"]:checked').val()") == 'read'

    driver.find_element(By.ID, 'multiselect-submit').click()
    assert sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id=object.id) == sampledb.logic.permissions.Permissions.READ


def test_object_list_change_signed_in_max_permission(object, flask_server, driver, user):
    sampledb.logic.object_permissions.set_object_permissions_for_all_users(object_id=object.id, permissions=sampledb.models.Permissions.WRITE)
    assert sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id=object.id) == sampledb.models.Permissions.WRITE

    driver.get(flask_server.base_url + f"users/{user.id}/autologin")
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Edit Permissions")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params["edit_permissions"] == ["True"]

    driver.find_element(By.ID, 'checkbox-select-overall').click()
    driver.find_element(By.XPATH, "//label/input[@name='update_mode' and @value='set-max']").click()

    driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='none']").click()

    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']/div/div/div").text == 'All Signed-In Users'
    assert driver.execute_script("return $('input:radio[name=\"update_mode\"]:checked').val()") == 'set-max'
    assert driver.execute_script("return $('input:radio[name=\"permission\"]:checked').val()") == 'none'

    driver.find_element(By.ID, 'multiselect-submit').click()

    assert sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id=object.id) == sampledb.logic.permissions.Permissions.NONE


def test_object_list_change_anonymous_min_permission(object, flask_server, driver, user):
    flask_server.app.config["ENABLE_ANONYMOUS_USERS"] = True
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Edit Permissions")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['edit_permissions'] == ['True']
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.ID, 'checkbox-select-overall').click()
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-target-type']/following-sibling::div/div/ul/li/a/span[text()='Anonymous Users']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='read']").click()

    assert not driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='write']").is_enabled()
    assert not driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='grant']").is_enabled()

    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']/div/div/div").text == 'Anonymous Users'
    assert driver.execute_script("return $('input:radio[name=\"update_mode\"]:checked').val()") == 'set-min'
    assert driver.execute_script("return $('input:radio[name=\"permission\"]:checked').val()") == 'read'

    driver.find_element(By.ID, 'multiselect-submit').click()
    assert sampledb.logic.object_permissions.get_object_permissions_for_anonymous_users(object_id=object.id) == sampledb.logic.permissions.Permissions.READ


def test_object_list_change_anonymous_max_permission(object, flask_server, driver, user):
    flask_server.app.config["ENABLE_ANONYMOUS_USERS"] = True
    sampledb.logic.object_permissions.set_object_permissions_for_all_users(object_id=object.id, permissions=sampledb.models.Permissions.WRITE)
    assert sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id=object.id) == sampledb.models.Permissions.WRITE

    driver.get(flask_server.base_url + f"users/{user.id}/autologin")
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Edit Permissions")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params["edit_permissions"] == ["True"]

    driver.find_element(By.ID, 'checkbox-select-overall').click()
    driver.find_element(By.XPATH, "//label/input[@name='update_mode' and @value='set-max']").click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-target-type']/following-sibling::div/div/ul/li/a/span[text()='Anonymous Users']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='none']").click()

    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']/div/div/div").text == 'Anonymous Users'
    assert driver.execute_script("return $('input:radio[name=\"update_mode\"]:checked').val()") == 'set-max'
    assert driver.execute_script("return $('input:radio[name=\"permission\"]:checked').val()") == 'none'

    driver.find_element(By.ID, 'multiselect-submit').click()

    assert sampledb.logic.object_permissions.get_object_permissions_for_anonymous_users(object_id=object.id) == sampledb.logic.permissions.Permissions.NONE


def test_object_list_change_user_min_permission(object, flask_server, driver, user):
    with flask_server.app.app_context():
        test_user = sampledb.models.User(name="Test User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(test_user)
        sampledb.db.session.commit()
        assert test_user.id is not None

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Edit Permissions")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['edit_permissions'] == ['True']
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.ID, 'checkbox-select-overall').click()
    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-target-type']/following-sibling::div/div/ul/li/a/span[text()='User']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-users']").click()
    driver.find_element(By.XPATH, f"//select[@id='edit-permissions-users']/following-sibling::div/div/ul/li/a/span[text()='{test_user.name} (#{test_user.id})']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='write']").click()

    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']/div/div/div").text == 'User'
    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-users']/div/div/div").text == f'{test_user.name} (#{test_user.id})'
    assert driver.execute_script("return $('input:radio[name=\"update_mode\"]:checked').val()") == 'set-min'
    assert driver.execute_script("return $('input:radio[name=\"permission\"]:checked').val()") == 'write'

    assert driver.find_element(By.ID, "multiselect-submit").is_enabled()
    driver.find_element(By.ID, 'multiselect-submit').click()
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id=object.id, user_id=test_user.id) == sampledb.logic.permissions.Permissions.WRITE


def test_object_list_change_user_max_permission(object, flask_server, driver, user):
    with flask_server.app.app_context():
        test_user = sampledb.models.User(name="Test User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(test_user)
        sampledb.db.session.commit()
        assert test_user.id is not None
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=object.id, user_id=test_user.id, permissions=sampledb.models.Permissions.WRITE)
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id=object.id, user_id=test_user.id) == sampledb.models.Permissions.WRITE

    driver.get(flask_server.base_url + f"users/{user.id}/autologin")
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Edit Permissions")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params["edit_permissions"] == ["True"]

    driver.find_element(By.ID, "checkbox-select-overall").click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-target-type']/following-sibling::div/div/ul/li/a/span[text()='User']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-users']").click()
    driver.find_element(By.XPATH, f"//select[@id='edit-permissions-users']/following-sibling::div/div/ul/li/a/span[text()='{test_user.name} (#{test_user.id})']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//label/input[@name='update_mode' and @value='set-max']").click()
    driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='read']").click()

    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']/div/div/div").text == 'User'
    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-users']/div/div/div").text == f'{test_user.name} (#{test_user.id})'
    assert driver.execute_script("return $('input:radio[name=\"update_mode\"]:checked').val()") == 'set-max'
    assert driver.execute_script("return $('input:radio[name=\"permission\"]:checked').val()") == 'read'

    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()
    driver.find_element(By.ID, 'multiselect-submit').click()
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id=object.id, user_id=test_user.id) == sampledb.logic.permissions.Permissions.READ


def test_object_list_change_group_min_permission(object, flask_server, driver, user):
    test_group = sampledb.logic.groups.create_group(name="Test Group", description="", initial_user_id=user.id)
    assert test_group.id is not None

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Edit Permissions")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['edit_permissions'] == ['True']
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.ID, "checkbox-select-overall").click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-target-type']/following-sibling::div/div/ul/li/a/span[text()='Basic Group']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-groups']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-groups']/following-sibling::div//button[text()='Expand All']").click()
    driver.find_element(By.XPATH, "//span[text()='Test Group']/parent::span/parent::a").click()

    driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='write']").click()

    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']/div/div/div").text == 'Basic Group'
    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-groups']/div/div/div").text == 'Test Group'
    assert driver.execute_script("return $('input:radio[name=\"update_mode\"]:checked').val()") == 'set-min'
    assert driver.execute_script("return $('input:radio[name=\"permission\"]:checked').val()") == 'write'

    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()
    driver.find_element(By.ID, 'multiselect-submit').click()
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id=object.id).get(test_group.id) == sampledb.logic.permissions.Permissions.WRITE


def test_object_list_change_group_max_permission(object, flask_server, driver, user):
    test_group = sampledb.logic.groups.create_group(name="Test Group", description="", initial_user_id=user.id)
    assert test_group.id is not None
    sampledb.logic.object_permissions.set_group_object_permissions(object_id=object.id, group_id=test_group.id, permissions=sampledb.models.permissions.Permissions.WRITE)
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id=object.id).get(test_group.id) == sampledb.models.permissions.Permissions.WRITE

    driver.get(flask_server.base_url + f"users/{user.id}/autologin")
    driver.get(flask_server.base_url + "objects/")

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Edit Permissions")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params["edit_permissions"] == ["True"]

    driver.find_element(By.ID, 'checkbox-select-overall').click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-target-type']/following-sibling::div/div/ul/li/a/span[text()='Basic Group']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-groups']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-groups']/following-sibling::div//button[text()='Expand All']").click()
    driver.find_element(By.XPATH, "//span[text()='Test Group']/parent::span/parent::a").click()

    driver.find_element(By.XPATH, "//label/input[@name='update_mode' and @value='set-max']").click()

    driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='read']").click()

    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']/div/div/div").text == 'Basic Group'
    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-groups']/div/div/div").text == 'Test Group'
    assert driver.execute_script("return $('input:radio[name=\"update_mode\"]:checked').val()") == 'set-max'
    assert driver.execute_script("return $('input:radio[name=\"permission\"]:checked').val()") == 'read'

    assert driver.find_element(By.ID, 'multiselect-submit').is_enabled()
    driver.find_element(By.ID, 'multiselect-submit').click()
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id=object.id).get(test_group.id) == sampledb.logic.permissions.Permissions.READ


def test_object_list_change_project_group_min_permission(object, flask_server, driver, user):
    test_project = sampledb.logic.projects.create_project(name="Test Project", description="", initial_user_id=user.id)
    assert test_project.id is not None

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'objects/')

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Edit Permissions")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params['edit_permissions'] == ['True']
    assert not driver.find_element(By.ID, 'multiselect-submit').is_enabled()

    driver.find_element(By.ID, 'checkbox-select-overall').click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-target-type']/following-sibling::div/div/ul/li/a/span[text()='Project Group']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-project-groups']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-project-groups']/following-sibling::div//button[text()='Expand All']").click()
    driver.find_element(By.XPATH, "//span[text()='Test Project']/parent::span/parent::a").click()

    driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='write']").click()

    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']/div/div/div").text == 'Project Group'
    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-project-groups']/div/div/div").text == 'Test Project'
    assert driver.execute_script("return $('input:radio[name=\"update_mode\"]:checked').val()") == 'set-min'
    assert driver.execute_script("return $('input:radio[name=\"permission\"]:checked').val()") == 'write'

    assert driver.find_element(By.ID, "multiselect-submit").is_enabled()
    driver.find_element(By.ID, "multiselect-submit").click()
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id=object.id).get(test_project.id) == sampledb.models.Permissions.WRITE


def test_object_list_change_project_group_max_permission(object, flask_server, driver, user):
    test_project = sampledb.logic.projects.create_project(name="Test Project", description="", initial_user_id=user.id)
    assert test_project.id is not None
    sampledb.logic.object_permissions.set_project_object_permissions(object_id=object.id, project_id=test_project.id, permissions=sampledb.models.Permissions.WRITE)
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id=object.id).get(test_project.id) == sampledb.models.Permissions.WRITE

    driver.get(flask_server.base_url + f"users/{user.id}/autologin")
    driver.get(flask_server.base_url + "objects/")

    driver.find_element(By.ID, 'multiselect-dropdown').click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Edit Permissions")]').click()

    query_params = parse_qs(urlparse(driver.current_url).query)
    assert query_params["edit_permissions"] == ["True"]

    driver.find_element(By.ID, "checkbox-select-overall").click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-target-type']/following-sibling::div/div/ul/li/a/span[text()='Project Group']/parent::a/parent::li").click()

    driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-project-groups']").click()
    driver.find_element(By.XPATH, "//select[@id='edit-permissions-project-groups']/following-sibling::div//button[text()='Expand All']").click()
    driver.find_element(By.XPATH, "//span[text()='Test Project']/parent::span/parent::a").click()

    driver.find_element(By.XPATH, "//label/input[@name='update_mode' and @value='set-max']").click()

    driver.find_element(By.XPATH, "//label/input[@name='permission' and @value='read']").click()

    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-target-type']/div/div/div").text == 'Project Group'
    assert driver.find_element(By.XPATH, "//button[@data-id='edit-permissions-project-groups']/div/div/div").text == 'Test Project'
    assert driver.execute_script("return $('input:radio[name=\"update_mode\"]:checked').val()") == 'set-max'
    assert driver.execute_script("return $('input:radio[name=\"permission\"]:checked').val()") == 'read'

    assert driver.find_element(By.ID, "multiselect-submit").is_enabled()
    driver.find_element(By.ID, "multiselect-submit").click()
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id=object.id).get(test_project.id) == sampledb.models.Permissions.READ
