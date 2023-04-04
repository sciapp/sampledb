import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located

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


def click_new_property_button(driver):
    new_property_number = driver.execute_script('return $("#form-action .schema-editor-delete-property-button").length;')
    id = f'schema-editor-object__new_property_{new_property_number}-name-input'

    def create_new_property(driver):
        # click button until the new property name input is present
        driver.find_element(By.CSS_SELECTOR, '#form-action .schema-editor-create-property-button').click()
        return presence_of_element_located(driver.find_element(By.ID, id))
    WebDriverWait(driver, 10).until(create_new_property)


def test_create_default_action(flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'actions/new/')

    driver.find_element(By.ID, 'input-name--99').send_keys('Test Action', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[placeholder="Title (English)"]').clear()
    driver.find_element(By.CSS_SELECTOR, '[placeholder="Title (English)"]').send_keys('Test Schema', Keys.TAB)

    driver.find_element(By.NAME, 'action_submit').click()

    action_url = driver.current_url
    assert action_url.startswith(flask_server.base_url + 'actions/')
    action_id = int(action_url[len(flask_server.base_url + 'actions/'):])
    action = sampledb.logic.actions.get_action(action_id)
    action_translation = sampledb.logic.action_translations.get_action_translation_for_action_in_language(action_id, sampledb.logic.languages.Language.ENGLISH)
    assert action_translation.name == 'Test Action'
    assert action.schema == {
        'title': {'en': 'Test Schema'},
        'type': 'object',
        'properties': {
            'name': {
                'title': {'en': 'Name'},
                'type': 'text'
            }
        },
        'required': ['name'],
        'propertyOrder': ['name']
    }
    assert action.user_id == user.id
    assert action.type_id == sampledb.models.ActionType.SAMPLE_CREATION
    assert sampledb.logic.action_permissions.get_action_permissions_for_all_users(action_id) == sampledb.models.Permissions.NONE


def test_create_simple_action(flask_server, driver, user):
    with flask_server.app.app_context():
        # make user admin to allow non-user-specific action
        user.is_admin = True
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        assert user.id is not None
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'actions/new/')
    driver.find_element(By.ID, 'input-name--99').send_keys('Test Action 2', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[placeholder="Title (English)"]').clear()
    driver.find_element(By.CSS_SELECTOR, '[placeholder="Title (English)"]').send_keys('Measurement Information', Keys.TAB)
    driver.find_element(By.NAME, 'is_public').click()
    driver.find_element(By.NAME, 'is_user_specific').click()
    driver.find_element(By.CSS_SELECTOR, '[data-id="input-type"]').click()
    driver.find_element(By.XPATH, '//span[contains(text(), "Measurement")]').click()
    driver.find_element(By.NAME, 'action_submit').click()

    action_url = driver.current_url
    assert action_url.startswith(flask_server.base_url + 'actions/')
    action_id = int(action_url[len(flask_server.base_url + 'actions/'):])
    action = sampledb.logic.actions.get_action(action_id)
    action_translation = sampledb.logic.action_translations.get_action_translation_for_action_in_language(action_id, sampledb.logic.languages.Language.ENGLISH)
    assert action_translation.name == 'Test Action 2'
    assert action.schema == {
        'title': {'en': 'Measurement Information'},
        'type': 'object',
        'properties': {
            'name': {
                'title': {'en': 'Name'},
                'type': 'text'
            }
        },
        'required': ['name'],
        'propertyOrder': ['name']
    }
    assert action.user_id is None
    assert action.type_id == sampledb.models.ActionType.MEASUREMENT
    assert sampledb.logic.action_permissions.get_action_permissions_for_all_users(action_id) == sampledb.models.Permissions.READ


def test_create_complex_action(flask_server, driver, user):
    with flask_server.app.app_context():
        german_language = sampledb.logic.languages.get_language_by_lang_code('de')
        sampledb.logic.languages.update_language(
            language_id=german_language.id,
            names=german_language.names,
            lang_code=german_language.lang_code,
            datetime_format_datetime=german_language.datetime_format_datetime,
            datetime_format_moment=german_language.datetime_format_moment,
            datetime_format_moment_output=german_language.datetime_format_moment_output,
            enabled_for_input=True,
            enabled_for_user_interface=True,
        )
        template_action = sampledb.logic.actions.create_action(
            action_type_id=sampledb.models.ActionType.TEMPLATE,
            schema={
                'title': 'Measurement Information',
                'type': 'object',
                'properties': {
                    'name': {
                        'title': 'Name',
                        'type': 'text'
                    }
                },
                'required': ['name'],
                'propertyOrder': ['name']
            }
        )
        sampledb.logic.action_translations.set_action_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            action_id=template_action.id,
            name='Example Schema Template Action'
        )
        sampledb.logic.action_permissions.set_user_action_permissions(
            action_id=template_action.id,
            user_id=user.id,
            permissions=sampledb.models.Permissions.READ
        )
        assert template_action.id is not None
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'actions/new/')
    driver.find_element(By.ID, 'input-name--99').send_keys('Test Action', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[placeholder="Title (English)"]').clear()
    driver.find_element(By.CSS_SELECTOR, '[placeholder="Title (English)"]').send_keys('Measurement Information', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[placeholder="Title (German)"]').send_keys('Messungsinformationen', Keys.TAB)

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_1-name-input').send_keys('text', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_1-title-input-en').send_keys('Example Text', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_1-title-input-de').send_keys('Beispieltext', Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-placeholder-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-placeholder-input"]').send_keys("Text Placeholder", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-default-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-default-input"]').send_keys("Text Default", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-minlength-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-minlength-input"]').send_keys("2", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-maxlength-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-maxlength-input"]').send_keys("10", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-generic-note-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-generic-note-input-en"]').send_keys("This is a Test", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-generic-note-input-de"]').send_keys("Dies ist ein Test", Keys.TAB)

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_2-name-input').send_keys('multiline_text', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_2-title-input-en').send_keys('Example Multiline Text', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_2-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_2-type-input"]/parent::div/descendant::span[contains(text(), "Text (Multiline)")]').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_2-required-input"]/following::div').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_2-multiline-placeholder-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_2-multiline-placeholder-input"]').send_keys("Multiline Placeholder", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_2-multiline-default-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//textarea[@id="schema-editor-object__new_property_2-multiline-default-input"]').send_keys("Multiline Default Line 1", Keys.ENTER)
    driver.find_element(By.XPATH, '//textarea[@id="schema-editor-object__new_property_2-multiline-default-input"]').send_keys("Multiline Default Line 2", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_2-multiline-minlength-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_2-multiline-minlength-input"]').send_keys("1", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_2-multiline-maxlength-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_2-multiline-maxlength-input"]').send_keys("20", Keys.TAB)

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_3-name-input').send_keys('markdown_text', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_3-title-input-en').send_keys('Example Markdown Text', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_3-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_3-type-input"]/parent::div/descendant::span[contains(text(), "Text (Markdown)")]').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_3-markdown-placeholder-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_3-markdown-placeholder-input"]').send_keys("Markdown Placeholder", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_3-markdown-default-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//textarea[@id="schema-editor-object__new_property_3-markdown-default-input"]').send_keys("Markdown Default Line 1", Keys.ENTER)
    driver.find_element(By.XPATH, '//textarea[@id="schema-editor-object__new_property_3-markdown-default-input"]').send_keys("Markdown Default Line 2", Keys.ENTER)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_3-markdown-minlength-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_3-markdown-minlength-input"]').send_keys("0", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_3-markdown-maxlength-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_3-markdown-maxlength-input"]').send_keys("10", Keys.TAB)

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_4-name-input').send_keys('choices_text', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_4-title-input-en').send_keys('Example Choices Text', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_4-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_4-type-input"]/parent::div/descendant::span[contains(text(), "Text (Choice)")]').click()
    driver.find_element(By.XPATH, '//textarea[@id="schema-editor-object__new_property_4-choice-choices-input"]').send_keys("Choice 1", Keys.ENTER)
    driver.find_element(By.XPATH, '//textarea[@id="schema-editor-object__new_property_4-choice-choices-input"]').send_keys("Choice 2", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_4-choice-default-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_4-choice-default-input"]').send_keys("Choice 1", Keys.TAB)

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_5-name-input').send_keys('quantity', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_5-title-input-en').send_keys('Example Quantity', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_5-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_5-type-input"]/parent::div/descendant::span[contains(text(), "Quantity")]').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_5-quantity-placeholder-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_5-quantity-placeholder-input"]').send_keys("Quantity Placeholder", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_5-quantity-default-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_5-quantity-default-input"]').send_keys("0.1", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_5-quantity-units-input"]').send_keys("m", Keys.TAB)

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_6-name-input').send_keys('boolean', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_6-title-input-en').send_keys('Example Boolean', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_6-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_6-type-input"]/parent::div/descendant::span[contains(text(), "Boolean")]').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_6-bool-default-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_6-bool-default-checkbox"]/ancestor::label/following::div').click()

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_7-name-input').send_keys('datetime', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_7-title-input-en').send_keys('Example Datetime', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_7-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_7-type-input"]/parent::div/descendant::span[contains(text(), "Datetime")]').click()

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_8-name-input').send_keys('sample', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_8-title-input-en').send_keys('Example Sample', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_8-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_8-type-input"]/parent::div/descendant::span[contains(text(), "Sample")]').click()

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_9-name-input').send_keys('measurement', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_9-title-input-en').send_keys('Example Measurement', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_9-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_9-type-input"]/parent::div/descendant::span[contains(text(), "Measurement")]').click()

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_10-name-input').send_keys('user', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_10-title-input-en').send_keys('Example User', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_10-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_10-type-input"]/parent::div/descendant::span[contains(text(), "User")]').click()

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_11-name-input').send_keys('object_reference', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_11-title-input-en').send_keys('Example Object Reference', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_11-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_11-type-input"]/parent::div/descendant::span[contains(text(), "Object Reference")]').click()

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_12-name-input').send_keys('plotly_chart', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_12-title-input-en').send_keys('Example Plotly Chart', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_12-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_12-type-input"]/parent::div/descendant::span[contains(text(), "Plotly Chart")]').click()

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_13-name-input').send_keys('schema_template', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_13-title-input-en').send_keys('Example Schema Template', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_13-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_13-type-input"]/parent::div/descendant::span[contains(text(), "Schema Template")]').click()
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_13-template-id-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_13-template-id-input"]/parent::div/descendant::span[contains(text(), "Example Schema Template Action")]').click()

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_14-name-input').send_keys('timeseries', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_14-title-input-en').send_keys('Example Time Series', Keys.TAB)
    driver.find_element(By.CSS_SELECTOR, '[data-id="schema-editor-object__new_property_14-type-input"]').click()
    driver.find_element(By.XPATH, '//select[@id="schema-editor-object__new_property_14-type-input"]/parent::div/descendant::span[contains(text(), "Time Series")]').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_14-timeseries-units-input"]').send_keys("m", Keys.TAB)

    driver.find_element(By.XPATH, '//input[@id="schema-editor-root-object-tags-input"]/parent::div').click()

    driver.find_element(By.XPATH, '//input[@id="schema-editor-root-object-hazards-input"]/parent::div').click()

    driver.find_element(By.NAME, 'action_submit').click()

    action_url = driver.current_url
    assert action_url.startswith(flask_server.base_url + 'actions/')
    action_id = int(action_url[len(flask_server.base_url + 'actions/'):])
    action = sampledb.logic.actions.get_action(action_id)
    assert action.schema == {
        'title': {
            'en': 'Measurement Information',
            'de': 'Messungsinformationen'
        },
        'type': 'object',
        'properties': {
            'name': {
                'title': {'en': 'Name'},
                'type': 'text'
            },
            'text': {
                'title': {
                    'en': 'Example Text',
                    'de': 'Beispieltext'
                },
                'type': 'text',
                'placeholder': 'Text Placeholder',
                'default': 'Text Default',
                'note': {
                    'en': 'This is a Test',
                    'de': 'Dies ist ein Test'
                },
                'minLength': 2,
                'maxLength': 10
            },
            'multiline_text': {
                'title': {'en': 'Example Multiline Text'},
                'type': 'text',
                'multiline': True,
                'placeholder': 'Multiline Placeholder',
                'default': 'Multiline Default Line 1\nMultiline Default Line 2',
                'minLength': 1,
                'maxLength': 20
            },
            'markdown_text': {
                'title': {'en': 'Example Markdown Text'},
                'type': 'text',
                'markdown': True,
                'placeholder': 'Markdown Placeholder',
                'default': 'Markdown Default Line 1\nMarkdown Default Line 2\n',
                'minLength': 0,
                'maxLength': 10
            },
            'choices_text': {
                'title': {'en': 'Example Choices Text'},
                'type': 'text',
                'choices': ['Choice 1', 'Choice 2'],
                'default': 'Choice 1'
            },
            'quantity': {
                'title': {'en': 'Example Quantity'},
                'type': 'quantity',
                'placeholder': 'Quantity Placeholder',
                'units': 'm',
                'default': 0.1
            },
            'boolean': {
                'title': {'en': 'Example Boolean'},
                'type': 'bool',
                'default': True
            },
            'datetime': {
                'title': {'en': 'Example Datetime'},
                'type': 'datetime'
            },
            'sample': {
                'title': {'en': 'Example Sample'},
                'type': 'sample'
            },
            'measurement': {
                'title': {'en': 'Example Measurement'},
                'type': 'measurement'
            },
            'user': {
                'title': {'en': 'Example User'},
                'type': 'user'
            },
            'plotly_chart': {
                'title': {'en': 'Example Plotly Chart'},
                'type': 'plotly_chart'
            },
            'object_reference': {
                'title': {'en': 'Example Object Reference'},
                'type': 'object_reference'
            },
            'schema_template': {
                'title': {'en': 'Example Schema Template'},
                'type': 'object',
                'template': template_action.id,
                'properties': {},
                'propertyOrder': [],
                'required': []
            },
            'timeseries': {
                'title': {'en': 'Example Time Series'},
                'type': 'timeseries',
                'units': 'm'
            },
            'tags': {
                'title': {
                    'en': 'Tags',
                    'de': 'Tags'
                },
                'type': 'tags'
            },
            'hazards': {
                'title': {
                    'en': 'GHS Hazards',
                    'de': 'GHS Gefahren'
                },
                'type': 'hazards'
            }
        },
        'required': [
            'name',
            'multiline_text',
            'tags',
            'hazards'
        ],
        'propertyOrder': [
            'name',
            'text',
            'multiline_text',
            'markdown_text',
            'choices_text',
            'quantity',
            'boolean',
            'datetime',
            'sample',
            'measurement',
            'user',
            'object_reference',
            'plotly_chart',
            'schema_template',
            'timeseries',
            'tags',
            'hazards'
        ]
    }


