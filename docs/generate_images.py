# coding: utf-8

import contextlib
import getpass
import io
import json
import os
import sys
import time

import flask
from PIL import Image
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options

import chromedriver_binary

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sampledb
import sampledb.config
import sampledb.logic
import tests.conftest
import tests.test_utils

app = tests.test_utils.app()


def scroll_to(driver, x, y):
    driver.execute_script("window.scrollTo({}, {})".format(x, y))
    # disable scrollbars
    driver.execute_script("""
    var style = document.createElement('style');
    style.innerHTML = '::-webkit-scrollbar { display: none; }';
    var head = document.getElementsByTagName('head')[0];
    head.appendChild(style);
    """)


def resize_for_screenshot(driver, width, height):
    """
    Resize the webdriver window to make screenshots match a given size.

    Webdrivers like Chrome might display information bars at the top that will
    result in a screenshot size smaller than the window size. This function
    iteratively compensates for these decorations until the screenshot size
    matches the requested width and height.

    :param driver: the webdriver
    :param width: the requested width
    :param height: the requested height
    :return:
    """
    global previous_width_correction
    global previous_height_correction
    real_height = -1
    real_width = -1
    requested_width = width
    requested_height = height
    width_correction = previous_width_correction
    height_correction = previous_height_correction
    while real_height != height or real_width != width:
        requested_width += width_correction
        requested_height += height_correction
        if requested_width <= 0 or requested_height <= 0:
            break
        driver.set_window_size(requested_width, requested_height)
        image_data = driver.get_screenshot_as_png()
        real_width, real_height = Image.open(io.BytesIO(image_data)).size
        width_correction = width - real_width
        height_correction = height - real_height
    previous_width_correction = requested_width - width
    previous_height_correction = requested_height - height


# Cached values for resize_for_screenshot()
previous_height_correction = 0
previous_width_correction = 0


def guest_invitation(base_url, driver):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'users/invitation')
    for heading in driver.find_elements_by_tag_name('h1'):
        if 'Invite' in heading.text:
            break
    else:
        assert False
    container = driver.find_element_by_id('main').find_elements_by_class_name('container')[-1]
    driver.get_screenshot_as_file('docs/static/img/generated/guest_invitation.png')
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/guest_invitation.png', (0, heading.location['y'], width, min(heading.location['y'] + max_height, container.location['y'] + container.rect['height'])))


def default_permissions(base_url, driver):
    width = 1280
    min_height = 200
    resize_for_screenshot(driver, width, min_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'users/me/preferences')
    for heading in driver.find_elements_by_tag_name('h2'):
        if 'Default Permissions' in heading.text:
            break
    else:
        assert False
    scroll_to(driver, 0, heading.location['y'])
    footer = driver.find_elements_by_tag_name('footer')[-1]
    resize_for_screenshot(driver, width, footer.location['y'] - heading.location['y'])
    driver.get_screenshot_as_file('docs/static/img/generated/default_permissions.png')


def object_permissions(base_url, driver):
    width = 1280
    min_height = 200
    resize_for_screenshot(driver, width, min_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))

    driver.get(base_url + 'objects/{}/permissions'.format(object.object_id))
    resize_for_screenshot(driver, width, min_height)
    for heading in driver.find_elements_by_tag_name('h2'):
        if 'Permissions' in heading.text:
            break
    else:
        assert False
    scroll_to(driver, 0, heading.location['y'])
    footer = driver.find_elements_by_tag_name('footer')[-1]
    resize_for_screenshot(driver, width, footer.location['y'] - heading.location['y'])
    driver.get_screenshot_as_file('docs/static/img/generated/object_permissions.png')


def save_cropped_screenshot_as_file(driver, file_name, box):
    image_data = driver.get_screenshot_as_png()
    image = Image.open(io.BytesIO(image_data))
    image = image.crop(box)
    image.save(file_name)


with app.app_context():
    user = sampledb.models.User(
        name="Example User",
        email="example@fz-juelich.de",
        type=sampledb.models.UserType.PERSON
    )
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert user.id is not None

    other_user = sampledb.models.User(
        name="Other User",
        email="example@fz-juelich.de",
        type=sampledb.models.UserType.PERSON
    )
    sampledb.db.session.add(other_user)
    sampledb.db.session.commit()
    assert other_user.id is not None

    group = sampledb.logic.groups.create_group(
        name="Example Group",
        description="An example group for the documentation",
        initial_user_id=user.id
    )

    project = sampledb.logic.projects.create_project(
        name="Example Project",
        description="An example project for the documentation",
        initial_user_id=user.id
    )

    instrument = sampledb.logic.instruments.create_instrument(
        name="Example Instrument",
        description="This is an example instrument for the documentation."
    )
    with open('sampledb/schemas/ombe_measurement.sampledb.json', 'r', encoding='utf-8') as schema_file:
        schema = json.load(schema_file)
    instrument_action = sampledb.logic.actions.create_action(
        action_type=sampledb.logic.actions.ActionType.SAMPLE_CREATION,
        name="Sample Creation",
        description="This is an example action",
        schema=schema,
        instrument_id=instrument.id
    )
    with open('example_data/ombe-1.sampledb.json', 'r', encoding='utf-8') as data_file:
        data = json.load(data_file)
    object = sampledb.logic.objects.create_object(
        action_id=instrument_action.id,
        data=data,
        user_id=user.id,
        previous_object_id=None,
        schema=schema
    )

    os.makedirs('docs/static/img/generated', exist_ok=True)
    options = Options()
    # disable Chrome sandbox for root in GitLab CI
    if 'CI' in os.environ and getpass.getuser() == 'root':
        options.add_argument('--no-sandbox')
    with contextlib.contextmanager(tests.test_utils.flask_server)(app) as flask_server:
        with contextlib.closing(Chrome(options=options)) as driver:
            object_permissions(flask_server.base_url, driver)
            default_permissions(flask_server.base_url, driver)
            guest_invitation(flask_server.base_url, driver)
