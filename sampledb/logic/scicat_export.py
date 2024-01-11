
import datetime
import string
import typing
import uuid
import urllib.parse

import flask
import requests

from .objects import get_object
from .object_permissions import get_user_object_permissions
from .datatypes import DateTime, Quantity, Timeseries
from . import settings, users, errors, utils, files
from ..models import SciCatExport, SciCatExportType, Permissions
from .. import db


SCICAT_TIMEOUT = 30


def get_scicat_url(
        object_id: int
) -> typing.Optional[str]:
    """
    Return the URL for an object in a SciCat instance.

    :param object_id: the ID of an existing object
    :return: the URL or None
    """
    scicat_export: typing.Optional[SciCatExport] = SciCatExport.query.filter_by(object_id=object_id).first()
    if scicat_export is None:
        return None
    return scicat_export.scicat_url


def _convert_metadata(
        data: typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]],
        schema: typing.Dict[str, typing.Any],
        property_whitelist: typing.List[typing.List[typing.Union[str, int]]],
        user_id: int,
        object_id: int
) -> typing.Optional[typing.Union[str, float, int, typing.Dict[str, typing.Any], typing.List[typing.Any]]]:
    if property_whitelist is None:
        property_whitelist = [['name']]

    def _convert_object(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any],
        property_whitelist: typing.List[typing.List[typing.Union[str, int]]],
        object_id: int
    ) -> typing.Dict[str, typing.Any]:
        metadata = {}
        for property_name in schema['properties']:
            if property_name not in data:
                continue
            if not all(c in string.ascii_letters + string.digits + '_' for c in property_name):
                # skip invalid property names
                continue
            sub_property_whitelist = []
            for path in property_whitelist:
                if path and path[0] == property_name:
                    sub_property_whitelist.append(path[1:])
            if not sub_property_whitelist:
                continue
            property_data = data[property_name]
            property_schema = schema['properties'][property_name]
            converted_data = _convert_metadata(property_data, property_schema, sub_property_whitelist, user_id, object_id)
            if converted_data is not None:
                metadata[property_name] = converted_data
        return metadata

    def _convert_array(
        data: typing.List[typing.Any],
        schema: typing.Dict[str, typing.Any],
        property_whitelist: typing.List[typing.List[typing.Union[str, int]]],
        object_id: int
    ) -> typing.List[typing.Any]:
        item_schema = schema['items']
        metadata = []
        for index, item_data in enumerate(data):
            sub_property_whitelist = []
            for path in property_whitelist:
                if path and path[0] == index:
                    sub_property_whitelist.append(path[1:])
            if not sub_property_whitelist:
                continue
            converted_data = _convert_metadata(item_data, item_schema, sub_property_whitelist, user_id, object_id)
            if converted_data is not None:
                metadata.append(converted_data)
        return metadata

    def _convert_timeseries(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any]
    ) -> typing.List[typing.Any]:
        units = data['units']
        rows = data['data']
        metadata = []
        for row in rows:
            utc_datetime_str, magnitude = row[:2]
            utc_datetime_str = datetime.datetime.strptime(utc_datetime_str, Timeseries.DATETIME_FORMAT_STRING).isoformat(timespec='microseconds')
            if units in {'1', ''}:
                value = magnitude
            else:
                value = {
                    'value': str(float(round(magnitude, 13))),
                    'unit': units
                }
            metadata.append({
                'utc_datetime': utc_datetime_str,
                'value': value
            })
        return metadata

    def _convert_datetime(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any]
    ) -> str:
        return datetime.datetime.strptime(data['utc_datetime'], DateTime.FORMAT_STRING).isoformat(timespec='microseconds')

    def _convert_bool(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any]
    ) -> bool:
        return bool(data['value'])

    def _convert_text(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any]
    ) -> str:
        if isinstance(data['text'], dict):
            return str(data['text'].get('en', data['text']))
        if isinstance(data['text'], str):
            return data['text']
        return ''

    def _convert_quantity(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any]
    ) -> typing.Union[float, int, typing.Dict[str, typing.Any]]:
        if data['units'] in {'1', ''}:
            return typing.cast(typing.Union[float, int], data['magnitude_in_base_units'])
        quantity = Quantity.from_json(data)
        return {
            'value': str(float(round(quantity.magnitude, 13))),
            'unit': quantity.units
        }

    def _convert_object_reference(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any]
    ) -> str:
        object_id = data['object_id']
        if Permissions.READ in get_user_object_permissions(object_id=object_id, user_id=user_id):
            raw_object_name = get_object(object_id).name
        else:
            raw_object_name = None
        object_name = utils.get_translated_text(raw_object_name, 'en', f"Object #{object_id}")
        sampledb_object_url = flask.url_for(
            'frontend.object',
            object_id=object_id,
            _external=True
        )
        scicat_export = get_scicat_export_for_object(object_id)
        if scicat_export is None:
            return f"{object_name} ({sampledb_object_url})"
        else:
            return f"{object_name} ({sampledb_object_url} / {scicat_export.scicat_url})"

    def _convert_user(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any]
    ) -> str:
        try:
            user = users.get_user(data['user_id'])
            return user.get_name(include_ref=True)
        except errors.UserDoesNotExistError:
            return f"User #{data['user_id']}"

    def _convert_file(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any],
        object_id: int
    ) -> str:
        try:
            file = files.get_file(data['file_id'], object_id)
            if file.is_hidden:
                return f'Hidden (#{data["file_id"]})'
            else:
                return file.original_file_name
        except errors.FileDoesNotExistError:
            return f'Unknown (#{data["file_id"]})'
        except errors.InvalidFileStorageError:
            return f'Unnamed (#{data["file_id"]})'

    def _convert_hazards(
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any]
    ) -> str:
        hazard_names = {
            1: 'Explosive',
            2: 'Flammable',
            3: 'Oxidizing',
            4: 'Compressed Gas',
            5: 'Corrosive',
            6: 'Toxic',
            7: 'Harmful',
            8: 'Health Hazard',
            9: 'Environmental Hazard'
        }
        return ', '.join(hazard_names[hazard_id] for hazard_id in sorted(data['hazards']))

    if schema['type'] == 'object' and isinstance(data, dict):
        return _convert_object(data, schema, property_whitelist, object_id)
    if schema['type'] == 'array' and isinstance(data, list):
        return _convert_array(data, schema, property_whitelist, object_id)
    if schema['type'] == 'datetime' and isinstance(data, dict):
        return _convert_datetime(data, schema)
    if schema['type'] == 'bool' and isinstance(data, dict):
        return _convert_bool(data, schema)
    if schema['type'] == 'text' and isinstance(data, dict):
        return _convert_text(data, schema)
    if schema['type'] == 'quantity' and isinstance(data, dict):
        return _convert_quantity(data, schema)
    if schema['type'] in {'sample', 'measurement', 'object_reference'} and isinstance(data, dict):
        return _convert_object_reference(data, schema)
    if schema['type'] == 'user' and isinstance(data, dict):
        return _convert_user(data, schema)
    if schema['type'] == 'hazards' and isinstance(data, dict):
        return _convert_hazards(data, schema)
    if schema['type'] == 'timeseries' and isinstance(data, dict):
        return _convert_timeseries(data, schema)
    if schema['type'] == 'file' and isinstance(data, dict):
        return _convert_file(data, schema, object_id)
    if schema['type'] == 'tags':
        # tags are exported as keywords
        return None
    return None


