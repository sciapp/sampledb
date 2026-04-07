import typing

import pytest

import sampledb.config

@pytest.mark.parametrize(
    ['default_notification_modes', 'should_be_valid'],
    [
        (None, True),
        (
            {
                'DEFAULT': 'WEBAPP'
            },
            True
        ),
        (
            {
                'DEFAULT': 'EMAIL'
            },
            True
        ),
        (
            {
                'DEFAULT': 'IGNORE'
            },
            True
        ),
        (
            {
                'DEFAULT': 'OTHER'
            },
            False
        ),
        (
            {
                'ANNOUNCEMENT': 'WEBAPP'
            },
            True
        ),
        (
            {
                'announcement': 'WEBAPP'
            },
            False
        )
    ]
)
def test_is_default_notification_modes_valid(default_notification_modes: typing.Any, should_be_valid: bool):
    sampledb.config.DEFAULT_NOTIFICATION_MODES = default_notification_modes
    assert sampledb.config.is_default_notification_modes_valid() == should_be_valid

def test_parse_and_convert_external_links():
    config = {}
    config['EXTERNAL_LINKS'] = None
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [None]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"labels": "Example Label", "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"label": 1, "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"label": "", "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"label": "Example Label", "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"label": {"en": "Example Label"}, "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"label": {"en": 1}, "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"label": {1: "Example Label"}, "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"label": {"de": "Example Label"}, "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"icon": ["fa-external-link"], "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"icon": "", "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"icon": "fa-external-link", "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"id_placeholder": "", "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"id_placeholder": 1, "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"id_placeholder": "<ID>", "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"applies_to_placeholder": "", "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"applies_to_placeholder": 1, "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"applies_to_placeholder": "<A>", "links": [{"url": "http://example.com", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": {"url": "http://example.com", "name": {"en": "Example Link"}}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": []}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [[]]}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": {"en": "Example Link"}, "applies_to": {}}]}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [{"url": "", "name": {"en": "Example Link"}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": [{"en": "Example Link"}]}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": {"en": ""}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": {}}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": ""}], "applies_to": {}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": "Example Link"}]}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": "Example Link"}], "applies_to": []}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": "Example Link"}], "applies_to": {"example_links_by_example_id": ['*']}}]
    assert not sampledb.config.parse_and_convert_external_links(config)

    for applies_to_key, config_key in {
        'objects_by_action_id': 'OBJECT_LINKS_BY_ACTION_ID',
        'actions_by_action_id': 'ACTION_LINKS_BY_ACTION_ID',
        'instruments_by_instrument_id': 'INSTRUMENT_LINKS_BY_INSTRUMENT_ID',
        'topics_by_topic_id': 'TOPIC_LINKS_BY_TOPIC_ID',
        'locations_by_location_id': 'LOCATION_LINKS_BY_LOCATION_ID',
        'basic_groups_by_basic_group_id': 'BASIC_GROUP_LINKS_BY_BASIC_GROUP_ID',
        'project_groups_by_project_group_id': 'PROJECT_GROUP_LINKS_BY_PROJECT_GROUP_ID',
    }.items():
        config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": "Example Link"}], "applies_to": {applies_to_key: {}}}]
        assert not sampledb.config.parse_and_convert_external_links(config)
        config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": "Example Link"}], "applies_to": {applies_to_key: ['*', '1']}}]
        assert not sampledb.config.parse_and_convert_external_links(config)
        config['EXTERNAL_LINKS'] = [{"links": [{"url": "http://example.com", "name": "Example Link"}], "applies_to": {applies_to_key: ['*', 1]}}]
        assert sampledb.config.parse_and_convert_external_links(config)

        for other_config_key in [
            'OBJECT_LINKS_BY_ACTION_ID',
            'ACTION_LINKS_BY_ACTION_ID',
            'INSTRUMENT_LINKS_BY_INSTRUMENT_ID',
            'TOPIC_LINKS_BY_TOPIC_ID',
            'LOCATION_LINKS_BY_LOCATION_ID',
            'BASIC_GROUP_LINKS_BY_BASIC_GROUP_ID',
            'PROJECT_GROUP_LINKS_BY_PROJECT_GROUP_ID',
        ]:
            if other_config_key != config_key:
                assert config[other_config_key] == {}
        assert config[config_key] == {
            1: [
                {
                    'applies_to': {
                        applies_to_key: [
                            '*',
                            1,
                        ],
                    },
                    'applies_to_placeholder': '<A>',
                    'icon': 'fa-external-link',
                    'id_placeholder': '<ID>',
                    'label': {
                        'en': 'Links',
                    },
                    'links': [
                        {
                            'name': {
                                'en': 'Example Link',
                            },
                            'url': 'http://example.com',
                        },
                    ],
                },
            ],
            '*': [
                {
                    'applies_to': {
                        applies_to_key: [
                            '*',
                            1,
                        ],
                    },
                    'applies_to_placeholder': '<A>',
                    'icon': 'fa-external-link',
                    'id_placeholder': '<ID>',
                    'label': {
                        'en': 'Links',
                    },
                    'links': [
                        {
                            'name': {
                                'en': 'Example Link',
                            },
                            'url': 'http://example.com',
                        },
                    ],
                },
            ],
        }
