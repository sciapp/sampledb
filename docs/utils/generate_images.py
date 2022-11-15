# coding: utf-8

import contextlib
import getpass
import io
import os
import secrets
import shutil
import sys
import tempfile
import time

from PIL import Image
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options

import chromedriver_binary
from selenium.webdriver.common.by import By

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import sampledb
import sampledb.config
import sampledb.logic
import tests.conftest

DEVICE_PIXEL_RATIO = int(os.environ.get('DEVICE_PIXEL_RATIO', '1'))


def scroll_to_element(driver, element):
    driver.execute_script(f"window.scrollTo(0, {element.location['y']})")
    # disable scrollbars
    driver.execute_script("""
    var style = document.createElement('style');
    style.innerHTML = '::-webkit-scrollbar { display: none; }';
    var head = document.getElementsByTagName('head')[0];
    head.appendChild(style);
    """)
    num_attempts = 0
    while element.location['y'] < 0 and num_attempts < 5:
        print(f"Additional scrolling by {element.location['y']} (attempt #{num_attempts})", file=sys.stderr)
        driver.execute_script("window.scrollBy({}, {})".format(0, element.location['y']))
        num_attempts += 1
    return driver.execute_script("""
    return window.pageYOffset;
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


def wait_until_visible(element):
    NUM_RETRIES = 30
    for wait_time in range(NUM_RETRIES):
        if element.rect['width'] > 0 and element.rect['height'] > 0:
            if wait_time >= 5:
                print('element visible after', wait_time, 'seconds', file=sys.stderr)
            return element
        time.sleep(1)
    # maximum number of retries exhausted
    assert False


# Cached values for resize_for_screenshot()
previous_height_correction = 0
previous_width_correction = 0


def guest_invitation(base_url, driver):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'users/invitation')
    for heading in driver.find_elements(By.TAG_NAME, 'h1'):
        if 'Invite' in heading.text:
            break
    else:
        assert False
    container = driver.find_element(By.ID, 'main').find_elements(By.CLASS_NAME, 'container')[-1]
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/guest_invitation.png', (0, heading.location['y'], width, min(heading.location['y'] + max_height, container.location['y'] + container.rect['height'])))


def default_permissions(base_url, driver):
    width = 1280
    min_height = 200
    resize_for_screenshot(driver, width, min_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'users/me/preferences')
    for heading in driver.find_elements(By.TAG_NAME, 'h2'):
        if 'Default Permissions' in heading.text:
            break
    else:
        assert False
    for next_heading in driver.find_elements(By.TAG_NAME, 'h2'):
        if 'Other Settings' in next_heading.text:
            break
    else:
        assert False
    scroll_to_element(driver, heading)
    resize_for_screenshot(driver, width, next_heading.location['y'] - heading.location['y'])
    driver.get_screenshot_as_file('docs/static/img/generated/default_permissions.png')


def action(base_url, driver, action):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'actions/{}'.format(action.id))
    heading = driver.find_elements(By.TAG_NAME, 'h1')[0]

    for anchor in driver.find_elements(By.TAG_NAME, 'a'):
        if 'Create Sample' in anchor.text:
            break
    else:
        assert False
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/action.png', (0, heading.location['y'], width, min(heading.location['y'] + max_height, anchor.location['y'] + anchor.rect['height'])))


def tags_input(base_url, driver, object):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'objects/{}'.format(object.id))
    for row in driver.find_elements(By.CLASS_NAME, 'row'):
        if 'Tags' in row.text:
            break
    else:
        assert False
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/tags.png', (0, row.location['y'], width, min(row.location['y'] + max_height, row.location['y'] + row.rect['height'])))


def comments(base_url, driver, object):
    sampledb.logic.comments.create_comment(object.id, user.id, "This is an example comment.")
    sampledb.logic.comments.create_comment(object.id, user.id, "Comments can contain multiple paragraphs.\nThe text will be displayed as you typed it.\n - As a result, you can use simple lists.\n - Markdown or similar languages are not supported however.")

    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'objects/{}'.format(object.id))
    for heading in driver.find_elements(By.TAG_NAME, 'h2'):
        if 'Comments' in heading.text:
            break
    else:
        assert False
    y_offset = scroll_to_element(driver, heading)
    comment_form = driver.find_element(By.ID, 'new-comment-form')
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/comments.png', (0, heading.location['y'] - y_offset, width, min(heading.location['y'] + max_height, comment_form.location['y'] + comment_form.rect['height']) - y_offset))


def activity_log(base_url, driver, object):
    object = sampledb.logic.objects.create_object(object.action_id, object.data, user.id, object.id)
    sampledb.logic.files.create_local_file(object.id, user.id, "example.txt", lambda stream: stream.write(b'example text'))
    sampledb.logic.comments.create_comment(object.id, user.id, "This is an example comment.")

    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'objects/{}'.format(object.id))
    for heading in driver.find_elements(By.TAG_NAME, 'h2'):
        if 'Activity Log' in heading.text:
            break
    else:
        assert False
    y_offset = scroll_to_element(driver, heading)
    activity_log = driver.find_element(By.ID, 'activity_log')
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/activity_log_dontblock.png', (0, heading.location['y'] - y_offset, width, min(activity_log.location['y'] - y_offset + activity_log.rect['height'], max_height)))


def location_assignments(base_url, driver, object, room_42):
    object = sampledb.logic.objects.create_object(object.action_id, object.data, user.id, object.id)
    sampledb.logic.locations.assign_location_to_object(object.id, room_42.id, None, user.id, {"en": "Shelf C"})
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'objects/{}'.format(object.id))
    for heading in driver.find_elements(By.TAG_NAME, 'h2'):
        if 'Location' in heading.text:
            break
    else:
        assert False
    y_offset = scroll_to_element(driver, heading)
    location_form = driver.find_element(By.ID, 'assign-location-form')
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/location_assignments.png', (0, heading.location['y'] - y_offset, width, min(heading.location['y'] + max_height, location_form.location['y'] + location_form.rect['height']) - y_offset))


def locations(base_url, driver):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'locations/')
    main = driver.find_elements(By.ID, 'main')[0]
    for last_location in driver.find_elements(By.TAG_NAME, 'a'):
        if 'Box Demo-3' in last_location.text:
            break
    else:
        assert False
    y_offset = scroll_to_element(driver, main)
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/locations.png', (0, main.location['y'] - y_offset, width, min(main.location['y'] + max_height, last_location.location['y'] + last_location.rect['height']) - y_offset))


def unread_notification_icon(base_url, driver):
    sampledb.logic.notifications.create_other_notification(user.id, "This is an example notification.")

    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url)
    navbar = driver.find_element(By.CLASS_NAME, 'navbar-static-top')
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/unread_notification_icon.png', (0, navbar.location['y'], width, min(navbar.location['y'] + max_height, navbar.location['y'] + navbar.rect['height'])))
    notification = sampledb.logic.notifications.get_notifications(user_id=user.id)[0]
    sampledb.logic.notifications.delete_notification(notification.id)


def files(base_url, driver, object):
    object = sampledb.logic.objects.create_object(object.action_id, object.data, user.id, object.id)
    sampledb.logic.files.create_local_file(object.id, user.id, "example.txt", lambda stream: stream.write(b'example text'))
    sampledb.logic.files.create_local_file(object.id, user.id, "notes.pdf", lambda stream: stream.write(b'example text'))
    with open('docs/utils/photo.jpg', 'rb') as image_file:
        sampledb.logic.files.create_local_file(object.id, user.id, "photo.jpg", lambda stream: stream.write(image_file.read()))

    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'objects/{}'.format(object.id))
    for heading in driver.find_elements(By.TAG_NAME, 'h2'):
        if 'Files' in heading.text:
            break
    else:
        assert False
    for form_group in driver.find_elements(By.CLASS_NAME, 'form-group'):
        if 'Upload' in form_group.text:
            break
    else:
        assert False
    wait_until_visible(form_group)
    y_offset = scroll_to_element(driver, heading)

    # this image has caused some issues before, so if the box is empty, print out information on how it was calculated
    # see: https://iffgit.fz-juelich.de/Scientific-IT-Systems/SampleDB/-/issues/11
    height = form_group.rect['height']
    heading_y_location = heading.location['y'] - y_offset
    form_group_y_location = form_group.location['y'] - y_offset
    box = (0, heading_y_location, width, min(heading_y_location + max_height, form_group_y_location + height))
    if not (box[0] >= 0 and box[1] >= 0 and box[2] > 0 and box[3] > 0):
        print('failed to make files visible', file=sys.stderr)
        print('box:', box, file=sys.stderr)
        print('heading_y_location:', heading_y_location, file=sys.stderr)
        print('form_group_y_location:', form_group_y_location, file=sys.stderr)
        print('y_offset:', y_offset, file=sys.stderr)
        print('height:', height, file=sys.stderr)

    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/files.png', box)


def file_information(base_url, driver, object):
    object = sampledb.logic.objects.create_object(object.action_id, object.data, user.id, object.id)
    sampledb.logic.files.create_local_file(object.id, user.id, "notes.pdf", lambda stream: stream.write(b'example text'))
    sampledb.logic.files.update_file_information(object.id, 0, user.id, 'Scanned Notes', 'This is an example file.')

    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'objects/{}'.format(object.id))
    file_table = driver.find_element(By.ID, 'file_table')
    file_table.find_elements(By.CLASS_NAME, 'button-file-info')[0].click()

    modal = wait_until_visible(driver.find_element(By.ID, 'fileInfoModal-0').find_element(By.CLASS_NAME, 'modal-content'))
    y_offset = scroll_to_element(driver, modal)

    # this image has caused some issues before, so if the box is empty, print out information on how it was calculated
    # see: https://iffgit.fz-juelich.de/Scientific-IT-Systems/SampleDB/-/issues/11
    height = modal.rect['height']
    y_location = modal.location['y'] - y_offset
    box = (0, y_location, width, y_location + min(max_height, height))
    if not (box[0] >= 0 and box[1] >= 0 and box[2] > 0 and box[3] > 0):
        print('failed to make file_information visible', file=sys.stderr)
        print('box:', box, file=sys.stderr)
        print('y_location:', y_location, file=sys.stderr)
        print('y_offset:', y_offset, file=sys.stderr)
        print('height:', height, file=sys.stderr)

    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/file_information.png', box)


def labels(base_url, driver, object):
    width = 640
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'objects/{}/label#toolbar=0'.format(object.id))

    # Wait for PDF preview to be visible
    time.sleep(10)

    driver.get_screenshot_as_file('docs/static/img/generated/labels.png')


def hazards_input(base_url, driver, action):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    driver.get(base_url + 'objects/new?action_id={}'.format(action.id))
    for form_group in driver.find_elements(By.CLASS_NAME, 'form-group'):
        if len(form_group.find_elements(By.CLASS_NAME, 'ghs-hazards-selection')) > 0:
            break
    else:
        assert False
    for label in form_group.find_elements(By.TAG_NAME, 'label'):
        if 'Environmental' in label.text:
            break
    else:
        assert False
    label.click()
    for label in form_group.find_elements(By.TAG_NAME, 'label'):
        if 'Corrosive' in label.text:
            break
    else:
        assert False
    label.click()
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/hazards_input.png', (0, form_group.location['y'], width, min(form_group.location['y'] + max_height, form_group.location['y'] + form_group.rect['height'])))


def object_permissions(base_url, driver):
    width = 1280
    min_height = 200
    resize_for_screenshot(driver, width, min_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))

    driver.get(base_url + 'objects/{}/permissions'.format(object.object_id))
    resize_for_screenshot(driver, width, min_height)
    for heading in driver.find_elements(By.TAG_NAME, 'h2'):
        if 'Permissions' in heading.text:
            break
    else:
        assert False
    y_offset = scroll_to_element(driver, heading)
    footer = driver.find_elements(By.TAG_NAME, 'footer')[-1]
    resize_for_screenshot(driver, width, footer.location['y'] - heading.location['y'])
    driver.get_screenshot_as_file('docs/static/img/generated/object_permissions.png')


def advanced_search_by_property(base_url, driver, object):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))

    driver.get(base_url + 'objects/{}'.format(object.id))
    for row in driver.find_elements(By.CLASS_NAME, 'row'):
        if 'Name' in row.text:
            break
    else:
        assert False

    driver.execute_script("var helpers = document.getElementsByClassName('search-helper'); for(var i = 0; i < helpers.length; i++) {helpers[i].style.opacity = 1;}")
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/advanced_search_by_property.png', (0, row.location['y'], width, min(row.location['y'] + max_height, row.location['y'] + row.rect['height'])))


def advanced_search_visualization(base_url, driver):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))

    driver.get(base_url + 'objects/?q=%22Sb%22+in+substance+and+%28temperature+%3C+110degC+or+temperature+%3E+120degC%29&advanced=on')
    search_tree = driver.find_element(By.ID, 'search-tree')

    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/advanced_search_visualization.png', (0, search_tree.location['y'], width, min(search_tree.location['y'] + max_height, search_tree.location['y'] + search_tree.rect['height'])))


def schema_editor(base_url, driver):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))

    driver.get(base_url + 'actions/new/')
    form = wait_until_visible(driver.find_element(By.ID, 'schema-editor'))
    y_offset = scroll_to_element(driver, form)
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/schema_editor.png', (0, form.location['y'] - y_offset, width, form.location['y'] - y_offset + min(max_height, form.rect['height'])))


def disable_schema_editor(base_url, driver):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + f'users/{user.id}/autologin')

    driver.get(base_url + f'users/{user.id}/preferences')
    radio_button = driver.find_element(By.ID, 'input-use-schema-editor-yes')
    parent = radio_button.find_element(By.XPATH, './..')
    while parent is not None:
        if parent.get_attribute('class') == 'form-group':
            form = parent
            break
        else:
            parent = parent.find_element(By.XPATH, './..')
    else:
        assert False
    y_offset = scroll_to_element(driver, form)
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/disable_schema_editor.png', (0, form.location['y'] - y_offset, width, form.location['y'] - y_offset + min(max_height, form.rect['height'])))


def translations(base_url, driver):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(user.id))
    for language in sampledb.logic.languages.get_languages():
        if not language.enabled_for_input:
            sampledb.logic.languages.update_language(
                language_id=language.id,
                names=language.names,
                lang_code=language.lang_code,
                datetime_format_datetime=language.datetime_format_datetime,
                datetime_format_moment=language.datetime_format_moment,
                datetime_format_moment_output=language.datetime_format_moment_output,
                enabled_for_input=True,
                enabled_for_user_interface=True
            )

    driver.get(base_url + 'actions/new/')
    driver.execute_script("""
    $('[data-name="input-names"] .selectpicker').selectpicker('val', ['-99', '-98']);
    $('[data-name="input-names"] .selectpicker').change();
    """)
    form = driver.find_element(By.CSS_SELECTOR, '[data-name="input-names"]')
    y_offset = scroll_to_element(driver, form)
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/translations.png', (0, form.location['y'] - y_offset, width, form.location['y'] - y_offset + min(max_height, form.rect['height'])))


def other_database(base_url, driver):
    width = 1280
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(admin.id))
    driver.get(base_url + 'other-databases/' + str(component.id))
    for heading in driver.find_elements(By.TAG_NAME, 'h3'):
        if 'Database #' + str(component.id) + ': ' + component.name in heading.text:
            break
    else:
        assert False
    y_offset = scroll_to_element(driver, heading)
    last_table = driver.find_elements(By.TAG_NAME, 'table')[-1]

    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/other_database.png', (0, heading.location['y'] - y_offset, width, min(heading.location['y'] + max_height, last_table.location['y'] + last_table.rect['height'])))


def group_categories(base_url, driver, categories):
    width = 300
    max_height = 1000
    resize_for_screenshot(driver, width, max_height)
    driver.get(base_url + 'users/{}/autologin'.format(admin.id))
    driver.get(base_url + 'groups/')
    for category in categories:
        driver.execute_script(f"""
        document.getElementById('groups_list_category_{category.id}_expand').checked = 1;
        """)
    list = driver.find_elements(By.CLASS_NAME, 'groups_list')[0]
    y_offset = scroll_to_element(driver, list)
    save_cropped_screenshot_as_file(driver, 'docs/static/img/generated/group_categories.png', (0, list.location['y'] - y_offset, width, min(list.location['y'] + max_height, list.location['y'] + list.rect['height'])))


def save_cropped_screenshot_as_file(driver, file_name, box):
    image_data = driver.get_screenshot_as_png()
    image = Image.open(io.BytesIO(image_data))
    if box:
        assert box[0] >= 0 and box[1] >= 0 and box[2] > 0 and box[3] > 0
        image = image.crop([c * DEVICE_PIXEL_RATIO for c in box])
        print('cropped screenshot size:', image.size, file=sys.stderr)
    print(f'saving {file_name} (cropped size: {image.size})', file=sys.stderr)
    image.save(file_name)


temp_dir = tempfile.mkdtemp()
try:
    os.mkdir(os.path.join(temp_dir, 'uploaded_files'))
    sampledb.config.FILE_STORAGE_PATH = os.path.join(temp_dir, 'uploaded_files')
    app = tests.conftest.create_app()
    with app.app_context():
        user = sampledb.models.User(
            name="Example User",
            email="example@example.com",
            type=sampledb.models.UserType.PERSON
        )
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        assert user.id is not None

        admin = sampledb.models.User(
            name="Administrator",
            email="admin@example.com",
            type=sampledb.models.UserType.PERSON
        )
        admin.is_admin = True
        sampledb.db.session.add(admin)
        sampledb.db.session.commit()
        assert user.id is not None

        other_user = sampledb.models.User(
            name="Other User",
            email="example@example.com",
            type=sampledb.models.UserType.PERSON
        )
        sampledb.db.session.add(other_user)
        sampledb.db.session.commit()
        assert other_user.id is not None

        group = sampledb.logic.groups.create_group(
            name={"en": "Example Group"},
            description={"en": "An example group for the documentation"},
            initial_user_id=user.id
        )

        group1 = sampledb.logic.groups.create_group(
            name={"en": "Work Group 1"},
            description={"en": ""},
            initial_user_id=user.id
        )
        group2 = sampledb.logic.groups.create_group(
            name={"en": "Work Group 2"},
            description={"en": ""},
            initial_user_id=user.id
        )
        group3 = sampledb.logic.groups.create_group(
            name={"en": "Demo University Students"},
            description={"en": ""},
            initial_user_id=user.id
        )
        category1 = sampledb.logic.group_categories.create_group_category(
            name={
                'en': 'Internal Groups'
            }
        )
        category2 = sampledb.logic.group_categories.create_group_category(
            name={
                'en': 'External Groups'
            }
        )
        category3 = sampledb.logic.group_categories.create_group_category(
            name={
                'en': 'Demo Institute'
            },
            parent_category_id=category1.id
        )
        sampledb.logic.group_categories.set_basic_group_categories(group1.id, (category3.id,))
        sampledb.logic.group_categories.set_basic_group_categories(group2.id, (category3.id,))
        sampledb.logic.group_categories.set_basic_group_categories(group3.id, (category2.id,))

        project = sampledb.logic.projects.create_project(
            name={"en": "Example Project"},
            description={"en": "An example project for the documentation"},
            initial_user_id=user.id
        )

        instrument = sampledb.logic.instruments.create_instrument()
        sampledb.logic.instrument_translations.set_instrument_translation(sampledb.models.Language.ENGLISH,
                                                                          instrument.id,
                                                                          name="Example Instrument",
                                                                          description="This is an example instrument for the documentation.")
        schema = {
            'title': "Sample Information",
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Sample Name',
                    'type': 'text'
                },
                'tags': {
                    'title': 'Tags',
                    'type': 'tags'
                },
                'hazards': {
                    'title': 'GHS Hazards',
                    'type': 'hazards'
                }
            },
            'required': ['name', 'hazards'],
            'propertyOrder': ['name', 'tags', 'hazards']
        }
        instrument_action = sampledb.logic.actions.create_action(
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
            schema=schema,
            instrument_id=instrument.id
        )

        sampledb.logic.action_translations.set_action_translation(
            sampledb.models.Language.ENGLISH,
            instrument_action.id,
            name="Sample Creation",
            description="This is an example action"
        )
        sampledb.logic.action_permissions.set_action_permissions_for_all_users(instrument_action.id, sampledb.models.Permissions.READ)
        data = {
            'name': {
                '_type': 'text',
                'text': 'Demo Sample'
            },
            'tags': {
                '_type': 'tags',
                'tags': ['demo', 'other_tag', 'ombe-1']
            },
            'hazards': {
                '_type': 'hazards',
                'hazards': [5, 9]
            }
        }
        object = sampledb.logic.objects.create_object(
            action_id=instrument_action.id,
            data=data,
            user_id=user.id,
            previous_object_id=None,
            schema=schema
        )

        component = sampledb.logic.components.add_component('28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', 'Example SampleDB', 'https://example.com', 'Example SampleDB instance.')
        sampledb.logic.component_authentication.add_token_authentication(component.id, secrets.token_hex(32), 'Export Token')
        sampledb.logic.component_authentication.add_own_token_authentication(component.id, secrets.token_hex(32), 'Import Token')

        campus = sampledb.logic.locations.create_location(
            name={"en": "Campus A"},
            description={"en": ""},
            parent_location_id=None,
            user_id=user.id,
            type_id=sampledb.logic.locations.LocationType.LOCATION
        )
        building_1 = sampledb.logic.locations.create_location(
            name={"en": "Building 1"},
            description={"en": ""},
            parent_location_id=campus.id,
            user_id=user.id,
            type_id=sampledb.logic.locations.LocationType.LOCATION
        )
        room_42 = sampledb.logic.locations.create_location(
            name={"en": "Room 42"},
            description={"en": "Demo Laboratory"},
            parent_location_id=building_1.id,
            user_id=user.id,
            type_id=sampledb.logic.locations.LocationType.LOCATION
        )
        room_43 = sampledb.logic.locations.create_location(
            name={"en": "Room 43"},
            description={"en": "Demo Storage Room"},
            parent_location_id=building_1.id,
            user_id=user.id,
            type_id=sampledb.logic.locations.LocationType.LOCATION
        )
        sampledb.logic.locations.create_location(
            name={"en": "Box Demo-1"},
            description={"en": ""},
            parent_location_id=room_43.id,
            user_id=user.id,
            type_id=sampledb.logic.locations.LocationType.LOCATION
        )
        sampledb.logic.locations.create_location(
            name={"en": "Box Demo-2"},
            description={"en": ""},
            parent_location_id=room_43.id,
            user_id=user.id,
            type_id=sampledb.logic.locations.LocationType.LOCATION
        )
        sampledb.logic.locations.create_location(
            name={"en": "Box Demo-3"},
            description={"en": ""},
            parent_location_id=room_43.id,
            user_id=user.id,
            type_id=sampledb.logic.locations.LocationType.LOCATION
        )
        for location in sampledb.logic.locations.get_locations():
            sampledb.logic.location_permissions.set_user_location_permissions(
                location_id=location.id,
                user_id=user.id,
                permissions=sampledb.models.Permissions.GRANT
            )

        os.makedirs('docs/static/img/generated', exist_ok=True)
        options = Options()
        options.add_argument("--lang=en-US")
        # disable Chrome sandbox for root in GitLab CI
        if 'CI' in os.environ and getpass.getuser() == 'root':
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-dev-shm-usage')
        with contextlib.contextmanager(tests.conftest.create_flask_server)(app) as flask_server:
            with contextlib.closing(Chrome(options=options)) as driver:
                time.sleep(5)
                object_permissions(flask_server.base_url, driver)
                default_permissions(flask_server.base_url, driver)
                guest_invitation(flask_server.base_url, driver)
                action(flask_server.base_url, driver, instrument_action)
                hazards_input(flask_server.base_url, driver, instrument_action)
                tags_input(flask_server.base_url, driver, object)
                comments(flask_server.base_url, driver, object)
                activity_log(flask_server.base_url, driver, object)
                files(flask_server.base_url, driver, object)
                file_information(flask_server.base_url, driver, object)
                labels(flask_server.base_url, driver, object)
                advanced_search_by_property(flask_server.base_url, driver, object)
                advanced_search_visualization(flask_server.base_url, driver)
                location_assignments(flask_server.base_url, driver, object, room_42)
                locations(flask_server.base_url, driver)
                schema_editor(flask_server.base_url, driver)
                unread_notification_icon(flask_server.base_url, driver)
                disable_schema_editor(flask_server.base_url, driver)
                translations(flask_server.base_url, driver)
                other_database(flask_server.base_url, driver)
                group_categories(flask_server.base_url, driver, [category1, category2, category3])
finally:
    shutil.rmtree(temp_dir)