def upload_object(
        object_id: int,
        user_id: int,
        api_url: str,
        frontend_url: str,
        api_token: str,
        property_whitelist: typing.List[typing.List[typing.Union[str, int]]],
        tag_whitelist: typing.List[str],
        object_export_type: SciCatExportType,
        owner_group: str,
        access_groups: typing.Optional[typing.List[str]] = None,
        instrument_pid: typing.Optional[str] = None,
        sample_pid: typing.Optional[str] = None,
        input_dataset_pids: typing.Optional[typing.List[str]] = None
) -> typing.Optional[str]:
    user = users.get_user(user_id)
    object = get_object(object_id)
    original_object_version = get_object(object_id, version_id=0)

    object_url = flask.url_for('frontend.object', object_id=object_id, _external=True)
    pid_prefix = flask.current_app.config["SCICAT_EXTRA_PID_PREFIX"]
    pid_uuid = uuid.uuid4()
    pid = f"{pid_prefix}{pid_uuid}"

    object_name = utils.get_translated_text(object.name, 'en', default=f"Object #{object_id}")

    if object_export_type in {SciCatExportType.RAW_DATASET, SciCatExportType.DERIVED_DATASET}:
        if object_export_type == SciCatExportType.RAW_DATASET:
            api_endpoint = f'{api_url}/api/v3/RawDatasets'
        else:
            api_endpoint = f'{api_url}/api/v3/DerivedDatasets'
        scicat_url = f'{frontend_url}/datasets/{urllib.parse.quote_plus("PID/" + pid)}'
        data: typing.Dict[str, typing.Any] = {
            "pid": pid,
            "datasetName": object_name,
            "owner": user.name,
            "ownerEmail": user.email,
            "ownerGroup": owner_group,
            "contactEmail": user.email,
            "creationTime": original_object_version.utc_datetime.strftime('%Y-%m-%d %H:%M:%S') if original_object_version.utc_datetime else None,
            "description": f"Metadata export from {flask.current_app.config['SERVICE_NAME']} object #{object_id}",
            "sourceFolder": "-",
            "version": str(object.version_id),
            "keywords": [],
            "scientificMetadata": _convert_metadata(object.data, object.schema, property_whitelist, user_id, object.object_id) if object.data is not None and object.schema is not None else {}
        }
        if object_export_type == SciCatExportType.RAW_DATASET:
            data.update({
                "principalInvestigator": "-",
                "creationLocation": object_url,
            })
            if instrument_pid is not None:
                data["instrumentId"] = instrument_pid
            if sample_pid is not None:
                data["sampleId"] = sample_pid
        else:
            if not input_dataset_pids:
                input_dataset_pids = ["-"]
            data.update({
                "investigator": "-",
                "usedSoftware": ["-"],
                "inputDatasets": input_dataset_pids
            })

        if object.schema is not None and object.data is not None and 'tags' in object.schema['properties'] and object.schema['properties']['tags']['type'] == 'tags' and 'tags' in object.data:
            for tag in object.data['tags']['tags']:
                if tag in tag_whitelist:
                    data['keywords'].append(tag)

        if user.orcid:
            data["orcidOfOwner"] = user.orcid

        if access_groups:
            data["accessGroups"] = access_groups
    elif object_export_type == SciCatExportType.SAMPLE:
        api_endpoint = f'{api_url}/api/v3/Samples'
        scicat_url = f'{frontend_url}/samples/{urllib.parse.quote(object_name + " / " + pid, safe="")}'
        data = {
            "sampleId": object_name + " / " + pid,
            "owner": user.name,
            "description": f"Metadata export from {flask.current_app.config['SERVICE_NAME']} object #{object_id}",
            "sampleCharacteristics": _convert_metadata(object.data, object.schema, property_whitelist, user_id, object.object_id) if object.data is not None and object.schema is not None else {},
            "ownerGroup": owner_group
        }

        if access_groups:
            data["accessGroups"] = access_groups
    else:
        return None

    try:
        r = requests.post(
            url=api_endpoint,
            json=[data],
            headers={
                'Authorization': api_token
            },
            timeout=SCICAT_TIMEOUT
        )
    except requests.exceptions.RequestException:
        raise errors.SciCatNotReachableError()
    if r.status_code != 200:
        return None

    db.session.add(SciCatExport(object_id, scicat_url, pid, user_id, object_export_type))
    db.session.commit()
    return scicat_url


