# coding: utf-8
"""

"""

import json
import os
import pytest
import sampledb
import sampledb.__main__ as scripts


def test_list_local_file_references(flask_server, capsys):
    scripts.main([scripts.__file__, 'list_local_file_references'])
    output = capsys.readouterr()[0]
    assert output == ''
    user = sampledb.logic.users.create_user(name='Example User', email='example@example.org', type=sampledb.models.UserType.PERSON)
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Schema',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
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
        user_id=user.id
    )

    flask_server.app.config['DOWNLOAD_SERVICE_WHITELIST'] = {
        '/example': [user.id]
    }
    sampledb.logic.files.create_local_file_reference(
        object_id=object.id,
        user_id=user.id,
        filepath='/example/example.txt'
    )
    scripts.main([scripts.__file__, 'list_local_file_references'])
    output = capsys.readouterr()[0]
    assert output == f' - object #{object.id} / file #0: /example/example.txt (uploaded by user #{user.id})\n'


def test_list_local_file_references_arguments(capsys):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'list_local_file_references', 1])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
