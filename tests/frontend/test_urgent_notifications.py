import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

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
def object_location_assignment_id(flask_server, user):
    server_name = flask_server.app.config['SERVER_NAME']
    flask_server.app.config['SERVER_NAME'] = 'localhost'
    with flask_server.app.app_context():
        other_user = sampledb.models.User(name="Other User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(other_user)
        sampledb.db.session.commit()
        action = sampledb.logic.actions.create_action(
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
            schema={
                'type': 'object',
                'title': 'Example Schema',
                'properties': {
                    'name': {
                        'type': 'text',
                        'title': 'Text'
                    }
                },
                'required': ['name']
            }
        )
        object = sampledb.logic.objects.create_object(
            action_id=action.id,
            data={
                'name': {
                    '_type': 'text',
                    'text': 'Example Object'
                }
            },
            user_id=other_user.id
        )
        sampledb.logic.object_permissions.set_object_permissions_for_all_users(object.id, sampledb.models.Permissions.READ)
        sampledb.logic.locations.assign_location_to_object(
            object_id=object.id,
            location_id=None,
            responsible_user_id=user.id,
            user_id=other_user.id,
            description=None
        )
        object_location_assignment_id = sampledb.logic.locations.get_object_location_assignments(object.id)[0].id
    flask_server.app.config['SERVER_NAME'] = server_name
    return object_location_assignment_id


def element_stopped_moving(element, element_locations):
    previous_element_location = element_locations.get(element)
    element_locations[element] = element.location
    return element.location == previous_element_location


def test_close_responsibility_assignment(flask_server, driver, user, object_location_assignment_id):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url)
    urgent_notifications_modal = driver.find_element(By.ID, 'urgentNotificationModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: element_stopped_moving(urgent_notifications_modal, element_locations))
    urgent_notifications_modal.find_element(By.CLASS_NAME, 'close').click()
    object_location_assignment = sampledb.logic.locations.get_object_location_assignment(object_location_assignment_id)
    assert not object_location_assignment.confirmed
    assert not object_location_assignment.declined


def test_accept_responsibility_assignment(flask_server, driver, user, object_location_assignment_id):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url)
    urgent_notifications_modal = driver.find_element(By.ID, 'urgentNotificationModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: element_stopped_moving(urgent_notifications_modal, element_locations))
    urgent_notifications_modal.find_element(By.CLASS_NAME, 'btn-primary').click()
    object_location_assignment = sampledb.logic.locations.get_object_location_assignment(object_location_assignment_id)
    assert object_location_assignment.confirmed
    assert not object_location_assignment.declined


def test_decline_responsibility_assignment(flask_server, driver, user, object_location_assignment_id):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url)
    urgent_notifications_modal = driver.find_element(By.ID, 'urgentNotificationModal')
    element_locations = {}
    WebDriverWait(driver, 10).until(lambda driver: element_stopped_moving(urgent_notifications_modal, element_locations))
    urgent_notifications_modal.find_element(By.CLASS_NAME, 'btn-danger').click()
    object_location_assignment = sampledb.logic.locations.get_object_location_assignment(object_location_assignment_id)
    assert not object_location_assignment.confirmed
    assert object_location_assignment.declined
