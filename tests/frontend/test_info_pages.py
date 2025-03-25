import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import visibility_of_element_located

import sampledb.logic
from ..conftest import wait_for_page_load


@pytest.fixture
def user():
    return sampledb.logic.users.create_user(
        name='Test User',
        email='example@example.org',
        type=sampledb.logic.users.UserType.PERSON
    )


@pytest.fixture
def admin():
    user = sampledb.logic.users.create_user(
        name='Admin User',
        email='example@example.org',
        type=sampledb.logic.users.UserType.PERSON
    )
    sampledb.logic.users.set_user_administrator(user.id, True)
    return sampledb.logic.users.get_user(user.id)


@pytest.fixture
def info_page():
    return sampledb.logic.info_pages.create_info_page(
        title={
            'en': 'Title'
        },
        content={
            'en': 'Content'
        },
        endpoint='frontend.index',
        disabled=False
    )


def test_view_and_acknowledge_single_info_page(flask_server, driver, user, info_page):
    assert not sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')

    driver.get(flask_server.base_url + 'users/')
    assert not driver.find_elements(By.ID, 'infoPageModal')

    driver.get(flask_server.base_url)
    assert driver.find_elements(By.ID, 'infoPageModal')
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.ID, 'infoPageModal')))
    info_page_titles = driver.find_elements(By.CSS_SELECTOR, '#infoPageModal .modal-title')
    assert len(info_page_titles) == 1
    assert info_page_titles[0].text == 'Title'
    assert not sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
    driver.find_element(By.CSS_SELECTOR, '#infoPageModal .modal-content button').click()
    time.sleep(1)

    assert user.id in sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
    driver.get(flask_server.base_url)
    assert not driver.find_elements(By.ID, 'infoPageModal')


def test_view_and_acknowledge_multiple_info_pages(flask_server, driver, user):
    info_pages = [
        sampledb.logic.info_pages.create_info_page(
            title={
                'en': 'Info Page Title #{i}'
            },
            content={
                'en': 'Content'
            },
            endpoint='frontend.users',
            disabled=False,
        )
        for _ in range(5)
    ]
    for info_page in info_pages:
        assert not sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')

    driver.get(flask_server.base_url)
    assert not driver.find_elements(By.ID, 'infoPageModal')

    driver.get(flask_server.base_url + 'users/')
    assert driver.find_elements(By.ID, 'infoPageModal')
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.ID, 'infoPageModal')))
    info_page_titles = driver.find_elements(By.CSS_SELECTOR, '#infoPageModal .modal-title')
    assert len(info_page_titles) == len(info_pages)
    for i in range(len(info_pages)):
        assert [info_page_title.text for info_page_title in info_page_titles] == [(f"{info_page.title["en"]} ({j + 1}\u202f/\u202f{len(info_pages)})"  if j == i else '') for j, info_page in enumerate(info_pages)]
        if i > 0:
            assert driver.find_element(By.CSS_SELECTOR, f'#infoPageModal .modal-content:nth-child({i+1}) button[data-info-page-button="back"]')
        if i < len(info_pages) - 1:
            driver.find_element(By.CSS_SELECTOR, f'#infoPageModal .modal-content:nth-child({i+1}) button[data-info-page-button="next"]').click()
        else:
            for info_page in info_pages:
                assert not sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
            driver.find_element(By.CSS_SELECTOR, f'#infoPageModal .modal-content:nth-child({i+1}) button[data-info-page-button="acknowledge"]').click()
    time.sleep(1)

    for info_page in info_pages:
        assert user.id in sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
    driver.get(flask_server.base_url)
    assert not driver.find_elements(By.ID, 'infoPageModal')

@pytest.mark.parametrize(['do_not_show_existing_users'], [[True], [False]])
def test_create_info_page(flask_server, driver, admin, user, do_not_show_existing_users):
    driver.get(flask_server.base_url + f'users/{admin.id}/autologin')
    driver.get(flask_server.base_url + 'admin/info_pages')
    driver.find_element(By.XPATH, f'//a[text()="Create Info Page"]').click()
    driver.find_element(By.CSS_SELECTOR, '.input-group[data-language-id="-99"] input[data-name="input-title"]').send_keys('Example Info Page', Keys.TAB)
    code_mirror = driver.find_element(By.CSS_SELECTOR, '.input-group[data-language-id="-99"] .CodeMirror')
    code_mirror.find_element(By.CSS_SELECTOR, '.CodeMirror-lines:first-child').click()
    code_mirror.find_element(By.CSS_SELECTOR, 'textarea').send_keys('Example Content', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#input-endpoint ~ .dropdown-toggle').click()
    driver.find_element(By.XPATH, f'//span[contains(text(), "/instruments/")]').click()
    if do_not_show_existing_users:
        driver.find_element(By.ID, 'input-do_not_show_existing_users').click()
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, 'button[name="action_submit"]').click()
    info_pages = sampledb.logic.info_pages.get_info_pages()
    assert len(info_pages) == 1
    info_page = info_pages[0]
    assert info_page.title == {'en': 'Example Info Page'}
    assert info_page.content == {'en': 'Example Content'}
    assert info_page.endpoint == 'frontend.instruments'
    if do_not_show_existing_users:
        assert user.id in sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
    else:
        assert user.id not in sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)


