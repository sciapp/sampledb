import pytest
from selenium.webdriver.common.by import By

import sampledb
import sampledb.models
import sampledb.logic


@pytest.fixture
def user(flask_server):
    return sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)


def test_external_links(flask_server, app, driver, user):
    location1 = sampledb.logic.locations.create_location(
        name={"en": "Location 1"},
        description={"en": ""},
        user_id=user.id,
        type_id=sampledb.models.LocationType.LOCATION,
        parent_location_id=None
    )
    sampledb.logic.location_permissions.set_location_permissions_for_all_users(location_id=location1.id, permissions=sampledb.models.Permissions.READ)
    location2 = sampledb.logic.locations.create_location(
        name={"en": "Location 2"},
        description={"en": ""},
        user_id=user.id,
        type_id=sampledb.models.LocationType.LOCATION,
        parent_location_id=None
    )
    sampledb.logic.location_permissions.set_location_permissions_for_all_users(location_id=location2.id, permissions=sampledb.models.Permissions.READ)

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')

    sampledb.frontend.utils.merge_external_links.cache_clear()
    flask_server.app.config['LOCATION_LINKS_BY_LOCATION_ID'] = {
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
        location1.id: [
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

    driver.get(flask_server.base_url + f'locations/{location1.id}')
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

    driver.get(flask_server.base_url + f'locations/{location2.id}')
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
