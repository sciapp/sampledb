# coding: utf-8
"""
Logic module handling communication with other components in a SampleDB federation
"""
import typing
import datetime
import io
import flask
import requests

from .utils import _get_dict, _get_list, _get_bool
from .users import import_user, parse_user
from .components import import_component_info, parse_component_info
from .location_types import import_location_type, parse_location_type
from .instruments import import_instrument, parse_instrument
from .action_types import import_action_type, parse_action_type
from .locations import import_location, parse_location, locations_check_for_cyclic_dependencies
from .markdown_images import parse_markdown_image, import_markdown_image
from .actions import import_action, parse_action
from .objects import import_object, parse_object
from ..components import Component, set_component_discoverable
from ..component_authentication import get_own_authentication
from ..users import link_users_by_email_hashes
from ..federation.login import update_metadata
from .. import errors
from ...models import ComponentAuthenticationType

PROTOCOL_VERSION_MAJOR = 0
PROTOCOL_VERSION_MINOR = 1

FEDERATION_TIMEOUT = 60


def _send_request(
        method: typing.Union[typing.Literal['get'], typing.Literal['post'], typing.Literal['put']],
        endpoint: str,
        component: Component,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        **kwargs: typing.Any
) -> requests.Response:
    if component.address is None:
        raise errors.MissingComponentAddressError()
    if headers is None:
        headers = {}
    auth = get_own_authentication(component.id, ComponentAuthenticationType.TOKEN)

    if auth:
        headers['Authorization'] = 'Bearer ' + auth.login['token']

    url = component.address.rstrip('/') + endpoint

    method_callable = {
        'get': requests.get,
        'post': requests.post,
        'put': requests.put,
    }[method]
    return method_callable(  # type: ignore
        url,
        headers=headers,
        timeout=FEDERATION_TIMEOUT,
        **kwargs
    )


def post(
        endpoint: str,
        component: Component,
        payload: typing.Optional[typing.Dict[str, typing.Any]] = None,
        headers: typing.Optional[typing.Dict[str, str]] = None
) -> None:
    _send_request('post', endpoint, component, headers, data=payload)


def put(
        endpoint: str,
        component: Component,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        **kwargs: typing.Any
) -> None:
    _send_request('put', endpoint, component, headers, **kwargs)


def get_binary(
    endpoint: str,
    component: Component,
    headers: typing.Optional[typing.Dict[str, str]] = None
) -> typing.BinaryIO:
    response = _send_request('get', endpoint, component, headers)
    if response.status_code == 401:
        # 401 Unauthorized
        raise errors.UnauthorizedRequestError()
    if response.status_code in [500, 501, 502, 503, 504]:
        raise errors.RequestServerError()
    if response.status_code != 200:
        raise errors.RequestError()
    return io.BytesIO(response.content)


def get(
        endpoint: str,
        component: Component,
        headers: typing.Optional[typing.Dict[str, str]] = None,
        *,
        ignore_last_sync_time: bool = False
) -> typing.Dict[str, typing.Any]:
    if component.address is None:
        raise errors.MissingComponentAddressError()
    if headers is None:
        headers = {}
    auth = get_own_authentication(component.id, ComponentAuthenticationType.TOKEN)

    if auth:
        headers['Authorization'] = 'Bearer ' + auth.login['token']

    parameters = {}
    if component.last_sync_timestamp is not None and not ignore_last_sync_time:
        parameters['last_sync_timestamp'] = component.last_sync_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
    req = requests.get(
        component.address.rstrip('/') + endpoint,
        headers=headers,
        params=parameters,
        timeout=FEDERATION_TIMEOUT
    )
    if req.status_code == 401:
        # 401 Unauthorized
        raise errors.UnauthorizedRequestError()
    if req.status_code in [500, 501, 502, 503, 504]:
        raise errors.RequestServerError()
    if req.status_code != 200:
        raise errors.RequestError()
    try:
        return req.json()  # type: ignore
    except ValueError:
        raise errors.InvalidJSONError()


def update_poke_component(
        component: Component
) -> None:
    post('/federation/v1/hooks/update/', component)


def _validate_header(
        header: typing.Optional[typing.Dict[str, typing.Any]],
        component: Component
) -> None:
    if header is not None:
        if header.get('db_uuid') != component.uuid:
            raise errors.InvalidDataExportError(f'UUID of exporting database ({header.get("db_uuid")}) does not match expected UUID ({component.uuid}).')
        protocol_version = header.get('protocol_version')
        if protocol_version is not None:
            if 'major' not in protocol_version or 'minor' not in protocol_version:
                raise errors.InvalidDataExportError(f'Invalid protocol version \'{header.get("protocol_version")}\'')
            try:
                major, minor = int(protocol_version['major']), int(protocol_version['minor'])
                if major > PROTOCOL_VERSION_MAJOR or (major <= PROTOCOL_VERSION_MAJOR and minor > PROTOCOL_VERSION_MINOR):
                    raise errors.InvalidDataExportError(f'Unsupported protocol version {header.get("protocol_version")}')
            except ValueError:
                raise errors.InvalidDataExportError(f'Invalid protocol version {header.get("protocol_version")}')
        else:
            raise errors.InvalidDataExportError('Missing protocol_version.')