@pytest.mark.parametrize(['clear_acknowledgements'], [[True], [False]])
def test_edit_info_page(flask_server, driver, admin, user, info_page, clear_acknowledgements):
    sampledb.logic.info_pages.acknowledge_info_pages({info_page.id}, user.id)
    driver.get(flask_server.base_url + f'users/{admin.id}/autologin')
    driver.get(flask_server.base_url + f'admin/info_pages/{info_page.id}')
    driver.find_element(By.XPATH, f'//a[text()="Edit"]').click()
    driver.find_element(By.CSS_SELECTOR, '.input-group[data-language-id="-99"] input[data-name="input-title"]').send_keys(*[Keys.BACKSPACE] * len(info_page.title['en']), 'Example Info Page', Keys.TAB)
    code_mirror = driver.find_element(By.CSS_SELECTOR, '.input-group[data-language-id="-99"] .CodeMirror')
    code_mirror.find_element(By.CSS_SELECTOR, '.CodeMirror-lines:first-child').click()
    code_mirror.find_element(By.CSS_SELECTOR, 'textarea').send_keys(*[Keys.BACKSPACE] * len(info_page.content['en']), 'Example Content', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '#input-endpoint ~ .dropdown-toggle').click()
    driver.find_element(By.XPATH, f'//span[contains(text(), "/users/")]').click()
    if clear_acknowledgements:
        driver.find_element(By.ID, 'input-clear_acknowledgements').click()
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, 'button[name="action_submit"]').click()
    info_pages = sampledb.logic.info_pages.get_info_pages()
    assert len(info_pages) == 1
    info_page = info_pages[0]
    assert info_page.title == {'en': 'Example Info Page'}
    assert info_page.content == {'en': 'Example Content'}
    assert info_page.endpoint == 'frontend.users'
    if clear_acknowledgements:
        assert user.id not in sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
    else:
        assert user.id in sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)


@pytest.mark.parametrize(['disabled', 'via_list'], [[True, True], [True, False], [False, True], [False, False]])
def test_toggle_info_page_disabled(flask_server, driver, admin, info_page, disabled, via_list):
    sampledb.logic.info_pages.set_info_page_disabled(info_page.id, not disabled)
    assert sampledb.logic.info_pages.get_info_page(info_page.id).disabled != disabled
    driver.get(flask_server.base_url + f'users/{admin.id}/autologin')
    if via_list:
        driver.get(flask_server.base_url + f'admin/info_pages/')
    else:
        driver.get(flask_server.base_url + f'admin/info_pages/{info_page.id}')
    with wait_for_page_load(driver):
        if disabled:
            driver.find_element(By.XPATH, f'//button[contains(text(), "Disable")]').click()
        else:
            driver.find_element(By.XPATH, f'//button[contains(text(), "Enable")]').click()
    assert sampledb.logic.info_pages.get_info_page(info_page.id).disabled == disabled


@pytest.mark.parametrize(['disabled', 'via_list'], [[True, True], [True, False], [False, True], [False, False]])
def test_toggle_info_page_disabled_repeated(flask_server, driver, admin, info_page, disabled, via_list):
    sampledb.logic.info_pages.set_info_page_disabled(info_page.id, not disabled)
    assert sampledb.logic.info_pages.get_info_page(info_page.id).disabled != disabled
    driver.get(flask_server.base_url + f'users/{admin.id}/autologin')
    if via_list:
        driver.get(flask_server.base_url + f'admin/info_pages/')
    else:
        driver.get(flask_server.base_url + f'admin/info_pages/{info_page.id}')
    sampledb.logic.info_pages.set_info_page_disabled(info_page.id, disabled)
    assert sampledb.logic.info_pages.get_info_page(info_page.id).disabled == disabled
    with wait_for_page_load(driver):
        if disabled:
            driver.find_element(By.XPATH, f'//button[contains(text(), "Disable")]').click()
        else:
            driver.find_element(By.XPATH, f'//button[contains(text(), "Enable")]').click()
    assert sampledb.logic.info_pages.get_info_page(info_page.id).disabled == disabled
    assert driver.find_elements(By.CSS_SELECTOR, 'div.alert.alert-warning')
    if disabled:
        assert "The info page has already been disabled." in driver.find_element(By.CSS_SELECTOR, 'div.alert.alert-warning').text
    else:
        assert "The info page has already been enabled." in driver.find_element(By.CSS_SELECTOR, 'div.alert.alert-warning').text


@pytest.mark.parametrize(['via_list'], [[True], [False]])
def test_delete_info_page(flask_server, driver, admin, info_page, via_list):
    assert sampledb.logic.info_pages.get_info_pages()
    driver.get(flask_server.base_url + f'users/{admin.id}/autologin')
    if via_list:
        driver.get(flask_server.base_url + f'admin/info_pages/')
    else:
        driver.get(flask_server.base_url + f'admin/info_pages/{info_page.id}')
    driver.find_element(By.XPATH, f'//button[contains(text(), "Delete")]').click()
    WebDriverWait(driver, 10).until(visibility_of_element_located((By.CSS_SELECTOR, 'button[value="delete_info_page"]')))
    with wait_for_page_load(driver):
        driver.find_element(By.CSS_SELECTOR, 'button[value="delete_info_page"]').click()
    assert not sampledb.logic.info_pages.get_info_pages()
