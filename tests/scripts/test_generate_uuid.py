# coding: utf-8
"""

"""

import uuid

import pytest
import sampledb.__main__ as scripts


def test_generate_uuid(capsys):
    scripts.main([scripts.__file__, 'generate_uuid'])
    uuid_str = capsys.readouterr()[0].rstrip('\n')
    uuid.UUID(uuid_str)     # validates UUID string


def test_generate_uuid_arguments(capsys):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'generate_uuid', 'argument'])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