def import_updates(
        component: Component,
        *,
        ignore_last_sync_time: bool = False
) -> None:
    if flask.current_app.config['FEDERATION_UUID'] is None:
        raise errors.ComponentNotConfiguredForFederationError()
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    components = None
    try:
        components = get('/federation/v1/shares/components/', component, ignore_last_sync_time=ignore_last_sync_time)
    except errors.InvalidJSONError:
        raise errors.InvalidDataExportError('Received an invalid JSON string.')
    except errors.RequestServerError:
        pass
    except errors.UnauthorizedRequestError:
        pass
    if components:
        update_components(component, components)
    users = None
    try:
        users = get('/federation/v1/shares/users/', component, ignore_last_sync_time=ignore_last_sync_time)
    except errors.InvalidJSONError:
        raise errors.InvalidDataExportError('Received an invalid JSON string.')
    except errors.RequestServerError:
        pass
    except errors.UnauthorizedRequestError:
        pass
    if users:
        update_users(component, users)
    try:
        updates = get('/federation/v1/shares/objects/', component, ignore_last_sync_time=ignore_last_sync_time)
    except errors.InvalidJSONError:
        raise errors.InvalidDataExportError('Received an invalid JSON string.')
    if updates:
        update_shares(component, updates)

    metadata = get('/federation/v1/shares/metadata/', component)
    if metadata is not None:
        update_metadata(component, metadata)
    component.update_last_sync_timestamp(timestamp)


def update_components(
        component: Component,
        updates: typing.Dict[str, typing.Any]
) -> None:
    _get_dict(updates, mandatory=True)
    _validate_header(updates.get('header'), component)
    discoverable = _get_bool(updates.get('discoverable'), mandatory=True)
    set_component_discoverable(component.id, discoverable=discoverable)
    if discoverable:
        components = []
        component_data_list = _get_list(updates.get('components'), default=[])
        for component_data in component_data_list:
            components.append(parse_component_info(component_data, component))
        for component_data in components:
            if flask.current_app.config['FEDERATION_UUID'] in (component_data['uuid'], component_data['source_uuid']):
                # skip component info from or about this instance
                continue
            import_component_info(component_data, component)


def update_users(
        component: Component,
        updates: typing.Dict[str, typing.Any]
) -> None:
    _get_dict(updates, mandatory=True)
    _validate_header(updates.get('header'), component)

    users = []
    user_data_list = _get_list(updates.get('users'), default=[])
    user_email_hashes = _get_list(updates.get('federation_candidates'), default=[])
    for user_data in user_data_list:
        users.append(parse_user(user_data, component))
    for user_data in users:
        import_user(user_data, component)

    link_users_by_email_hashes(component.id, user_email_hashes)


def update_shares(
        component: Component,
        updates: typing.Dict[str, typing.Any]
) -> None:
    # parse and validate
    _get_dict(updates, mandatory=True)
    _validate_header(updates.get('header'), component)

    markdown_images = []
    markdown_images_data_dict = _get_dict(updates.get('markdown_images'), default={})
    for markdown_image_data in markdown_images_data_dict.items():
        markdown_images.append(parse_markdown_image(markdown_image_data, component))

    users = []
    user_data_list = _get_list(updates.get('users'), default=[])
    for user_data in user_data_list:
        users.append(parse_user(user_data, component))

    instruments = []
    instrument_data_list = _get_list(updates.get('instruments'), default=[])
    for instrument_data in instrument_data_list:
        instruments.append(parse_instrument(instrument_data))

    action_types = []
    action_type_data_list = _get_list(updates.get('action_types'), default=[])
    for action_type_data in action_type_data_list:
        action_types.append(parse_action_type(action_type_data))

    actions = []
    action_data_list = _get_list(updates.get('actions'), default=[])
    for action_data in action_data_list:
        actions.append(parse_action(action_data))

    location_types = []
    location_type_data_list = _get_list(updates.get('location_types'), default=[])
    for location_type_data in location_type_data_list:
        location_types.append(parse_location_type(location_type_data))

    locations = {}
    location_data_list = _get_list(updates.get('locations'), default=[])
    for location_data in location_data_list:
        location = parse_location(location_data)
        locations[(location['fed_id'], location['component_uuid'])] = location

    locations_check_for_cyclic_dependencies(locations)

    objects = []
    object_data_list = _get_list(updates.get('objects'), default=[])
    for object_data in object_data_list:
        objects.append(parse_object(object_data, component))

    # apply
    for markdown_image_data in markdown_images:
        import_markdown_image(markdown_image_data, component)

    for user_data in users:
        import_user(user_data, component)

    for instrument_data in instruments:
        import_instrument(instrument_data, component)

    for action_type_data in action_types:
        import_action_type(action_type_data, component)

    for action_data in actions:
        import_action(action_data, component)

    for location_type_data in location_types:
        import_location_type(location_type_data, component)

    while len(locations) > 0:
        key = list(locations)[0]
        import_location(locations[key], component, locations, users)
        if key in locations:
            locations.pop(key)

    import_status_by_object_id = {}
    for object_data in objects:
        import_status: typing.Dict[str, typing.Any] = {}
        import_object(object_data, component, import_status=import_status)
        import_status_by_object_id[object_data['fed_object_id']] = import_status

    if component.address:
        for object_id, import_status in import_status_by_object_id.items():
            if import_status:
                send_object_share_import_status(
                    object_id=object_id,
                    component=component,
                    import_status=import_status
                )


def send_object_share_import_status(
        object_id: int,
        component: Component,
        import_status: typing.Dict[str, typing.Any]
) -> None:
    put(
        endpoint=f'/federation/v1/shares/objects/{object_id}/import_status',
        component=component,
        json=import_status
    )