def get_user_valid_api_token(api_url: str, user_id: int) -> typing.Optional[str]:
    """
    Return whether a user has a valid API token for a given SciCat instance.

    :param api_url: the base URL of the SciCat API server
    :param user_id: the ID of an existing user
    :return: a valid API token stored for the user, or None
    :raise errors.UserDoesNotExistError: if not user with the given user ID
        exists
    :raise errors.SciCatNotReachableError: if there was an error during
        communication with the SciCat API
    """
    api_token: typing.Optional[str] = settings.get_user_setting(user_id, 'SCICAT_API_TOKEN')
    if not api_token:
        # make sure the user even exists
        users.check_user_exists(user_id)
        return None
    if not is_api_token_valid(api_url, api_token):
        return None
    return api_token


def is_api_token_valid(api_url: str, api_token: str) -> bool:
    """
    Return whether an API token is valid for a given SciCat instance.

    :param api_url: the base URL of the SciCat API server
    :param api_token: the API token to validate
    :return: whether the API token is valid
    :raise errors.SciCatNotReachableError: if there was an error during
        communication with the SciCat API
    """
    # check basic API token structure
    if len(api_token) != 64:
        return False
    if not all(c in (string.ascii_letters + string.digits) for c in api_token):
        return False
    # check whether the API token can actually be used
    try:
        r = requests.get(
            f'{api_url}/api/v3/Datasets/count',
            headers={
                'Authorization': api_token
            },
            allow_redirects=False,
            timeout=SCICAT_TIMEOUT
        )
    except requests.exceptions.RequestException:
        raise errors.SciCatNotReachableError()
    if r.status_code != 200:
        return False
    return True


