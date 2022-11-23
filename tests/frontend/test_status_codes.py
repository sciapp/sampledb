import copy
import secrets

import flask
import pytest
import requests

import sampledb
import sampledb.models


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        user.is_admin = True
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def _assert_all_routes_are_handled(flask_server, handled_routes, arguments):
    all_routes = set()
    # set known server name to allow repeatable URL generation
    server_name = flask_server.app.config['SERVER_NAME']
    flask_server.app.config['SERVER_NAME'] = 'localhost'
    with flask_server.app.app_context():
        for rule in flask_server.app.url_map.iter_rules():
            if "GET" in rule.methods:
                rule_arguments = dict(rule.defaults or {})
                for argument in rule.arguments:
                    if argument not in rule_arguments:
                        rule_arguments[argument] = arguments[argument]
                argument_combinations = [{}]
                for key, value in rule_arguments.items():
                    if isinstance(value, list):
                        new_argument_combinations = []
                        for combination in argument_combinations:
                            for item in value:
                                new_combination = copy.deepcopy(combination)
                                new_combination[key] = item
                                new_argument_combinations.append(new_combination)
                        argument_combinations = new_argument_combinations
                    else:
                        for combination in argument_combinations:
                            combination[key] = value
                for combination in argument_combinations:
                    url = flask.url_for(rule.endpoint, **combination)
                assert url.startswith('http://localhost/')
                url = url[len('http://localhost/'):]
                all_routes.add(url)
    # ensure there are no unhandled routes
    unhandled_routes = all_routes - set(handled_routes)
    assert len(unhandled_routes) == 0
    flask_server.app.config['SERVER_NAME'] = server_name


