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