def get_property_export_default(
        path: typing.List[str],
        schema: typing.Dict[str, typing.Any]
) -> bool:
    """
    Return whether scicat_export is set to True in the schema of a property.

    :param path: the path to a property
    :param schema: the object schema
    :return: the value of scicat_export, or False if it is not set
    """
    if path == ['name']:
        return True
    try:
        subschema = schema
        for key in path:
            if isinstance(key, str):
                subschema = subschema['properties'][key]
            else:
                subschema = subschema['items']
        return bool(subschema.get('scicat_export', False))
        # TODO: allow scicat_export in schemas
    except Exception:
        return False


def get_user_groups(
        api_url: str,
        api_token: str
) -> typing.List[str]:
    """
    Return the list of SciCat groups the current user is in.

    :param api_url: the base URL of the SciCat API server
    :param api_token: the API token to validate
    :return: the list of group names
    :raise errors.SciCatNotReachableError: if there was an error during
        communication with the SciCat API
    """
    try:
        r = requests.get(
            f'{api_url}/api/v3/Users/userInfos',
            headers={
                'Authorization': api_token
            },
            allow_redirects=False,
            timeout=SCICAT_TIMEOUT
        )
    except requests.exceptions.RequestException:
        raise errors.SciCatNotReachableError()
    if r.status_code != 200:
        return []
    try:
        unfiltered_groups = r.json().get('currentGroups')
    except Exception:
        return []
    # remove duplicates, but keep order
    user_groups = []
    for user_group in unfiltered_groups:
        if user_group not in user_groups:
            user_groups.append(user_group)
    return user_groups


def get_instruments(
        api_url: str,
        api_token: str
) -> typing.List[typing.Tuple[str, str]]:
    """
    Return the list of SciCat instruments.

    :param api_url: the base URL of the SciCat API server
    :param api_token: the API token to validate
    :return: the list of instruments as tuples containing pid and name
    :raise errors.SciCatNotReachableError: if there was an error during
        communication with the SciCat API
    """
    try:
        r = requests.get(
            f'{api_url}/api/v3/Instruments',
            headers={
                'Authorization': api_token
            },
            allow_redirects=False,
            timeout=SCICAT_TIMEOUT
        )
    except requests.exceptions.RequestException:
        raise errors.SciCatNotReachableError()
    if r.status_code != 200:
        return []
    return [
        (instrument['pid'], instrument['name'])
        for instrument in r.json()
    ]


def get_scicat_export_for_object(
        object_id: int
) -> typing.Optional[SciCatExport]:
    return SciCatExport.query.filter_by(object_id=object_id).first()


def get_exported_referenced_objects(
        data: typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]],
        schema: typing.Dict[str, typing.Any],
        user_id: int
) -> typing.Set[SciCatExport]:
    exports: typing.Set[SciCatExport] = set()
    if schema['type'] == 'object' and isinstance(data, dict):
        for property_name in schema['properties']:
            if property_name not in data:
                continue
            property_data = data[property_name]
            property_schema = schema['properties'][property_name]
            exports.update(get_exported_referenced_objects(property_data, property_schema, user_id))
    if schema['type'] == 'array' and isinstance(data, list):
        item_schema = schema['items']
        for item_data in data:
            exports.update(get_exported_referenced_objects(item_data, item_schema, user_id))
    if schema['type'] in {'sample', 'measurement', 'object_reference'} and isinstance(data, dict):
        export = get_scicat_export_for_object(data['object_id'])
        if export is not None:
            exports.add(export)
    return exports