def test_status_codes(flask_server, user):
    flask_server.app.config['DATAVERSE_URL'] = 'http://localhost'
    flask_server.app.config['SCICAT_FRONTEND_URL'] = 'http://localhost'
    flask_server.app.config['SCICAT_API_URL'] = 'http://localhost'
    flask_server.app.config['DOWNLOAD_SERVICE_URL'] = 'http://localhost'
    flask_server.app.config['DOWNLOAD_SERVICE_SECRET'] = 'secret'
    with flask_server.app.app_context():
        user_id = user.id
        language_id = sampledb.logic.languages.Language.ENGLISH
        component = sampledb.logic.components.add_component(
            uuid='8bde2cf5-e64c-4bda-beb3-0b448cb90174',
            address='https://localhost',
            name='Test Component'
        )
        component_id = component.id
        token = "invalid"
        static_file_name = 'css/custom.css'
        action_type_id = sampledb.models.ActionType.SAMPLE_CREATION
        action_id = sampledb.logic.actions.create_action(
            action_type_id=action_type_id,
            schema={
                'type': 'object',
                'title': 'Example',
                'properties': {
                    'name': {
                        'type': 'text',
                        'title': 'name'
                    }
                },
                'required': ['name']
            }
        ).id
        sampledb.logic.action_permissions.set_user_action_permissions(
            user_id=user_id,
            action_id=action_id,
            permissions=sampledb.models.Permissions.GRANT
        )
        other_action_id = sampledb.logic.actions.create_action(
            action_type_id=None,
            fed_id=1,
            component_id=component_id,
            schema=None
        ).id
        sampledb.logic.action_permissions.set_user_action_permissions(
            user_id=user_id,
            action_id=other_action_id,
            permissions=sampledb.models.Permissions.READ
        )
        api_token = secrets.token_hex(32)
        sampledb.logic.authentication.add_api_token(user.id, api_token, 'Test API Token')
        api_token_id = sampledb.models.Authentication.query.filter_by(
            type=sampledb.models.AuthenticationType.API_TOKEN
        ).first().id
        sampledb.logic.action_translations.set_action_translation(
            language_id=language_id,
            action_id=action_id,
            name='Test Action'
        )
        instrument_id = sampledb.logic.instruments.create_instrument().id
        sampledb.logic.instruments.set_instrument_responsible_users(
            instrument_id=instrument_id,
            user_ids=[user_id]
        )
        instrument_log_category_id = sampledb.logic.instrument_log_entries.create_instrument_log_category(
            instrument_id=instrument_id,
            title='Test Instrument Log Category',
            theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
        ).id
        instrument_log_entry_id = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
            instrument_id=instrument_id,
            user_id=user_id,
            content='Test Instrument Log Entry'
        ).id
        sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
            instrument_log_entry_id=instrument_log_entry_id,
            file_name='test.txt',
            content=b'test'
        )
        instrument_log_file_attachment_id = sampledb.logic.instrument_log_entries.get_instrument_log_file_attachments(
            instrument_log_entry_id=instrument_log_entry_id
        )[0].id
        object_id = sampledb.logic.objects.create_object(
            action_id=action_id,
            data={
                'name': {
                    '_type': 'text',
                    'text': 'test'
                }
            },
            user_id=user_id
        ).id
        sampledb.logic.instrument_log_entries.create_instrument_log_object_attachment(
            instrument_log_entry_id=instrument_log_entry_id,
            object_id=object_id
        )
        instrument_log_object_attachment_id = sampledb.logic.instrument_log_entries.get_instrument_log_object_attachments(
            instrument_log_entry_id=instrument_log_entry_id
        )[0].id
        location_type_id = sampledb.logic.locations.LocationType.LOCATION
        location_id = sampledb.logic.locations.create_location(
            name={'en': 'Test Location'},
            description={'en': ''},
            parent_location_id=None,
            user_id=user_id,
            type_id=location_type_id
        ).id
        sampledb.logic.location_permissions.set_user_location_permissions(
            location_id=location_id,
            user_id=user_id,
            permissions=sampledb.models.Permissions.GRANT
        )
        comment_id = sampledb.logic.comments.create_comment(
            object_id=object_id,
            user_id=user_id,
            content='Test Comment'
        )
        file_id = sampledb.logic.files.create_database_file(
            object_id=object_id,
            user_id=user_id,
            file_name='test.txt',
            save_content=lambda f: f.write(b'test')
        ).id
        sampledb.logic.locations.assign_location_to_object(
            object_id=object_id,
            location_id=location_id,
            responsible_user_id=user_id,
            user_id=user_id,
            description={'en': ''}
        )
        object_location_assignment_index = 0
        group_id = sampledb.logic.groups.create_group(
            name={'en': 'Test Group'},
            description={'en': ''},
            initial_user_id=user_id
        ).id
        project_id = sampledb.logic.projects.create_project(
            name={'en': 'Test Project'},
            description={'en': ''},
            initial_user_id=user_id
        ).id
        markdown_image_file_name = sampledb.logic.markdown_images.store_temporary_markdown_image(
            content=b'test',
            image_file_extension='.png',
            user_id=user_id
        )
        sampledb.logic.objects.update_object(
            object_id=object_id,
            data={
                'name': {
                    '_type': 'text',
                    'text': 'test'
                }
            },
            user_id=user_id
        )
        other_object_id = sampledb.logic.objects.create_object(
            action_id=other_action_id,
            data={
                'name': {
                    '_type': 'text',
                    'text': 'test'
                }
            },
            schema={
                'type': 'object',
                'title': 'Example',
                'properties': {
                    'name': {
                        'type': 'text',
                        'title': 'name'
                    }
                },
                'required': ['name']
            },
            user_id=user_id
        ).id
        sampledb.logic.instrument_log_entries.create_instrument_log_object_attachment(
            instrument_log_entry_id=instrument_log_entry_id,
            object_id=object_id
        )
        task_id = 1

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    expected_status_codes = {
        '': 200,
        'action_types/': 200,
        f'action_types/{action_type_id}': 200,
        'action_types/new': 200,
        'actions/': 200,
        f'actions/{action_id}': 200,
        f'actions/{other_action_id}': 200,
        f'actions/{action_id}/permissions': 200,
        f'actions/{other_action_id}/permissions': 200,
        'actions/new/': 200,
        'admin/background_tasks/': 200,
        'admin/warnings/': 200,
        'api/v1/action_types/': 200,
        f'api/v1/action_types/{action_type_id}': 200,
        'api/v1/actions/': 200,
        f'api/v1/actions/{action_id}': 200,
        f'api/v1/actions/{other_action_id}': 200,
        'api/v1/instruments/': 200,
        f'api/v1/instruments/{instrument_id}': 200,
        f'api/v1/instruments/{instrument_id}/log_categories/': 200,
        f'api/v1/instruments/{instrument_id}/log_categories/{instrument_log_category_id}': 200,
        f'api/v1/instruments/{instrument_id}/log_entries/': 200,
        f'api/v1/instruments/{instrument_id}/log_entries/{instrument_log_entry_id}': 200,
        f'api/v1/instruments/{instrument_id}/log_entries/{instrument_log_entry_id}/file_attachments/': 200,
        f'api/v1/instruments/{instrument_id}/log_entries/{instrument_log_entry_id}/file_attachments/{instrument_log_file_attachment_id}': 200,
        f'api/v1/instruments/{instrument_id}/log_entries/{instrument_log_entry_id}/object_attachments/': 200,
        f'api/v1/instruments/{instrument_id}/log_entries/{instrument_log_entry_id}/object_attachments/{instrument_log_object_attachment_id}': 200,
        'api/v1/locations/': 200,
        f'api/v1/locations/{location_id}': 200,
        'api/v1/location_types/': 200,
        f'api/v1/location_types/{location_type_id}': 200,
        'api/v1/objects/': 200,
        f'api/v1/objects/{object_id}': 302,
        f'api/v1/objects/{object_id}/comments/': 200,
        f'api/v1/objects/{object_id}/comments/{comment_id}': 200,
        f'api/v1/objects/{object_id}/files/': 200,
        f'api/v1/objects/{object_id}/files/{file_id}': 200,
        f'api/v1/objects/{object_id}/locations/': 200,
        f'api/v1/objects/{object_id}/locations/{object_location_assignment_index}': 200,
        f'api/v1/objects/{object_id}/permissions/anonymous_users': 400,  # 400 because anonymous users are disabled
        f'api/v1/objects/{object_id}/permissions/authenticated_users': 200,
        f'api/v1/objects/{object_id}/permissions/groups/': 200,
        f'api/v1/objects/{object_id}/permissions/groups/{group_id}': 200,
        f'api/v1/objects/{object_id}/permissions/projects/': 200,
        f'api/v1/objects/{object_id}/permissions/projects/{project_id}': 200,
        f'api/v1/objects/{object_id}/permissions/public': 200,
        f'api/v1/objects/{object_id}/permissions/users/': 200,
        f'api/v1/objects/{object_id}/permissions/users/{user_id}': 200,
        f'api/v1/objects/{object_id}/versions/0': 200,
        f'api/v1/objects/{other_object_id}': 302,
        f'api/v1/objects/{other_object_id}/comments/': 200,
        f'api/v1/objects/{other_object_id}/comments/{comment_id}': 404,
        f'api/v1/objects/{other_object_id}/files/': 200,
        f'api/v1/objects/{other_object_id}/files/{file_id}': 404,
        f'api/v1/objects/{other_object_id}/locations/': 200,
        f'api/v1/objects/{other_object_id}/locations/{object_location_assignment_index}': 404,
        f'api/v1/objects/{other_object_id}/permissions/anonymous_users': 400,  # 400 because anonymous users are disabled
        f'api/v1/objects/{other_object_id}/permissions/authenticated_users': 200,
        f'api/v1/objects/{other_object_id}/permissions/groups/': 200,
        f'api/v1/objects/{other_object_id}/permissions/groups/{group_id}': 200,
        f'api/v1/objects/{other_object_id}/permissions/projects/': 200,
        f'api/v1/objects/{other_object_id}/permissions/projects/{project_id}': 200,
        f'api/v1/objects/{other_object_id}/permissions/public': 200,
        f'api/v1/objects/{other_object_id}/permissions/users/': 200,
        f'api/v1/objects/{other_object_id}/permissions/users/{user_id}': 200,
        f'api/v1/objects/{other_object_id}/versions/0': 200,
        'api/v1/users/': 200,
        f'api/v1/users/{user_id}': 200,
        'api/v1/users/me': 200,
        'apple-touch-icon.png': 200,
        'favicon.ico': 200,
        'federation/v1/shares/objects/': 401,  # 401 because federation API requires federation token
        'federation/v1/shares/users/': 401,  # 401 because federation API requires federation token
        'groups/': 200,
        f'groups/{group_id}': 200,
        'instruments/': 200,
        f'instruments/{instrument_id}': 200,
        f'instruments/{instrument_id}/edit': 200,
        f'instruments/{instrument_id}/log/{instrument_log_entry_id}/file_attachments/{instrument_log_file_attachment_id}': 200,
        f'instruments/{instrument_id}/log/mobile_upload/{token}': 400,  # 400 because mobile upload requires valid token
        'instruments/new': 200,
        'language/new': 200,
        'languages/': 200,
        f'languages/{language_id}': 200,
        'locations/': 200,
        f'locations/{location_id}': 200,
        f'locations/{location_id}/permissions': 200,
        'locations/confirm_responsibility': 302,
        'locations/decline_responsibility': 302,
        'locations/new/': 200,
        'location_types/': 200,
        f'location_types/{location_type_id}': 200,
        'location_types/new': 200,
        f'markdown_images/{markdown_image_file_name}': 200,
        f'markdown_images/{component.uuid}/{markdown_image_file_name}': 404,
        'objects/': 200,
        f'objects/{object_id}': 200,
        f'objects/{object_id}/dataverse_export/': 200,
        f'objects/{task_id}/dataverse_export_loading/': 404,
        f'objects/{task_id}/dataverse_export_status/': 404,
        f'objects/{object_id}/dc.rdf': 200,
        f'objects/{object_id}/download_service/': 302,
        f'objects/{object_id}/export': 200,
        f'objects/{object_id}/files/': 200,
        f'objects/{object_id}/files/{file_id}': 200,
        f'objects/{object_id}/files/mobile_upload/{token}': 400,  # 400 because mobile upload requires valid token
        f'objects/{object_id}/label': 200,
        f'objects/{object_id}/permissions': 200,
        f'objects/{object_id}/scicat_export/': 200,
        f'objects/{object_id}/versions/': 200,
        f'objects/{object_id}/versions/0': 200,
        f'objects/{object_id}/versions/0/dc.rdf': 200,
        f'objects/{object_id}/versions/0/restore': 200,
        f'objects/{other_object_id}': 200,
        f'objects/{other_object_id}/dataverse_export/': 200,
        f'objects/{other_object_id}/download_service/': 302,
        f'objects/{other_object_id}/dc.rdf': 200,
        f'objects/{other_object_id}/export': 200,
        f'objects/{other_object_id}/files/': 200,
        f'objects/{other_object_id}/files/{file_id}': 404,
        f'objects/{other_object_id}/files/mobile_upload/{token}': 400,  # 400 because mobile upload requires valid token
        f'objects/{other_object_id}/label': 200,
        f'objects/{other_object_id}/permissions': 200,
        f'objects/{other_object_id}/scicat_export/': 302,
        f'objects/{other_object_id}/versions/': 200,
        f'objects/{other_object_id}/versions/0': 200,
        f'objects/{other_object_id}/versions/0/dc.rdf': 200,
        f'objects/{other_object_id}/versions/0/restore': 404,
        'objects/new': 404,  # 404 because /objects/new requires action_id or previous_object_id
        f'objects/new?action_id={action_id}': 200,
        f'objects/new?action_id={other_action_id}': 302,
        f'objects/new?previous_object_id={object_id}': 200,
        f'objects/new?previous_object_id={other_object_id}': 302,
        'objects/referencable': 200,
        'objects/search/': 200,
        'other-databases/': 200,
        f'other-databases/{component_id}': 200,
        'other-databases/alias/': 200,
        'projects/': 200,
        f'projects/{project_id}': 200,
        f'projects/{project_id}/permissions': 200,
        'publications/': 200,
        f'static/{static_file_name}': 200,
        'status/': 200,
        'tags/': 200,
        'users/': 200,
        f'users/{user_id}': 200,
        f'users/{user_id}/activity': 302,
        f'users/{user_id}/api_token_id/{api_token_id}/log/': 200,
        f'users/{user_id}/export': 200,
        f'users/{user_id}/notifications': 200,
        f'users/{user_id}/preferences': 200,
        'users/create_other_user': 200,
        'users/invitation': 200,
        'users/me': 302,
        'users/me/activity': 302,
        f'users/me/api_token_id/{api_token_id}/log/': 302,
        'users/me/export': 302,
        'users/me/notifications': 302,
        'users/me/preferences': 302,
        'users/me/refresh_sign_in': 302,
        'users/me/sign_in': 302,
        'users/me/sign_out': 200,
        'users/me/two_factor_authentication/totp/confirm': 302,
        'users/me/two_factor_authentication/totp/setup': 200
    }
    for relative_url, expected_status_code in expected_status_codes.items():
        if relative_url.startswith('api/v1/'):
            headers = {
                'Authorization': 'Bearer ' + api_token
            }
        else:
            headers = {}
        assert session.get(
            url=flask_server.base_url + relative_url,
            allow_redirects=False,
            headers=headers
        ).status_code == expected_status_code

    # routes which do not need to be tested, e.g. because they are part of the testing environment
    excluded_routes = [
        f'users/{user_id}/autologin',
        'users/me/loginstatus',
    ]

    handled_routes = list(expected_status_codes.keys()) + excluded_routes
    _assert_all_routes_are_handled(flask_server, handled_routes, {
        'object_id': [object_id, other_object_id],
        'version_id': 0,
        'instrument_id': instrument_id,
        'log_entry_id': instrument_log_entry_id,
        'file_attachment_id': instrument_log_file_attachment_id,
        'object_attachment_id': instrument_log_object_attachment_id,
        'user_id': user_id,
        'group_id': group_id,
        'project_id': project_id,
        'api_token_id': api_token_id,
        'category_id': instrument_log_category_id,
        'object_location_assignment_index': object_location_assignment_index,
        'comment_id': comment_id,
        'file_id': file_id,
        'type_id': action_type_id,
        'location_id': location_id,
        'location_type_id': location_type_id,
        'action_id': [action_id, other_action_id],
        'component': component.uuid,
        'component_id': component_id,
        'language_id': language_id,
        'filename': static_file_name,
        'file_name': markdown_image_file_name,
        'token': token,
        'task_id': task_id,
    })