def test_create_action_with_json_editor(flask_server, driver, user):
    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + 'actions/new/')
    driver.find_element(By.ID, 'input-name--99').send_keys('Test Action')
    driver.find_element(By.CSS_SELECTOR, '[placeholder="Title (English)"]').clear()
    driver.find_element(By.CSS_SELECTOR, '[placeholder="Title (English)"]').send_keys('Measurement Information')

    click_new_property_button(driver)

    driver.find_element(By.ID, 'schema-editor-object__new_property_1-name-input').send_keys('text', Keys.TAB)
    driver.find_element(By.ID, 'schema-editor-object__new_property_1-title-input-en').send_keys('Example Text', Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-placeholder-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-placeholder-input"]').send_keys("Text Placeholder", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-default-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-default-input"]').send_keys("Text Default", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-minlength-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-minlength-input"]').send_keys("2", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-maxlength-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-text-maxlength-input"]').send_keys("10", Keys.TAB)
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-generic-note-checkbox"]/ancestor::label').click()
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__new_property_1-generic-note-input-en"]').send_keys("This is a Test", Keys.TAB)

    driver.find_element(By.XPATH, '//input[@id="toggle-schema-editor"]/parent::div').click()
    schema_textarea = driver.find_element(By.ID, 'input-schema')
    schema_text = schema_textarea.get_attribute("value")

    assert schema_text.strip() == """
{
    "title": {
        "en": "Measurement Information"
    },
    "type": "object",
    "properties": {
        "name": {
            "title": {
                "en": "Name"
            },
            "type": "text"
        },
        "text": {
            "title": {
                "en": "Example Text"
            },
            "note": {
                "en": "This is a Test"
            },
            "type": "text",
            "default": "Text Default",
            "placeholder": "Text Placeholder",
            "minLength": 2,
            "maxLength": 10
        }
    },
    "required": [
        "name"
    ],
    "propertyOrder": [
        "name",
        "text"
    ]
}
    """.strip()

    schema_textarea.clear()
    schema_textarea.send_keys("""
    {
        "title": "Measurement Information",
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "text": {
                "title": "Example Text",
                "type": "text",
                "default": "Text Default",
                "placeholder": "Text Placeholder",
                "minLength": 2,
                "maxLength": 10
            },
            "user": {
                "title": "Example User",
                "type": "user"
            }
        },
        "required": [
            "name",
            "text"
        ],
        "propertyOrder": [
            "name",
            "text",
            "user"
        ]
    }
    """.strip(), Keys.TAB)

    driver.find_element(By.XPATH, '//input[@id="toggle-schema-editor"]/parent::div').click()

    assert driver.find_element(By.ID, 'schema-editor-object__text-required-input').get_attribute('checked')
    assert not driver.find_element(By.ID, 'schema-editor-object__user-required-input').get_attribute('checked')
    driver.find_element(By.XPATH, '//input[@id="schema-editor-object__user-required-input"]/parent::div').click()

    driver.find_element(By.NAME, 'action_submit').click()

    action_url = driver.current_url
    assert action_url.startswith(flask_server.base_url + 'actions/')
    action_id = int(action_url[len(flask_server.base_url + 'actions/'):])
    action = sampledb.logic.actions.get_action(action_id)
    assert action.schema == {
        "title": {"en": "Measurement Information"},
        "type": "object",
        "properties": {
            "name": {
                "title": {"en": "Name"},
                "type": "text"
            },
            "text": {
                "title": {"en": "Example Text"},
                "type": "text",
                "default": "Text Default",
                "placeholder": "Text Placeholder",
                "minLength": 2,
                "maxLength": 10
            },
            "user": {
                "title": {"en": "Example User"},
                "type": "user"
            }
        },
        "required": [
            "name",
            "text",
            "user"
        ],
        "propertyOrder": [
            "name",
            "text",
            "user"
        ]
    }
