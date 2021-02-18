# coding: utf-8
"""

"""

import pytest

import requests
import requests_mock

import sampledb


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
def action():
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Example Action',
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Sample Name',
                    'type': 'text'
                },
                'array': {
                    'title': 'Array Property',
                    'type': 'array',
                    'items': {
                        'title': 'Object Property',
                        'type': 'object',
                        'properties': {
                            'text': {
                                'title': 'Text Property',
                                'type': 'text',
                                'dataverse_export': True
                            },
                            'quantity': {
                                'title': 'Quantity Property',
                                'type': 'quantity',
                                'units': 'm',
                                'dataverse_export': False
                            },
                            'bool': {
                                'title': 'Boolean Property',
                                'type': 'bool'
                            }
                        }
                    }
                }
            },
            'required': ['name']
        },
        description='',
        instrument_id=None
    )
    return action


def test_get_title(action):
    assert sampledb.logic.dataverse_export.get_title_for_property(
        ['name'],
        action.schema
    ) == 'Sample Name'
    assert sampledb.logic.dataverse_export.get_title_for_property(
        ['array', 0, 'text'],
        action.schema
    ) == 'Array Property → 0 → Text Property'


def test_get_property_export_default(action):
    assert sampledb.logic.dataverse_export.get_property_export_default(
        ['name'],
        action.schema
    ) is True
    assert sampledb.logic.dataverse_export.get_property_export_default(
        ['array', 0, 'text'],
        action.schema
    ) is True
    assert sampledb.logic.dataverse_export.get_property_export_default(
        ['array', 0, 'quantity'],
        action.schema
    ) is False
    assert sampledb.logic.dataverse_export.get_property_export_default(
        ['array', 0, 'bool'],
        action.schema
    ) is False


def test_dataverse_has_required_metadata_blocks():
    with requests_mock.Mocker() as m:
        m.get(
            'mock://dataverse/api/v1/dataverses/valid_dataverse/metadatablocks',
            json={
                'status': 'OK',
                'data': [
                    {
                        'name': 'citation'
                    },
                    {
                        'name': 'process'
                    }
                ]
            }
        )
        m.get(
            'mock://dataverse/api/v1/dataverses/citation_only_dataverse/metadatablocks',
            json={
                'status': 'OK',
                'data': [
                    {
                        'name': 'citation'
                    }
                ]
            }
        )
        m.get(
            'mock://dataverse/api/v1/dataverses/process_only_dataverse/metadatablocks',
            json={
                'status': 'OK',
                'data': [
                    {
                        'name': 'process'
                    }
                ]
            }
        )
        m.get(
            'mock://dataverse/api/v1/dataverses/timeout_dataverse/metadatablocks',
            exc=requests.exceptions.Timeout
        )
        m.get(
            'mock://dataverse/api/v1/dataverses/forbidden_dataverse/metadatablocks',
            status_code=403
        )
        assert sampledb.logic.dataverse_export.dataverse_has_required_metadata_blocks('mock://dataverse', '00000000-0000-0000-0000-000000000000', 'valid_dataverse')
        assert not sampledb.logic.dataverse_export.dataverse_has_required_metadata_blocks('mock://dataverse', '00000000-0000-0000-0000-000000000000', 'citation_only_dataverse')
        assert not sampledb.logic.dataverse_export.dataverse_has_required_metadata_blocks('mock://dataverse', '00000000-0000-0000-0000-000000000000', 'process_only_dataverse')
        assert not sampledb.logic.dataverse_export.dataverse_has_required_metadata_blocks('mock://dataverse', '00000000-0000-0000-0000-000000000000', 'forbidden_dataverse')
        with pytest.raises(sampledb.logic.errors.DataverseNotReachableError):
            sampledb.logic.dataverse_export.dataverse_has_required_metadata_blocks('mock://dataverse', '00000000-0000-0000-0000-000000000000', 'timeout_dataverse')


def test_is_api_token_valid():
    with requests_mock.Mocker() as m:
        m.get(
            'mock://dataverse/api/v1/users/token',
            json={
                'status': 'OK'
            },
            request_headers={
                'X-Dataverse-key': '00000000-0000-0000-0000-000000000000'
            }
        )
        m.get(
            'mock://dataverse/api/v1/users/token',
            json={
                'status': 'Error'
            },
            request_headers={
                'X-Dataverse-key': '00000000-0000-0000-0000-000000000001'
            },
            status_code=403
        )
        assert sampledb.logic.dataverse_export.is_api_token_valid('mock://dataverse', '00000000-0000-0000-0000-000000000000')
        assert not sampledb.logic.dataverse_export.is_api_token_valid('mock://dataverse', '00000000-0000-0000-0000-000000000001')
        assert not sampledb.logic.dataverse_export.is_api_token_valid('mock://dataverse', '00000000-0000-0000-0000-00000000000')
        assert not sampledb.logic.dataverse_export.is_api_token_valid('mock://dataverse', '00000000-0000-0000-0000-00000000000x')
        assert not sampledb.logic.dataverse_export.is_api_token_valid('mock://dataverse', '000000000000000000000000000000000000')


