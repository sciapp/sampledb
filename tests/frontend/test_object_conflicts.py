import copy
import datetime

import pytest
import requests
from selenium.webdriver.common.by import By

import sampledb
import sampledb.models
import sampledb.logic
from ..conftest import wait_for_page_load


UUID1 = "e8e37a3f-ac02-48d4-90cc-585c660e7f59"

DATA = {
    "name": {
        "text": {
            "en": "Test-Object"
        },
        "_type": "text"
    },
    "subobject": {
        "name": {
            "text": {
                "en": "Test-Subobject"
            },
            "_type": "text"
        }
    }
}


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(
            name="Basic User",
            email="example@example.com",
            type=sampledb.models.UserType.PERSON
        )
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return sampledb.logic.users.User.from_database(user)


@pytest.fixture
def action():
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            "title": {
                "en": "Object Information"
            },
            "type": "object",
            "properties": {
                "name": {
                    "type": "text",
                    "title": {
                        "en": "Name"
                    }
                },
                "subobject": {
                    "type": "object",
                    "title": {
                        "en": "Subobject"
                    },
                    "properties": {
                        "name": {
                            "type": "text",
                            "title": {
                                "en": "Subobject – Name"
                            }
                        }
                    }
                }
            },
            "required": [
                "name"
            ],
            "propertyOrder": [
                "name"
            ],
        },
        instrument_id=None
    )
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def object(action, user):
    object = sampledb.logic.objects.create_object(action_id=action.id, data=DATA, user_id=user.id)
    # force attribute refresh
    assert object.id is not None
    return object


@pytest.fixture
def component():
    component = sampledb.models.Component(UUID1, name="Test Component", description="")
    sampledb.db.session.add(component)
    sampledb.db.session.commit()
    # force attribute refresh
    assert component.id is not None
    return sampledb.logic.components.Component.from_database(component)


@pytest.fixture
def component_user(component):
    component_user = sampledb.models.User("Fed User", email="fedexample@example.com", type=sampledb.models.UserType.FEDERATION_USER, component_id=component.id, fed_id=1)
    sampledb.db.session.add(component_user)
    sampledb.db.session.commit()
    # force attribute refresh
    assert component_user.id is not None
    return sampledb.logic.users.User.from_database(component_user)


@pytest.fixture
def conflict(object, component, user, component_user, action):
    data_imported = copy.deepcopy(DATA)
    data_imported["name"]["text"]["en"] = "Imported Version"

    data_local = copy.deepcopy(DATA)
    data_local["name"]["text"]["en"] = "Local Version"

    sampledb.logic.objects.update_object(object_id=object.id, data=data_local, user_id=user.id)
    sampledb.logic.shares.add_object_share(object_id=object.id, component_id=component.id, policy={"access": {"data": True, "files": True, "users": True, "action": True, "comments": True, "object_location_assignments": True}, "permissions": {"users": {"1": "write"}, "groups": {}, "projects": {}, "all_users": "none"}})

    conflicting_object = sampledb.logic.objects.create_conflicting_federated_object(
        object_id=object.id,
        fed_version_id=1,
        version_component_id=component.id,
        data=data_imported,
        schema=action.schema,
        action_id=action.id,
        utc_datetime=datetime.datetime.now(),
        user_id=component_user.id,
        local_parent=object.version_id,
        hash_data=sampledb.logic.federation.conflicts.calculate_data_hash(data_imported, action.schema),
        hash_metadata=sampledb.logic.federation.conflicts.calculate_metadata_hash(user_id=component_user.id, utc_datetime=datetime.datetime.now())
    )

    conflict = sampledb.logic.federation.conflicts.create_object_version_conflict(
        object_id=object.id,
        fed_version_id=conflicting_object.fed_version_id,
        component_id=component.id,
        base_version_id=object.version_id
    )

    return conflict


def test_conflict_accessible(flask_server, user, conflict):
    session = requests.session()
    assert session.get(f'{flask_server.base_url}users/{user.id}/autologin').status_code == 200
    r = session.get(f"{flask_server.base_url}objects")
    assert r.status_code == 200
    assert "fa-exclamation-triangle" in r.text
    r = session.get(f"{flask_server.base_url}objects/{conflict.object_id}")
    assert r.status_code == 200
    assert "Solve Conflicts" in r.text


def test_solve_conflict_apply_local(flask_server, user, conflict):
    session = requests.session()
    assert session.get(f'{flask_server.base_url}users/{user.id}/autologin').status_code == 200
    r = session.post(f"{flask_server.base_url}objects/{conflict.object_id}/conflicts/component/{conflict.component_id}", data={
        "strategy": "apply_local",
    })
    assert r.status_code == 200
    o = sampledb.logic.objects.get_object(object_id=conflict.object_id)
    c = sampledb.logic.federation.conflicts.get_object_version_conflict(
        object_id=conflict.object_id,
        component_id=conflict.component_id,
        fed_version_id=conflict.fed_version_id
    )
    assert c.version_solved_in == o.version_id
    assert c.solver_id == user.id
    modified_data = copy.deepcopy(DATA)
    modified_data['name']['text']['en'] = "Local Version"
    assert o.data == modified_data
    assert not c.discarded


def test_solve_conflict_apply_imported(flask_server, user, conflict):
    session = requests.session()
    assert session.get(f'{flask_server.base_url}users/{user.id}/autologin').status_code == 200
    r = session.post(f"{flask_server.base_url}objects/{conflict.object_id}/conflicts/component/{conflict.component_id}", data={
        "strategy": "apply_imported",
    })
    assert r.status_code == 200
    o = sampledb.logic.objects.get_object(object_id=conflict.object_id)
    c = sampledb.logic.federation.conflicts.get_object_version_conflict(
        object_id=conflict.object_id,
        component_id=conflict.component_id,
        fed_version_id=conflict.fed_version_id
    )
    assert c.version_solved_in == o.version_id
    assert c.solver_id == user.id
    modified_data = copy.deepcopy(DATA)
    modified_data['name']['text']['en'] = "Imported Version"
    assert o.data == modified_data
    assert not c.discarded


def test_solve_conflict_interactive_solving(flask_server, driver, user, conflict):
    driver.get(f"{flask_server.base_url}users/{user.id}/autologin")
    driver.get(f"{flask_server.base_url}objects/{conflict.object_id}?mode=conflict&component_id={conflict.component_id}")

    object_selection = driver.find_element(By.XPATH, "//input[@name=\"object__name__text_en\"]/following-sibling::div")
    assert driver.find_element(By.NAME, "object__name__text_en").get_attribute('value') == "Local Version"
    object_selection.click()
    driver.find_element(By.XPATH, "//button[contains(text(), \"Imported Version\")]").click()
    assert driver.find_element(By.NAME, "object__name__text_en").get_attribute('value') == "Imported Version"

    object_name_field = driver.find_element(By.NAME, "object__name__text_en")
    object_name_field.clear()
    object_name_field.send_keys("Interactive Version")
    assert object_name_field.get_attribute('value') == "Interactive Version"

    with wait_for_page_load(driver):
        driver.find_element(By.NAME, "action_submit").click()

    o = sampledb.logic.objects.get_object(object_id=conflict.object_id)
    c = sampledb.logic.federation.conflicts.get_object_version_conflict(
        object_id=conflict.object_id,
        fed_version_id=conflict.fed_version_id,
        component_id=conflict.component_id
    )
    assert c.version_solved_in == o.version_id
    assert o.data['name']['text']['en'] == "Interactive Version"
    assert c.solver_id == user.id
    assert not c.discarded