def test_get_user_valid_api_token(user):
    with requests_mock.Mocker() as m:
        m.get(
            'mock://dataverse/api/v1/users/token',
            json={
                'status': 'OK'
            },
            request_headers={
                'X-Dataverse-key': '00000000-0000-0000-0000-000000000000'
            }
        )
        m.get(
            'mock://dataverse/api/v1/users/token',
            json={
                'status': 'Error'
            },
            request_headers={
                'X-Dataverse-key': '00000000-0000-0000-0000-000000000001'
            },
            status_code=403
        )
        assert sampledb.logic.dataverse_export.get_user_valid_api_token('mock://dataverse', user.id) is None
        sampledb.logic.settings.set_user_settings(user.id, {'DATAVERSE_API_TOKEN': '00000000-0000-0000-0000-000000000001'})
        assert sampledb.logic.dataverse_export.get_user_valid_api_token('mock://dataverse', user.id) is None
        sampledb.logic.settings.set_user_settings(user.id, {'DATAVERSE_API_TOKEN': '00000000-0000-0000-0000-000000000000'})
        assert sampledb.logic.dataverse_export.get_user_valid_api_token('mock://dataverse', user.id) == '00000000-0000-0000-0000-000000000000'


def test_export(user, action, tmpdir, app):
    sampledb.logic.files.FILE_STORAGE_PATH = tmpdir

    data = {
        'name': {
            '_type': 'text',
            'text': 'Object'
        },
        'array': [
            {
                'text': {
                    '_type': 'text',
                    'text': 'Text Value'
                }
            }
        ]
    }
    object = sampledb.logic.objects.create_object(user_id=user.id, action_id=action.id, data=data)
    example_file = sampledb.logic.files.create_local_file(object.id, user.id, 'example1.txt', lambda io: io.write(b'Example Content'))
    sampledb.logic.files.create_local_file(object.id, user.id, 'example2.txt', lambda io: io.write(b'Example Content'))
    app.config['SERVER_NAME'] = 'http://localhost'
    with app.app_context():
        with requests_mock.Mocker() as m:
            m.post(
                'mock://dataverse/api/v1/dataverses/example_dataverse/datasets/',
                request_headers={
                    'X-Dataverse-key': '00000000-0000-0000-0000-000000000000'
                },
                status_code=201,
                json={
                    'status': 'OK',
                    'data': {
                        'persistentId': 'TEST'
                    }
                }
            )
            m.post(
                'mock://dataverse/api/datasets/:persistentId/add',
                request_headers={
                    'X-Dataverse-key': '00000000-0000-0000-0000-000000000000'
                },
                status_code=201,
                json={
                    'status': 'OK'
                }
            )
            success, info = sampledb.logic.dataverse_export.upload_object(
                object.id,
                user.id,
                'mock://dataverse',
                '00000000-0000-0000-0000-000000000000',
                'example_dataverse',
                [['array', 0, 'text']],
                [example_file.id]
            )
            assert success
            assert info == 'mock://dataverse/dataset.xhtml?persistentId=TEST'
            assert len(m.request_history) == 2


def test_list_dataverses():
    with requests_mock.Mocker() as m:
        m.get(
            'mock://dataverse/api/v1/dataverses/example_dataverse/contents',
            request_headers={
                'X-Dataverse-key': '00000000-0000-0000-0000-000000000000'
            },
            status_code=200,
            json={
                'status': 'OK',
                'data': [
                    {
                        'type': 'dataverse',
                        'id': 'dataverse_1',
                        'title': 'Dataverse 1'
                    },
                    {
                        'type': 'dataverse',
                        'id': 'dataverse_2',
                        'title': 'Dataverse 2'
                    }
                ]
            }
        )
        m.get(
            'mock://dataverse/api/v1/dataverses/dataverse_1/contents',
            request_headers={
                'X-Dataverse-key': '00000000-0000-0000-0000-000000000000'
            },
            status_code=200,
            json={
                'status': 'OK',
                'data': [
                    {
                        'type': 'dataverse',
                        'id': 'dataverse_1_1',
                        'title': 'Dataverse 1.1'
                    }
                ]
            }
        )
        m.get(
            'mock://dataverse/api/v1/dataverses/dataverse_1_1/contents',
            request_headers={
                'X-Dataverse-key': '00000000-0000-0000-0000-000000000000'
            },
            status_code=403,
            json={
                'status': 'Error'
            }
        )
        m.get(
            'mock://dataverse/api/v1/dataverses/dataverse_2/contents',
            request_headers={
                'X-Dataverse-key': '00000000-0000-0000-0000-000000000000'
            },
            status_code=403,
            json={
                'status': 'Error'
            }
        )
        assert sampledb.logic.dataverse_export.list_dataverses(
            'mock://dataverse',
            '00000000-0000-0000-0000-000000000000',
            'example_dataverse'
        ) == [
            (1, {'id': 'dataverse_1', 'title': 'Dataverse 1'}),
            (2, {'id': 'dataverse_1_1', 'title': 'Dataverse 1.1'}),
            (1, {'id': 'dataverse_2', 'title': 'Dataverse 2'})
        ]


def test_get_dataverse_info():
    with requests_mock.Mocker() as m:
        m.get(
            'mock://dataverse/api/v1/dataverses/example_dataverse',
            request_headers={
                'X-Dataverse-key': '00000000-0000-0000-0000-000000000000'
            },
            status_code=200,
            json={
                'status': 'OK',
                'data': {
                    'id': 'example_dataverse',
                    'name': 'Example Dataverse'
                }
            }
        )
        assert sampledb.logic.dataverse_export.get_dataverse_info(
            'mock://dataverse',
            '00000000-0000-0000-0000-000000000000',
            'example_dataverse'
        ) == {
            'id': 'example_dataverse',
            'title': 'Example Dataverse'
        }
