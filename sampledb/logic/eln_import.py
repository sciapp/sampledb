import binascii
import copy
import dataclasses
import datetime
import hashlib
import io
import itertools
import json
import os.path
import string
import typing
import urllib.parse
import zipfile
from urllib.parse import urlsplit

import flask
import requests
from flask_babel import gettext
import minisign

from .. import db
from .utils import parse_url, relative_url_for
from .users import User, create_user, set_user_hidden
from .objects import create_eln_import_object, update_object, get_object
from .actions import create_action
from .action_types import ActionType
from .action_permissions import set_action_permissions_for_all_users
from .action_translations import set_action_translation
from .files import create_url_file, create_database_file, update_file_information
from .comments import create_comment
from .schemas.validate_schema import validate_schema
from .schemas.validate import validate
from . import errors, object_log
from .units import get_unit_for_un_cefact_code, ureg
from ..models import eln_imports, users, Language, Permissions, UserType, Object


@dataclasses.dataclass
class ELNImport:
    id: int
    file_name: str
    user_id: int
    upload_utc_datetime: datetime.datetime
    import_utc_datetime: typing.Optional[datetime.datetime]
    invalid_reason: typing.Optional[str]
    user: User
    signed_by: typing.Optional[str]

    @classmethod
    def from_database(cls, eln_import: eln_imports.ELNImport) -> 'ELNImport':
        return cls(
            id=eln_import.id,
            file_name=eln_import.file_name,
            user_id=eln_import.user_id,
            upload_utc_datetime=eln_import.upload_utc_datetime,
            import_utc_datetime=eln_import.import_utc_datetime,
            invalid_reason=eln_import.invalid_reason,
            user=User.from_database(eln_import.user),
            signed_by=eln_import.signed_by
        )

    @property
    def is_valid(self) -> bool:
        return self.invalid_reason is None

    @property
    def imported(self) -> bool:
        return self.import_utc_datetime is not None


@dataclasses.dataclass(frozen=True)
class ParsedELNComment:
    text: str
    date_created: datetime.datetime
    author_id: typing.Optional[str]


@dataclasses.dataclass(frozen=True)
class ParsedELNVersion:
    version_id: int
    data: typing.Optional[typing.Dict[str, typing.Any]]
    schema: typing.Optional[typing.Dict[str, typing.Any]]
    user_id: typing.Optional[str]
    date_created: typing.Optional[datetime.datetime]


@dataclasses.dataclass(frozen=True)
class ParsedELNDatabaseFile:
    name: str
    title: typing.Optional[str]
    description: typing.Optional[str]
    content: bytes
    user_id: typing.Optional[str]
    date_created: typing.Optional[datetime.datetime]


@dataclasses.dataclass(frozen=True)
class ParsedELNURLFile:
    url: str
    title: typing.Optional[str]
    description: typing.Optional[str]
    user_id: typing.Optional[str]
    date_created: typing.Optional[datetime.datetime]


@dataclasses.dataclass(frozen=True)
class ParsedELNObject:
    id: str
    name: str
    url: typing.Optional[str]
    files: typing.List[typing.Union[ParsedELNURLFile, ParsedELNDatabaseFile]]
    versions: typing.List[ParsedELNVersion]
    comments: typing.List[ParsedELNComment]
    type: typing.Optional[str]
    type_id: typing.Optional[int]


@dataclasses.dataclass(frozen=True)
class ParsedELNUser:
    id: str
    name: typing.Optional[str]
    url: typing.Optional[str]


@dataclasses.dataclass(frozen=True)
class ParsedELNImport:
    objects: typing.List[ParsedELNObject]
    users: typing.List[ParsedELNUser]
    import_notes: typing.Dict[str, typing.List[str]]
    signed_by: typing.Optional[str]


def get_eln_import(eln_import_id: int) -> ELNImport:
    eln_import = eln_imports.ELNImport.query.filter_by(id=eln_import_id).first()
    if eln_import is None:
        raise errors.ELNImportDoesNotExistError()
    return ELNImport.from_database(eln_import)


def create_eln_import(
        user_id: int,
        file_name: str,
        zip_bytes: bytes
) -> ELNImport:
    eln_import = eln_imports.ELNImport(
        user_id=user_id,
        file_name=file_name,
        binary_data=zip_bytes,
        upload_utc_datetime=datetime.datetime.now(datetime.timezone.utc),
        import_utc_datetime=None,
    )
    db.session.add(eln_import)
    db.session.commit()
    return ELNImport.from_database(eln_import)


def delete_eln_import(
        eln_import_id: int
) -> None:
    eln_import = eln_imports.ELNImport.query.filter_by(id=eln_import_id).first()
    if eln_import is None:
        raise errors.ELNImportDoesNotExistError()
    db.session.delete(eln_import)
    db.session.commit()


def mark_eln_import_invalid(
        eln_import_id: int,
        invalid_reason: str
) -> None:
    eln_import = eln_imports.ELNImport.query.filter_by(id=eln_import_id).first()
    if eln_import is None:
        raise errors.ELNImportDoesNotExistError()
    eln_import.invalid_reason = invalid_reason
    db.session.add(eln_import)
    db.session.commit()


def _create_eln_import_action(
        action_type_id: int
) -> eln_imports.ELNImportAction:
    action = create_action(
        action_type_id=action_type_id,
        schema={
            'type': 'object',
            'title': {
                'en': 'Object Information'
            },
            'properties': {
                'name': {
                    'type': 'text',
                    'title': {
                        'en': 'Name'
                    }
                }
            },
            'required': ['name'],
            'propertyOrder': ['name']
        },
        is_hidden=True,
        disable_create_objects=True
    )
    set_action_translation(
        language_id=Language.ENGLISH,
        action_id=action.id,
        name='Import from .eln file',
        description='This action represents importing an object from an .eln file.',
        short_description='This action represents importing an object from an .eln file.'
    )
    set_action_translation(
        language_id=Language.GERMAN,
        action_id=action.id,
        name='Import aus .eln-Datei',
        description='Diese Aktion repräsentiert das Importieren eines Objekts aus einer .eln-Datei.',
        short_description='Diese Aktion repräsentiert das Importieren eines Objekts aus einer .eln-Datei.'
    )
    set_action_permissions_for_all_users(action_id=action.id, permissions=Permissions.READ)
    eln_import_action = eln_imports.ELNImportAction(action_id=action.id, action_type_id=action_type_id)
    db.session.add(eln_import_action)
    db.session.commit()
    return eln_import_action


def import_eln_file(
        eln_import_id: int,
        action_type_ids: typing.Optional[typing.List[typing.Optional[int]]] = None
) -> typing.Tuple[typing.List[int], typing.Dict[typing.Optional[str], User], typing.List[str]]:
    errors = []

    eln_import = eln_imports.ELNImport.query.filter_by(id=eln_import_id).first()
    if eln_import is None:
        return [], {}, ['Unknown ELN import']
    if eln_import.import_utc_datetime is not None:
        return [], {}, ['This ELN file has already been imported']
    user_id = eln_import.user_id

    parsed_data = parse_eln_file(eln_import_id=eln_import_id)
    if action_type_ids is None:
        action_type_ids = []
        for object_info in parsed_data.objects:
            action_type_ids.append(object_info.type_id)
    elif len(action_type_ids) != len(parsed_data.objects):
        return [], {}, ['Invalid Action Type ID information for this ELN file']

    eln_import.import_utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    eln_import.signed_by = parsed_data.signed_by
    db.session.add(eln_import)
    db.session.commit()

    users_by_id: typing.Dict[typing.Optional[str], User] = {}
    for user_info in parsed_data.users:
        user = create_user(
            name=user_info.name,
            email=None,
            type=UserType.ELN_IMPORT_USER,
            eln_import_id=eln_import_id,
            eln_object_id=user_info.id
        )
        set_user_hidden(user.id, True)
        users_by_id[user_info.id] = user
    has_unknown_user = False
    for object_info in parsed_data.objects:
        for file_info in object_info.files:
            if file_info.user_id is None:
                has_unknown_user = True
                break
        for comment_info in object_info.comments:
            if comment_info.author_id is None:
                has_unknown_user = True
                break
    if has_unknown_user:
        user = create_user(
            name='Unknown User',
            email=None,
            type=UserType.ELN_IMPORT_USER,
            eln_import_id=eln_import_id,
            eln_object_id=''
        )
        set_user_hidden(user.id, True)

    action_ids_by_action_type_id: typing.Dict[typing.Optional[int], typing.Optional[int]] = {
        None: None
    }
    for action_type_id in set(action_type_ids):
        if action_type_id is None:
            continue
        eln_import_action = eln_imports.ELNImportAction.query.filter_by(action_type_id=action_type_id).first()
        if eln_import_action is None:
            eln_import_action = _create_eln_import_action(action_type_id)
        action_ids_by_action_type_id[action_type_id] = eln_import_action.action_id
    imported_object_ids = []
    for object_index, object_data in enumerate(zip(parsed_data.objects, action_type_ids)):
        object_info, action_type_id = object_data
        versions_by_id = {
            version_info.version_id: version_info
            for version_info in object_info.versions
        }
        version_ids = list(sorted(versions_by_id.keys()))
        initial_version_info = versions_by_id[version_ids[0]]
        try:
            imported_object = create_eln_import_object(
                importing_user_id=user_id,
                user_id=users_by_id[initial_version_info.user_id].id if initial_version_info.user_id else None,
                action_id=action_ids_by_action_type_id[action_type_id],
                data=initial_version_info.data,
                schema=initial_version_info.schema,
                eln_import_id=eln_import_id,
                eln_object_id=object_info.id,
                utc_datetime=initial_version_info.date_created,
                data_validator_arguments={'file_names_by_id': None, 'strict': False, 'allow_disabled_languages': True}
            )
        except Exception:
            errors.append(f'Failed to import object #{object_index}')
            continue
        if initial_version_info.user_id and initial_version_info.date_created:
            object_log.create_object(
                user_id=users_by_id[initial_version_info.user_id].id,
                object_id=imported_object.object_id,
                utc_datetime=initial_version_info.date_created,
                is_imported=True
            )
        db.session.add(eln_imports.ELNImportObject(
            object_id=imported_object.id,
            eln_import_id=eln_import_id,
            url=object_info.url
        ))
        db.session.commit()
        for version_index, version_id in enumerate(version_ids[1:], start=1):
            version_info = versions_by_id[version_id]
            try:
                update_object(
                    object_id=imported_object.id,
                    data=version_info.data,
                    schema=version_info.schema,
                    user_id=users_by_id[version_info.user_id].id if version_info.user_id else user_id,
                    data_validator_arguments={'file_names_by_id': None, 'strict': False, 'allow_disabled_languages': True},
                    create_log_entries=False,
                    utc_datetime=version_info.date_created
                )
            except Exception:
                errors.append(f'Failed to import object #{object_index} version #{version_index}')
            else:
                if version_info.user_id and version_info.date_created:
                    object_log.edit_object(
                        user_id=users_by_id[version_info.user_id].id,
                        object_id=imported_object.object_id,
                        version_id=version_index,
                        utc_datetime=version_info.date_created,
                        is_imported=True
                    )
        imported_object_ids.append(imported_object.id)
        for file_index, file_info in enumerate(object_info.files):
            file_user_id = user_id
            if isinstance(file_info, ParsedELNDatabaseFile):
                content = file_info.content
                if file_info.user_id:
                    file_user_id = users_by_id[file_info.user_id].id

                def save_content(file: typing.BinaryIO, content: bytes = content) -> None:
                    file.write(content)
                file_id = create_database_file(
                    object_id=imported_object.id,
                    user_id=file_user_id,
                    file_name=file_info.name,
                    save_content=save_content,
                    create_log_entry=False,
                    utc_datetime=file_info.date_created
                ).id
            elif isinstance(file_info, ParsedELNURLFile):
                if file_info.user_id:
                    file_user_id = users_by_id[file_info.user_id].id

                file_id = create_url_file(
                    object_id=imported_object.id,
                    user_id=file_user_id,
                    url=file_info.url,
                    create_log_entry=False,
                    utc_datetime=file_info.date_created
                ).id
            else:
                errors.append(f'Failed to import file #{file_index} for object #{object_index}')
                continue
            if file_info.user_id and file_info.date_created:
                object_log.upload_file(
                    user_id=file_user_id,
                    object_id=imported_object.object_id,
                    file_id=file_id,
                    utc_datetime=file_info.date_created,
                    is_imported=True
                )
            update_file_information(
                object_id=imported_object.id,
                file_id=file_id,
                user_id=file_user_id,
                title=file_info.title or '',
                description=file_info.description or ''
            )
        for comment_info in object_info.comments:
            comment_id = create_comment(
                object_id=imported_object.id,
                user_id=users_by_id[comment_info.author_id].id,
                content=comment_info.text,
                utc_datetime=comment_info.date_created,
                create_log_entry=False
            )
            object_log.post_comment(
                user_id=users_by_id[comment_info.author_id].id,
                object_id=imported_object.object_id,
                comment_id=comment_id,
                utc_datetime=comment_info.date_created,
                is_imported=True
            )
    return imported_object_ids, users_by_id, errors


def _eln_assert(assertion: bool, message: str = 'Invalid .eln file') -> None:
    if not assertion:
        raise errors.InvalidELNFileError(message)


def _json_contains_no_invalid_data(
        json_data: typing.Any
) -> bool:
    """
    Ensure that JSON data contains no invalid data such as strings with NULL bytes.
    """
    if isinstance(json_data, list):
        return all(_json_contains_no_invalid_data(item) for item in json_data)
    if isinstance(json_data, dict):
        return all(_json_contains_no_invalid_data(value) for value in json_data.values())
    if isinstance(json_data, str):
        if '\0' in json_data:
            return False
        return True
    return True


def _parse_eln_import_datetime(datetime_string: str) -> typing.Optional[datetime.datetime]:
    for datetime_format in [
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]:
        try:
            parsed_datetime = datetime.datetime.strptime(datetime_string, datetime_format)
            if parsed_datetime.tzinfo is None:
                utc_datetime = parsed_datetime.replace(tzinfo=datetime.timezone.utc)
            else:
                utc_datetime = parsed_datetime.astimezone(tz=datetime.timezone.utc)
            return utc_datetime
        except Exception:
            continue
    return None


def _parse_author_ref(
        author_ref: typing.Any,
        graph_nodes_by_id: typing.Dict[str, typing.Any]
) -> typing.Optional[str]:
    return _parse_person_ref(
        person_ref=author_ref,
        graph_nodes_by_id=graph_nodes_by_id,
        node_name='author'
    )


def _parse_creator_ref(
        creator_ref: typing.Any,
        graph_nodes_by_id: typing.Dict[str, typing.Any]
) -> typing.Optional[str]:
    return _parse_person_ref(
        person_ref=creator_ref,
        graph_nodes_by_id=graph_nodes_by_id,
        node_name='creator'
    )


def _parse_person_ref(
        person_ref: typing.Any,
        graph_nodes_by_id: typing.Dict[str, typing.Any],
        node_name: str
) -> typing.Optional[str]:
    if person_ref is None:
        return None
    person_id: str
    _eln_assert(isinstance(person_ref, dict), f"Invalid {node_name} reference or node")
    person_ref = typing.cast(typing.Dict[str, typing.Any], person_ref)
    if '@id' in person_ref and person_ref['@id'] in graph_nodes_by_id:
        person_id = person_ref['@id']
        if graph_nodes_by_id[person_id] != person_ref:
            _eln_assert(list(person_ref.keys()) == ['@id'], f"Invalid {node_name} reference")
        person_node = graph_nodes_by_id[person_id]
    else:
        person_node = person_ref
        if '@id' in person_node:
            person_id = person_node['@id']
        else:
            _eln_assert('identifier' in person_node and isinstance(person_node['identifier'], str), f"Invalid {node_name} node")
            person_id = person_node['identifier']
            person_node['@id'] = person_id
        if person_id in graph_nodes_by_id:
            pass
            # TODO: the following check should be performed but is currently omitted to allow importing elabFTW exports, which may contain conflicting user information
            # _eln_assert(graph_nodes_by_id[person_id] == person_node, f"Invalid {node_name} reference")
        else:
            graph_nodes_by_id[person_id] = person_node
    _eln_assert(person_node['@type'] == 'Person', "Reference to node of wrong type")
    return person_id


def _json_has_valid_signature(json_bytes: bytes, signature: minisign.Signature) -> typing.Tuple[bool, typing.Optional[str]]:
    valid_schemes = ["https"]
    if flask.current_app.config["ELN_FILE_IMPORT_ALLOW_HTTP"]:
        valid_schemes.append("http")

    url = signature.trusted_comment

    try:
        split_url = urlsplit(url)
    except ValueError:
        return False, gettext("The signature does not contain a valid URL.")

    if split_url.scheme == "":
        return False, gettext("Missing URL scheme")
    if split_url.scheme not in valid_schemes:
        return False, gettext("Invalid URL scheme: %(scheme)s", scheme=split_url.scheme)
    if split_url.path != "/.well-known/keys.json":
        return False, gettext("The signature does not contain a valid URL pointing to /.well-known/keys.json.")

    try:
        res = requests.get(url, timeout=3)
    except requests.exceptions.ConnectionError:
        return False, gettext("Failed to connect to %(url)s.", url=url)

    if res.status_code != 200:
        return False, gettext("Received an error from %(url)s.", url=url)

    try:
        key_list = res.json()
    except requests.exceptions.JSONDecodeError:
        return False, gettext("%(url)s did not return a valid JSON object.", url=url)

    if isinstance(key_list, dict):
        key_list = [key_list]
    if not isinstance(key_list, list):
        return False, gettext("%(url)s did not return a valid JSON list.", url=url)

    num_failed_keys = 0
    for elem in key_list:
        if not isinstance(elem, dict):
            num_failed_keys += 1
            continue
        if "contentUrl" in elem:
            try:
                response = requests.get(elem['contentUrl'], timeout=3)
            except requests.exceptions.ConnectionError:
                num_failed_keys += 1
                continue
        else:
            num_failed_keys += 1
            continue

        if response.status_code != 200:
            num_failed_keys += 1
            continue

        try:
            pub = minisign.PublicKey.from_base64(response.content)
        except binascii.Error:
            # not in base64 format
            num_failed_keys += 1
            continue
        except ValueError:
            # invalid content, e.g. wrong bytes specifying minisign SignatureAlgorithm
            num_failed_keys += 1
            continue

        try:
            pub.verify(json_bytes, signature)
            return True, None
        except minisign.exceptions.VerifyError:
            continue

    if num_failed_keys > 0:
        return False, gettext(
            "There was an error checking %(num_failed_keys)s of %(num_keys)s public keys. No matching public key was found.",
            num_failed_keys=num_failed_keys,
            num_keys=len(key_list)
        )
    return False, gettext(
        "Successfully fetched all %(num_keys)s keys but no matching public key was found.",
        num_keys=len(key_list)
    )


def parse_eln_file(
        eln_import_id: int
) -> ParsedELNImport:

    eln_import = eln_imports.ELNImport.query.filter_by(id=eln_import_id).first()
    if eln_import is None:
        raise errors.ELNImportDoesNotExistError()
    zip_bytes = eln_import.binary_data

    parsed_data = ParsedELNImport(
        objects=[],
        users=[],
        import_notes={},
        signed_by=None
    )

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
            _eln_assert(zip_file.testzip() is None, ".eln file must be valid .zip file")

            member_names = {
                os.path.normpath(member_name): member_name
                for member_name in zip_file.namelist()
            }
            root_path_names = set()
            for member_name in member_names:
                path_name, file_name = os.path.split(member_name)
                root_path_names.add(path_name.split(os.sep)[0])
            _eln_assert(len(root_path_names) == 1, ".eln file must contain a single root directory")
            root_path_name = list(root_path_names)[0]

            ro_crate_metadata_file_name = root_path_name + '/ro-crate-metadata.json'
            ro_crate_metadata_file_name = os.path.normpath(ro_crate_metadata_file_name)
            _eln_assert(ro_crate_metadata_file_name in member_names, ".eln file must contain ro-crate-metadata.json in its root directory")
            try:
                with zip_file.open(member_names[ro_crate_metadata_file_name]) as ro_crate_metadata_file:
                    ro_crate_metadata = json.load(ro_crate_metadata_file)
            except Exception:
                raise errors.InvalidELNFileError("ro-crate-metadata.json must contain a JSON-encoded object")

            with zip_file.open(root_path_name + '/ro-crate-metadata.json') as ro_crate_metadata_file:
                ro_crate_metadata_bytes = ro_crate_metadata_file.read()

            ro_crate_metadata_sig_file_name = root_path_name + '/ro-crate-metadata.json.minisig'
            ro_crate_metadata_sig_file_name = os.path.normpath(ro_crate_metadata_sig_file_name)
            if ro_crate_metadata_sig_file_name in member_names:
                skip_validation = False
                try:
                    with zip_file.open(member_names[ro_crate_metadata_sig_file_name]) as ro_crate_metadata_sig_bytes:
                        ro_crate_metadata_sig = minisign.Signature.from_bytes(ro_crate_metadata_sig_bytes.read())
                except minisign.ParseError:
                    raise errors.InvalidELNFileError("ro-crate-metadata.json.minisig must contain a minisign signature")
                except Exception:
                    skip_validation = True

                if not skip_validation:
                    has_valid_signature, note = _json_has_valid_signature(ro_crate_metadata_bytes, ro_crate_metadata_sig)
                    if not has_valid_signature and note is not None:
                        parsed_data.import_notes["Signature"] = [note]
                    else:
                        parsed_data = ParsedELNImport(
                            parsed_data.objects,
                            parsed_data.users,
                            parsed_data.import_notes,
                            ro_crate_metadata_sig.trusted_comment.removesuffix("/.well-known/keys.json") if has_valid_signature else None
                        )
            _eln_assert(isinstance(ro_crate_metadata, dict), "ro-crate-metadata.json must contain a JSON-encoded object")
            _eln_assert(_json_contains_no_invalid_data(ro_crate_metadata), "ro-crate-metadata.json must not contain invalid data")
            _eln_assert(ro_crate_metadata.get('@context') == 'https://w3id.org/ro/crate/1.1/context', "ro-crate-metadata.json @context must be RO-Crate 1.1 context")

            _eln_assert(isinstance(ro_crate_metadata.get('@graph'), list), "ro-crate-metadata.json @graph must be list")
            graph_nodes_by_id: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
            for graph_node in ro_crate_metadata['@graph']:
                _eln_assert(isinstance(graph_node, dict), "ro-crate-metadata.json @graph entries must be valid objects")
                _eln_assert(all(isinstance(key, str) for key in graph_node), "ro-crate-metadata.json @graph entries must be valid objects")
                _eln_assert(isinstance(graph_node.get('@id'), str), "ro-crate-metadata.json @graph entries must have string @id")
                _eln_assert(isinstance(graph_node.get('@type'), str) or (isinstance(graph_node.get('@type'), list) and len(graph_node['@type']) >= 1 and all(isinstance(type_entry, str) for type_entry in graph_node['@type'])), "ro-crate-metadata.json @graph entries must have string or list of strings @type")
                _eln_assert(graph_node['@id'] not in graph_nodes_by_id, "ro-crate-metadata.json @graph entries must not have duplicate @id values")
                graph_nodes_by_id[graph_node['@id']] = graph_node

            _eln_assert('./' in graph_nodes_by_id, "ro-crate-metadata.json @graph must contain entry with @id value './'")
            root_node = graph_nodes_by_id['./']
            _eln_assert('ro-crate-metadata.json' in graph_nodes_by_id, "ro-crate-metadata.json @graph must contain entry with @id value 'ro-crate-metadata.json'")
            metadata_node = graph_nodes_by_id['ro-crate-metadata.json']
            _eln_assert(root_node['@type'] == 'Dataset' or root_node['@type'] == ['Dataset'], "ro-crate-metadata.json @graph root node must be Dataset")
            if 'version' in metadata_node:
                supported_ro_crate_versions = [
                    '1.0',
                    '1.1',
                    '1.2',
                ]
                _eln_assert(metadata_node['version'] in supported_ro_crate_versions or any(metadata_node['version'].startswith(supported_ro_crate_version + '.') for supported_ro_crate_version in supported_ro_crate_versions), f"ro-crate-metadata.json node has unsupported RO-Crate version (supported are: {', '.join(supported_ro_crate_versions)})")
            root_sdpublisher = root_node.get('sdPublisher')
            metadata_sdpublisher = metadata_node.get('sdPublisher')
            _eln_assert(isinstance(root_sdpublisher, dict) or isinstance(metadata_sdpublisher, dict), "ro-crate-metadata.json @graph root node or ro-crate-metadata.json node must contain valid sdPublisher")
            _eln_assert(isinstance(root_sdpublisher, dict) or root_sdpublisher is None, "ro-crate-metadata.json @graph root node sdPublisher is invalid")
            _eln_assert(isinstance(metadata_sdpublisher, dict) or metadata_sdpublisher is None, "ro-crate-metadata.json @graph ro-crate-metadata.json node sdPublisher is invalid")
            if root_sdpublisher is not None and metadata_sdpublisher is not None:
                _eln_assert(root_sdpublisher == metadata_sdpublisher, "ro-crate-metadata.json @graph contains conflicting sdPublisher information")
            if root_sdpublisher is not None:
                sdpublisher = root_sdpublisher
            else:
                sdpublisher = metadata_sdpublisher
            _eln_assert(all(isinstance(key, str) for key in sdpublisher), "ro-crate-metadata.json @graph sdPublisher is invalid")
            if set(sdpublisher.keys()) == {'@id'}:
                _eln_assert(isinstance(sdpublisher['@id'], str), "ro-crate-metadata.json @graph sdPublisher is invalid")
                sdpublisher = graph_nodes_by_id.get(sdpublisher['@id'])
                _eln_assert(isinstance(sdpublisher, dict), "ro-crate-metadata.json @graph sdPublisher is invalid")
                sdpublisher = typing.cast(typing.Dict[str, typing.Any], sdpublisher)
                _eln_assert(all(isinstance(key, str) for key in sdpublisher), "ro-crate-metadata.json @graph sdPublisher is invalid")
            _eln_assert(sdpublisher.get('@type') == 'Organization', "ro-crate-metadata.json @graph sdPublisher is invalid")
            if sdpublisher.get('name') == 'SampleDB':
                eln_dialect = 'SampleDB'
            else:
                eln_dialect = None
            _eln_assert('hasPart' in root_node, "ro-crate-metadata.json @graph root node must have parts")
            if not isinstance(root_node['hasPart'], list):
                root_node['hasPart'] = [root_node['hasPart']]

            for object_node_ref in root_node['hasPart']:
                _eln_assert(isinstance(object_node_ref, dict), "Invalid reference")
                _eln_assert(list(object_node_ref.keys()) == ['@id'], "Invalid reference")
                _eln_assert(object_node_ref['@id'] in graph_nodes_by_id, "Reference to unknown ID")

                object_node = graph_nodes_by_id[object_node_ref['@id']]
                _eln_assert(isinstance(object_node.get('name'), str), "Missing name for Dataset")
                name = object_node['name']

                parsed_data.import_notes[object_node["@id"]] = []

                _eln_assert(isinstance(object_node.get('description', ''), (str, dict)), "Invalid description for Dataset")
                description = object_node.get('description', '')
                if isinstance(description, dict):
                    if list(description.keys()) == ['@id']:
                        _eln_assert(description['@id'] in graph_nodes_by_id, "Reference to unknown ID")
                        description = graph_nodes_by_id[description['@id']]
                    _eln_assert(isinstance(object_node_ref, dict), "Invalid description")
                    _eln_assert(description.get('@type') == 'TextObject', "Invalid description for Dataset")
                    description_is_markdown = description.get('encodingFormat') == 'text/markdown'
                    description = description.get('text', '')
                else:
                    description_is_markdown = False

                if 'url' in object_node:
                    _eln_assert(isinstance(object_node.get('url'), str), "Invalid URL for Dataset")
                    try:
                        url = object_node['url']
                        parse_url(url, valid_schemes=('http', 'https'))
                    except Exception:
                        raise errors.InvalidELNFileError("Invalid URL for Dataset")
                else:
                    url = None
                if eln_dialect == 'SampleDB':
                    _eln_assert(object_node_ref['@id'].startswith('./objects/'), "Invalid @id for Dataset for SampleDB .eln file")
                    try:
                        original_object_id_str = object_node_ref['@id'][len('./objects/'):].rstrip('/')
                        original_object_id = int(original_object_id_str)
                        _eln_assert(str(original_object_id) == original_object_id_str and original_object_id > 0, "Invalid @id for Dataset for SampleDB .eln file")
                    except ValueError:
                        _eln_assert(False, "Invalid @id for Dataset for SampleDB .eln file")
                    _eln_assert(isinstance(url, str), "Invalid url for Dataset for SampleDB .eln file")
                    _eln_assert(url.endswith(object_node_ref['@id'].rstrip('/')[1:]), "Invalid url for Dataset for SampleDB .eln file")
                    eln_source_url = url[:-len(object_node_ref['@id'][2:])]
                else:
                    eln_source_url = None

                if object_node.get('genre') in {'sample', 'measurement', 'simulation', 'experiment', 'procedure'}:
                    object_type = {
                        'experiment': 'measurement',
                        'procedure': 'measurement'
                    }.get(object_node['genre'], object_node['genre'])
                    object_type_id = {
                        'sample': ActionType.SAMPLE_CREATION,
                        'measurement': ActionType.MEASUREMENT,
                        'simulation': ActionType.SIMULATION,
                    }.get(object_type)
                else:
                    object_type = None
                    object_type_id = None

                if 'comment' in object_node and not isinstance(object_node['comment'], list):
                    object_node['comment'] = [object_node['comment']]
                comments: typing.List[ParsedELNComment] = []
                for comment_ref in object_node.get('comment', []):
                    _eln_assert(isinstance(comment_ref, dict), "Invalid comment reference or node")
                    if '@id' in comment_ref and comment_ref['@id'] in graph_nodes_by_id:
                        _eln_assert(list(comment_ref.keys()) == ['@id'], "Invalid comment reference")
                        comment_node = graph_nodes_by_id[comment_ref['@id']]
                    else:
                        comment_node = comment_ref
                    author_ref = comment_node.get('author')
                    if author_ref is None:
                        author_id = None
                    else:
                        _eln_assert(isinstance(author_ref, dict), "Invalid author reference or node")
                        author_ref = typing.cast(typing.Dict[str, typing.Any], author_ref)
                        if '@id' in author_ref and author_ref['@id'] in graph_nodes_by_id:
                            author_id = author_ref['@id']
                            if graph_nodes_by_id[author_id] != author_ref:
                                _eln_assert(list(author_ref.keys()) == ['@id'], "Invalid author reference")
                            author_node = graph_nodes_by_id[author_id]
                        else:
                            author_node = author_ref
                            if '@id' in author_node:
                                author_id = author_node['@id']
                            else:
                                _eln_assert('identifier' in author_node, "Invalid author node")
                                author_id = author_node['identifier']
                                author_node['@id'] = author_id
                            if author_id in graph_nodes_by_id:
                                pass
                                # TODO: the following check should be performed but is currently omitted to allow importing elabFTW exports, which may contain conflicting user information
                                # _eln_assert(graph_nodes_by_id[author_id] == author_node, "Invalid author reference")
                            else:
                                graph_nodes_by_id[author_id] = author_node
                        _eln_assert(author_node['@type'] == 'Person', "Reference to node of wrong type")
                    _eln_assert(isinstance(comment_node.get('text'), str), "Invalid text for Comment")
                    _eln_assert(isinstance(comment_node.get('dateCreated'), str), "Invalid dateCreated for Comment")
                    date_created: typing.Optional[datetime.datetime]
                    try:
                        date_created = datetime.datetime.fromisoformat(comment_node['dateCreated'])
                    except Exception:
                        raise errors.InvalidELNFileError("Invalid dateCreated for Comment")
                    comments.append(ParsedELNComment(
                        text=comment_node['text'],
                        date_created=date_created,
                        author_id=author_id
                    ))

                files: typing.List[typing.Union[ParsedELNURLFile, ParsedELNDatabaseFile]] = []
                versions: typing.List[ParsedELNVersion] = []

                fallback_data = {
                    'name': {
                        '_type': 'text',
                        'text': {'en': name}
                    }
                }
                if description:
                    fallback_data['description'] = {
                        '_type': 'text',
                        'text': {'en': description},
                    }
                    if description_is_markdown:
                        fallback_data['description']['is_markdown'] = True  # type: ignore[assignment]
                fallback_schema = {
                    'type': 'object',
                    'title': {
                        'en': 'Object Information',
                        'de': 'Objektinformationen',
                    },
                    'properties': {
                        'name': {
                            'type': 'text',
                            'title': {
                                'en': 'Name',
                                'de': 'Name'
                            }
                        }
                    },
                    'required': ['name'],
                    'propertyOrder': ['name']
                }
                fallback_schema_properties = typing.cast(typing.Dict[str, typing.Any], fallback_schema['properties'])
                fallback_schema_property_order = typing.cast(typing.List[str], fallback_schema['propertyOrder'])
                if description:
                    fallback_schema_properties['description'] = {
                        'type': 'text',
                        'title': {
                            'en': 'Description',
                            'de': 'Beschreibung'
                        },
                        'multiline': '\n' in description
                    }
                    if description_is_markdown:
                        fallback_schema_properties['description']['multiline'] = False
                        fallback_schema_properties['description']['markdown'] = True
                    fallback_schema_property_order.append('description')
                has_metadata = False
                if 'keywords' in object_node:
                    fallback_schema_properties['tags'] = {
                        'type': 'tags',
                        'title': {
                            'en': 'Tags',
                            'de': 'Tags'
                        }
                    }
                    fallback_schema_property_order.append('tags')
                    if isinstance(object_node['keywords'], list):
                        keywords = [
                            keyword
                            for keyword in object_node['keywords']
                            if isinstance(keyword, str)
                        ]
                    elif isinstance(object_node['keywords'], str):
                        keywords = [
                            keyword
                            for keyword in object_node['keywords'].split(',')
                        ]
                    else:
                        keywords = []
                    tags = []
                    for keyword in keywords:
                        keyword = keyword.strip().lower()
                        # skip duplicate tags
                        if keyword in tags:
                            continue
                        # skip tags with invalid characters
                        if any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-äöüß' for c in keyword):
                            continue
                        # skip numeric tags unless enabled
                        if all(c in string.digits for c in keyword) and not flask.current_app.config['ENABLE_NUMERIC_TAGS']:
                            continue
                        tags.append(keyword)
                    fallback_data['tags'] = {
                        '_type': 'tags',
                        'tags': tags
                    }
                else:
                    tags = []
                if 'variableMeasured' in object_node and object_node['variableMeasured'] is not None:
                    if not isinstance(object_node['variableMeasured'], list):
                        object_node['variableMeasured'] = [object_node['variableMeasured']]
                    has_metadata = True
                    property_values = []
                    for property_value in object_node['variableMeasured']:
                        _eln_assert(isinstance(property_value, dict), "Invalid variableMeasured item for Dataset")
                        if '@id' in property_value and property_value['@id'] in graph_nodes_by_id:
                            property_value = graph_nodes_by_id[property_value['@id']]
                        # skip untyped variableMeasured entries, e.g. used by elabFTW for elabftw_metadata
                        if '@type' not in property_value:
                            continue
                        _eln_assert(property_value.get('@type') == 'PropertyValue', "Invalid variableMeasured item type for Dataset")
                        _eln_assert(isinstance(property_value.get('propertyID'), str), "Invalid variableMeasured item propertyID for Dataset")
                        _eln_assert(isinstance(property_value.get('name', ''), str), "Invalid variableMeasured item name for Dataset")
                        _eln_assert(isinstance(property_value.get('value'), (str, bool, int, float)), "Invalid variableMeasured item value for Dataset")
                        _eln_assert(isinstance(property_value.get('unitCode', ''), str), "Invalid variableMeasured item unitCode for Dataset")
                        _eln_assert(isinstance(property_value.get('unitText', ''), str), "Invalid variableMeasured item unitText for Dataset")
                        property_values.append(property_value)
                    fallback_data, fallback_schema = _convert_property_values_to_data_and_schema(
                        property_values=property_values,
                        name=name,
                        description=description,
                        description_is_markdown=description_is_markdown,
                        tags=tags
                    )
                if 'hasPart' in object_node and not isinstance(object_node['hasPart'], list):
                    object_node['hasPart'] = [object_node['hasPart']]
                for object_part_ref in object_node.get('hasPart', []):
                    _eln_assert(isinstance(object_part_ref, dict), "Invalid reference")
                    _eln_assert(list(object_part_ref.keys()) == ['@id'], "Invalid reference")
                    _eln_assert(object_part_ref['@id'] in graph_nodes_by_id, "Reference to unknown ID")
                    object_part = graph_nodes_by_id[object_part_ref['@id']]
                    if object_part['@type'] == 'File':
                        _eln_assert(isinstance(object_part.get('name'), str), "Invalid name for File")
                        if 'description' in object_part:
                            description = object_part.get('description')
                            if isinstance(description, dict):
                                if list(description.keys()) == ['@id']:
                                    _eln_assert(description['@id'] in graph_nodes_by_id, "Reference to unknown ID")
                                    description = graph_nodes_by_id[description['@id']]
                                _eln_assert(isinstance(object_node_ref, dict), "Invalid description")
                                _eln_assert(description.get('@type') == 'TextObject', "Invalid description for File")
                                description = description.get('text', '')
                            else:
                                _eln_assert(isinstance(object_part.get('description'), str), "Invalid description for File")
                        file_path = object_part['@id']
                        try:
                            file_url_parse_result = urllib.parse.urlparse(file_path)
                        except ValueError:
                            file_url_parse_result = None
                        if file_url_parse_result is not None and file_url_parse_result.netloc and file_url_parse_result.scheme in ('http', 'https'):
                            file_url = object_part.get('url', file_path)
                            try:
                                parse_url(file_url, valid_schemes=('http', 'https'))
                            except Exception:
                                parsed_data.import_notes[object_node["@id"]].append(gettext('Failed to import %(file_url)s as URL file', file_url=file_url))
                            else:
                                date_created = None
                                if 'dateCreated' in object_part:
                                    _eln_assert(isinstance(object_part.get('dateCreated'), str), "Invalid dateCreated for File")
                                    date_created = _parse_eln_import_datetime(object_part['dateCreated'])
                                author_ref = object_part.get('author')
                                author_id = _parse_author_ref(author_ref, graph_nodes_by_id)
                                files.append(ParsedELNURLFile(
                                    url=file_url,
                                    title=object_part.get('name'),
                                    description=description,
                                    user_id=author_id,
                                    date_created=date_created
                                ))
                            continue
                        if file_path.startswith('./'):
                            file_path = file_path[1:]
                        elif not file_path.startswith('/'):
                            file_path = '/' + file_path
                        file_path = root_path_name + file_path
                        file_path = os.path.normpath(file_path)
                        _eln_assert(file_path in member_names, "File not found in .eln file (1)")
                        file_name = os.path.split(file_path)[1]
                        with zip_file.open(member_names[file_path]) as file:
                            file_data = file.read()
                        if isinstance(object_part.get('contentSize'), str):
                            try:
                                object_part['contentSize'] = int(object_part['contentSize'])
                            except ValueError:
                                pass
                        _eln_assert(isinstance(object_part.get('contentSize'), int), "Invalid content size for File")
                        _eln_assert(len(file_data) == object_part['contentSize'], "Content size mismatch for File")
                        if 'sha256' in object_part:
                            _eln_assert(isinstance(object_part.get('sha256'), str), "Invalid SHA256 hash for File")
                            _eln_assert(hashlib.sha256(file_data).hexdigest() == object_part['sha256'], "Hash mismatch for File")
                        if eln_dialect == 'SampleDB' and object_part['@id'] == object_node_ref['@id'] + ('/' if not object_node_ref['@id'].endswith('/') else '') + 'files.json':
                            try:
                                files_info = json.loads(file_data.decode('utf-8'))
                            except Exception:
                                raise errors.InvalidELNFileError("Invalid files.json for SampleDB .eln file")
                            _eln_assert(isinstance(files_info, list), "Invalid files.json for SampleDB .eln file")
                            for file_info in files_info:
                                _eln_assert(isinstance(file_info, dict), "Invalid files.json for SampleDB .eln file")
                                if 'url' not in file_info:
                                    continue
                                _eln_assert(isinstance(file_info.get('url'), str), "Invalid URL file for SampleDB .eln file")
                                _eln_assert(isinstance(file_info.get('title'), str) or file_info.get('title') is None, "Invalid URL file for SampleDB .eln file")
                                _eln_assert(isinstance(file_info.get('description'), str) or file_info.get('description') is None, "Invalid URL file for SampleDB .eln file")
                                _eln_assert(isinstance(file_info.get('uploader_id'), int), "Invalid URL file for SampleDB .eln file")
                                author_sampledb_id = file_info.get('uploader_id')
                                try:
                                    file_url = file_info['url']
                                    parse_url(file_url, valid_schemes=('http', 'https'))
                                except Exception:
                                    raise errors.InvalidELNFileError("Invalid URL file for SampleDB .eln file")
                                try:
                                    date_created = datetime.datetime.strptime(file_info.get('utc_datetime', ''), '%Y-%m-%dT%H:%M:%S.%f')
                                    date_created = date_created.replace(tzinfo=datetime.timezone.utc)
                                except Exception:
                                    date_created = None
                                files.append(ParsedELNURLFile(
                                    url=file_url,
                                    title=file_info.get('title'),
                                    description=file_info.get('description'),
                                    user_id=f'./users/{author_sampledb_id}',
                                    date_created=date_created
                                ))
                        else:
                            date_created = None
                            if 'dateCreated' in object_part:
                                _eln_assert(isinstance(object_part.get('dateCreated'), str), "Invalid dateCreated for File")
                                date_created = _parse_eln_import_datetime(object_part['dateCreated'])
                            author_ref = object_part.get('author')
                            author_id = _parse_author_ref(author_ref, graph_nodes_by_id)
                            files.append(ParsedELNDatabaseFile(
                                name=file_name,
                                title=object_part['name'],
                                description=object_part.get('description'),
                                content=file_data,
                                user_id=author_id,
                                date_created=date_created,
                            ))
                    if eln_dialect == 'SampleDB' and object_part['@type'] == 'Dataset':
                        _eln_assert(any(object_part['@id'].startswith(object_node['@id'] + ('/' if not object_node['@id'].endswith('/') else '') + version_suffix) for version_suffix in ('version/', 'versions/')), "SampleDB .eln file must only contain versions as Dataset parts of objects")
                        try:
                            version_id = int(object_part['@id'].strip('/').rsplit('/', maxsplit=1)[1])
                        except ValueError:
                            raise errors.InvalidELNFileError("SampleDB .eln file must only contain versions as Dataset parts of objects")
                        _eln_assert(isinstance(object_part.get('hasPart'), list), "SampleDB .eln file must contain data and schema for each version")
                        _eln_assert(len(object_part['hasPart']) == 2, "SampleDB .eln file must contain data and schema for each version")
                        _eln_assert({'@id': object_part['@id'] + ('/' if not object_part['@id'].endswith('/') else '') + 'data.json'} in object_part['hasPart'], "SampleDB .eln file must contain data and schema for each version")
                        _eln_assert({'@id': object_part['@id'] + ('/' if not object_part['@id'].endswith('/') else '') + 'schema.json'} in object_part['hasPart'], "SampleDB .eln file must contain data and schema for each version")
                        data_file_name = object_part['@id'] + '/data.json'
                        if data_file_name.startswith('./'):
                            data_file_name = data_file_name[1:]
                        elif not data_file_name.startswith('/'):
                            data_file_name = '/' + data_file_name
                        data_file_name = root_path_name + data_file_name
                        data_file_name = os.path.normpath(data_file_name)
                        _eln_assert(data_file_name in member_names, "SampleDB .eln file must contain data and schema for each version")
                        schema_file_name = object_part['@id'] + '/schema.json'
                        if schema_file_name.startswith('./'):
                            schema_file_name = schema_file_name[1:]
                        elif not schema_file_name.startswith('/'):
                            schema_file_name = '/' + schema_file_name
                        schema_file_name = root_path_name + schema_file_name
                        schema_file_name = os.path.normpath(schema_file_name)
                        _eln_assert(schema_file_name in member_names, "SampleDB .eln file must contain data and schema for each version")
                        try:
                            with zip_file.open(member_names[data_file_name]) as data_file:
                                data_file_content = data_file.read()
                                _eln_assert(isinstance(graph_nodes_by_id[object_part['@id'] + 'data.json'].get('sha256'), str), "Invalid SHA256 hash for data.json")
                                _eln_assert(hashlib.sha256(data_file_content).hexdigest() == graph_nodes_by_id[object_part['@id'] + 'data.json']['sha256'], "Hash mismatch for data.json")
                                version_data = json.loads(data_file_content.decode('utf-8'))
                            with zip_file.open(member_names[schema_file_name]) as schema_file:
                                schema_file_content = schema_file.read()
                                _eln_assert(isinstance(graph_nodes_by_id[object_part['@id'] + 'schema.json'].get('sha256'), str), "Invalid SHA256 hash for schema.json")
                                _eln_assert(hashlib.sha256(schema_file_content).hexdigest() == graph_nodes_by_id[object_part['@id'] + 'schema.json']['sha256'], "Hash mismatch for schema.json")
                                version_schema = json.loads(schema_file_content.decode('utf-8'))
                        except errors.InvalidELNFileError:
                            raise
                        except Exception:
                            raise errors.InvalidELNFileError("SampleDB .eln file must contain data and schema for each version")
                        creator_ref = object_part.get('creator')
                        if creator_ref is None and isinstance(object_part.get('author'), dict):
                            creator_ref = object_part.get('author')
                        creator_id = _parse_creator_ref(creator_ref, graph_nodes_by_id)
                        date_created = None
                        if 'dateCreated' in object_part:
                            _eln_assert(isinstance(object_part.get('dateCreated'), str), "Invalid dateCreated for Dataset")
                            date_created = _parse_eln_import_datetime(object_part['dateCreated'])
                        if version_schema is None or version_data is None:
                            versions.append(ParsedELNVersion(
                                version_id=version_id,
                                data=None,
                                schema=None,
                                user_id=creator_id,
                                date_created=date_created
                            ))
                            parsed_data.import_notes[object_node["@id"]].append(gettext('Missing data or schema for version %(version_id)s of object %(eln_object_id)s', version_id=version_id, eln_object_id=object_node['@id']))
                        else:
                            _remove_template_ids(version_schema)
                            _replace_references(version_data, eln_source_url)
                            try:
                                validate_schema(version_schema, strict=False)
                                validate(version_data, version_schema, allow_disabled_languages=True, strict=False, file_names_by_id=None)
                                versions.append(ParsedELNVersion(
                                    version_id=version_id,
                                    data=version_data,
                                    schema=version_schema,
                                    user_id=creator_id,
                                    date_created=date_created
                                ))
                            except errors.ValidationError as e:
                                versions.append(ParsedELNVersion(
                                    version_id=version_id,
                                    data=fallback_data,
                                    schema=fallback_schema,
                                    user_id=creator_id,
                                    date_created=date_created
                                ))
                                parsed_data.import_notes[object_node["@id"]].append(gettext('Invalid data or schema in version %(version_id)s of object %(eln_object_id)s (%(error)s)', version_id=version_id, eln_object_id=object_node['@id'], error=e))
                if not versions:
                    creator_ref = object_node.get('creator')
                    if creator_ref is None and isinstance(object_node.get('author'), dict):
                        creator_ref = object_node.get('author')
                    creator_id = _parse_creator_ref(creator_ref, graph_nodes_by_id)
                    date_created = None
                    if 'dateCreated' in object_node:
                        _eln_assert(isinstance(object_node.get('dateCreated'), str), "Invalid dateCreated for Dataset")
                        date_created = _parse_eln_import_datetime(object_node['dateCreated'])
                    if not has_metadata:
                        fallback_data['import_note'] = {
                            '_type': 'text',
                            'text': {
                                'en': 'The .eln file did not contain any valid flexible metadata for this object.',
                                'de': 'Die .eln-Datei enthielt keine gültigen flexiblen Metadaten für dieses Objekt.'
                            }
                        }
                        parsed_data.import_notes[object_node["@id"]].append(gettext('The .eln file did not contain any valid flexible metadata for this object.'))
                        fallback_schema_property_order.append('import_note')
                        fallback_schema_properties['import_note'] = {
                            'type': 'text',
                            'languages': ['en', 'de'],
                            'title': {
                                'en': 'Import Note',
                                'de': 'Import-Hinweis'
                            }
                        }
                    versions.append(ParsedELNVersion(
                        version_id=0,
                        data=fallback_data,
                        schema=fallback_schema,
                        user_id=creator_id,
                        date_created=date_created
                    ))
                parsed_data.objects.append(ParsedELNObject(
                    id=object_node_ref['@id'],
                    name=name,
                    url=url,
                    files=files,
                    versions=versions,
                    comments=comments,
                    type=object_type,
                    type_id=object_type_id,
                ))
            for graph_node in graph_nodes_by_id.values():
                if graph_node['@type'] == 'Person':
                    if 'name' in graph_node and graph_node['name'] is None:
                        name = None
                    else:
                        if 'name' in graph_node:
                            _eln_assert(isinstance(graph_node['name'], str), "Invalid name for Person")
                            name = graph_node['name'].strip()
                        elif 'familyName' in graph_node and 'givenName' in graph_node:
                            _eln_assert(isinstance(graph_node['familyName'], str), "Invalid family name for Person")
                            _eln_assert(isinstance(graph_node['givenName'], str), "Invalid given name for Person")
                            name = graph_node['givenName'] + ' ' + graph_node['familyName']
                            name = name.strip()
                        else:
                            name = None
                        _eln_assert(name, "Invalid name for Person")
                    url = None
                    if 'url' in graph_node:
                        _eln_assert(isinstance(graph_node['url'], str), "Invalid url for Person")
                        url = graph_node['url']
                    elif 'identifier' in graph_node:
                        _eln_assert(isinstance(graph_node['identifier'], str), "Invalid identifier for Person")
                        if graph_node['identifier'].startswith('https://orcid.org/'):
                            url = graph_node['identifier']
                    parsed_data.users.append(ParsedELNUser(
                        id=graph_node['@id'],
                        name=name,
                        url=url,
                    ))
    except errors.InvalidELNFileError:
        raise
    except zipfile.BadZipfile:
        raise errors.InvalidELNFileError(".eln file must be valid .zip file")
    except Exception as e:
        raise errors.InvalidELNFileError("Unknown error") from e

    if not parsed_data.objects:
        raise errors.InvalidELNFileError(".eln file must contain at least one object")
    return parsed_data


def remove_expired_eln_imports() -> None:
    expired_eln_imports = eln_imports.ELNImport.query.filter(db.and_(
        eln_imports.ELNImport.import_utc_datetime.is_(None),
        eln_imports.ELNImport.upload_utc_datetime < datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    )).all()
    if expired_eln_imports:
        for eln_import in expired_eln_imports:
            db.session.delete(eln_import)
        db.session.commit()


def get_pending_eln_imports(user_id: int) -> typing.List[ELNImport]:
    pending_eln_imports = eln_imports.ELNImport.query.filter_by(
        import_utc_datetime=None,
        user_id=user_id
    ).order_by(eln_imports.ELNImport.upload_utc_datetime).all()
    return [
        ELNImport.from_database(eln_import)
        for eln_import in pending_eln_imports
    ]


def get_eln_import_object_url(
        object_id: int
) -> typing.Optional[str]:
    eln_import_object = eln_imports.ELNImportObject.query.filter_by(object_id=object_id).first()
    if eln_import_object is None:
        return None
    return eln_import_object.url


def get_eln_import_for_object(
        object_id: int
) -> typing.Optional[typing.Tuple[ELNImport, typing.Optional[str]]]:
    eln_import_object = eln_imports.ELNImportObject.query.filter_by(object_id=object_id).first()
    if eln_import_object is None:
        return None
    return ELNImport.from_database(eln_import_object.eln_import), eln_import_object.url


def get_eln_import_objects(
        eln_import_id: int
) -> typing.Sequence[Object]:
    eln_import_objects = eln_imports.ELNImportObject.query.filter_by(eln_import_id=eln_import_id).all()
    return [
        get_object(eln_import_object.object_id)
        for eln_import_object in eln_import_objects
    ]


def get_eln_import_users(
        eln_import_id: int
) -> typing.Sequence[User]:
    eln_import_users = users.User.query.filter_by(type=UserType.ELN_IMPORT_USER, eln_import_id=eln_import_id).all()
    return [
        User.from_database(eln_import_user)
        for eln_import_user in eln_import_users
    ]


def get_import_signed_by(
        eln_import_id: int
) -> typing.Optional[str]:
    eln_import = eln_imports.ELNImport.query.filter_by(id=eln_import_id).first()
    if eln_import is None:
        return None
    return eln_import.signed_by


def _replace_references(
        data: typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]],
        eln_source_url: str,
        generate_sampledb_object_url: bool = True
) -> None:
    """
    Replace references to users and objects.

    :param data: the data to replace references in
    :param eln_source_url: the URL of the ELN the data is from
    :param generate_sampledb_object_url: whether object URLs should be generated in the SampleDB pattern
    """
    if isinstance(data, list):
        for item in data:
            _replace_references(item, eln_source_url)
    elif isinstance(data, dict):
        if '_type' in data:
            if data['_type'] in ['user', 'sample', 'measurement', 'object_reference']:
                if 'eln_source_url' in data:
                    del data['eln_source_url']
                if 'eln_object_url' in data:
                    del data['eln_object_url']
                if 'eln_user_url' in data:
                    del data['eln_user_url']
                if 'component_uuid' not in data:
                    data['eln_source_url'] = eln_source_url
                    if data['_type'] == 'user':
                        if generate_sampledb_object_url and 'user_id' in data and isinstance(data['user_id'], int):
                            data['eln_user_url'] = eln_source_url + ('' if eln_source_url.endswith('/') else '/') + relative_url_for('frontend.user_profile', user_id=data['user_id'])
                        else:
                            data['eln_user_url'] = None
                    else:
                        if generate_sampledb_object_url and 'object_id' in data and isinstance(data['object_id'], int):
                            data['eln_object_url'] = eln_source_url + ('' if eln_source_url.endswith('/') else '/') + relative_url_for('frontend.object', object_id=data['object_id'])
                        else:
                            data['eln_object_url'] = None
        else:
            for value in data.values():
                _replace_references(value, eln_source_url)


def _remove_template_ids(
        schema: typing.Dict[str, typing.Any]
) -> None:
    """
    Remove references to template actions from a schema.

    :param schema: the schema to remove template action references from
    """
    if schema['type'] == 'array':
        _remove_template_ids(schema['items'])
    elif schema['type'] == 'object':
        if 'template' in schema:
            del schema['template']
        for property_schema in schema['properties'].values():
            _remove_template_ids(property_schema)


def _convert_property_value_to_id_schema_and_data(
        property_value: typing.Dict[str, typing.Any]
) -> typing.Tuple[str, typing.Dict[str, typing.Any], typing.Dict[str, typing.Any], str]:
    property_id = property_value['propertyID']
    # bool
    if isinstance(property_value['value'], bool):
        property_schema = {
            "type": "bool",
            "title": {
                "en": property_value.get('name', property_value['propertyID'])
            }
        }
        property_data = {
            "_type": "bool",
            "value": property_value['value']
        }
        text_representation = json.dumps(property_value['value'])
        return property_id, property_schema, property_data, text_representation
    # datetime
    if isinstance(property_value['value'], str):
        try:
            parsed_datetime = datetime.datetime.fromisoformat(property_value['value'])
        except ValueError:
            pass
        else:
            if parsed_datetime.tzinfo is not None:
                parsed_datetime = parsed_datetime.astimezone(datetime.timezone.utc)
            utc_datetime = parsed_datetime.replace(tzinfo=None)
            property_schema = {
                "type": "datetime",
                "title": {
                    "en": property_value.get('name', property_value['propertyID'])
                }
            }
            property_data = {
                "_type": "datetime",
                "utc_datetime": utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
            }
            text_representation = property_value['value']
            return property_id, property_schema, property_data, text_representation
    # quantity
    if isinstance(property_value['value'], (int, float)):
        units = None
        if 'unitCode' in property_value:
            units = get_unit_for_un_cefact_code(property_value['unitCode'])
        if units is None and 'unitText' in property_value:
            try:
                pint_units = ureg.parse_units(property_value['unitText'])
            except Exception:
                pass
            else:
                units = str(pint_units)
        if units is None:
            units = "1"
        property_schema = {
            "type": "quantity",
            "title": {
                "en": property_value.get('name', property_value['propertyID'])
            },
            "units": units
        }
        property_data = {
            "_type": "quantity",
            "magnitude": property_value['value'],
            "units": units
        }
        if 'unitText' in property_value:
            text_representation = f"{property_value['value']} {property_value['unitText']}"
        else:
            text_representation = f"{property_value['value']}"
        return property_id, property_schema, property_data, text_representation
    # text as fallback
    text_representation = str(property_value['value'])
    property_schema = {
        "type": "text",
        "title": {
            "en": property_value.get('name', property_value['propertyID'])
        }
    }
    property_data = {
        "_type": "text",
        "text": {
            'en': text_representation
        }
    }
    if '\n' in text_representation:
        property_schema['multiline'] = True  # type: ignore
    return property_id, property_schema, property_data, text_representation


def _sanitize_keys(
        keys: typing.Sequence[str],
) -> typing.Union[typing.Dict[int, int], typing.Dict[int, str]]:
    keys_with_original_indices = sorted(zip(keys, range(len(keys))))
    used_indices: typing.List[typing.Tuple[int, int]] = []
    for key, original_index in keys_with_original_indices:
        try:
            index = int(key)
        except ValueError:
            break
        if index in dict(used_indices):
            break
        used_indices.append((index, original_index))
    else:
        used_indices.sort()
        offset = 0
        if used_indices[0][0] == 1:
            offset = 1
        if (used_indices[0][0] == offset) and (used_indices[-1][0] - offset == len(used_indices) - 1):
            return {
                original_index: int(key) - offset
                for key, original_index in keys_with_original_indices
            }
    sanitized_keys: typing.Dict[int, str] = {}
    for key, original_index in keys_with_original_indices:
        sanitized_key = ''.join(
            c
            for c in key.lower()
            if c in string.ascii_letters + string.digits + '_'
        )
        sanitized_key = sanitized_key.strip('_')
        while '__' in sanitized_key:
            sanitized_key = sanitized_key.replace('__', '_')
        if sanitized_key and sanitized_key[0] in string.ascii_letters and sanitized_key not in sanitized_keys.values():
            sanitized_keys[original_index] = sanitized_key
        else:
            if sanitized_key:
                sanitized_key = '_' + sanitized_key
            if 'property' + sanitized_key not in sanitized_keys.values():
                sanitized_keys[original_index] = 'property' + sanitized_key
            else:
                for i in itertools.count(2):
                    if f'property{i}' + sanitized_key not in sanitized_keys.values():
                        sanitized_keys[original_index] = f'property{i}' + sanitized_key
                        break
    return sanitized_keys


PropertyValue = typing.Dict[str, typing.Any]  # TODO: TypedDict?
PropertyPath = typing.Tuple[typing.Union[int, str], ...]
FlattenedPropertyValueTree = typing.Dict[typing.Sequence[typing.Union[int, str]], PropertyValue]


def _map_property_values_to_paths(property_values: typing.Sequence[PropertyValue]) -> FlattenedPropertyValueTree:
    if not property_values:
        return {}
    property_paths_and_values = []
    for property_value in property_values:
        property_id = property_value['propertyID']
        property_path: PropertyPath = tuple(property_id.split('.'))
        property_paths_and_values.append((property_path, property_value))
    max_depth = max(
        len(property_path)
        for property_path, _ in property_paths_and_values
    )
    for depth in range(max_depth):
        property_paths_and_values_by_prefix: typing.Dict[PropertyPath, typing.List[typing.Tuple[PropertyPath, PropertyValue]]] = {}
        sanitized_property_paths_and_values = []
        for property_path, property_value in property_paths_and_values:
            if len(property_path) <= depth:
                sanitized_property_paths_and_values.append((property_path, property_value))
                continue
            property_path_prefix = property_path[:depth]
            if property_path_prefix not in property_paths_and_values_by_prefix:
                property_paths_and_values_by_prefix[property_path_prefix] = []
            property_paths_and_values_by_prefix[property_path_prefix].append((property_path, property_value))
        for property_path_prefix, property_paths_and_values_for_prefix in property_paths_and_values_by_prefix.items():
            property_paths_and_values_by_path_element: typing.Dict[str, typing.Tuple[typing.List[typing.Tuple[PropertyPath, PropertyValue]], typing.List[typing.Tuple[PropertyPath, PropertyValue]]]] = {}
            for property_path, property_value in property_paths_and_values_for_prefix:
                path_element = typing.cast(str, property_path[depth])
                if path_element not in property_paths_and_values_by_path_element:
                    property_paths_and_values_by_path_element[path_element] = ([], [])
                if len(property_path) == depth + 1:
                    property_paths_and_values_by_path_element[path_element][0].append((property_path, property_value))
                else:
                    property_paths_and_values_by_path_element[path_element][1].append((property_path, property_value))
            unsanitized_path_elements = []
            property_paths_and_values_by_path_element_index: typing.List[typing.List[typing.Tuple[PropertyPath, PropertyValue]]] = []
            for path_element, property_path_and_values_for_path_element in property_paths_and_values_by_path_element.items():
                unsanitized_path_elements += [path_element] * len(property_path_and_values_for_path_element[0])
                property_paths_and_values_by_path_element_index.extend(
                    [(property_path, property_value)]
                    for property_path, property_value in property_path_and_values_for_path_element[0]
                )
                if property_path_and_values_for_path_element[1]:
                    unsanitized_path_elements.append(path_element)
                    property_paths_and_values_by_path_element_index.append(property_path_and_values_for_path_element[1])
            sanitized_path_elements_by_index = _sanitize_keys(unsanitized_path_elements)
            for path_element_index, sanitized_path_element in sanitized_path_elements_by_index.items():
                for property_path, property_value in property_paths_and_values_by_path_element_index[path_element_index]:
                    sanitized_property_paths_and_values.append((
                        property_path_prefix + (sanitized_path_element,) + property_path[depth + 1:],
                        property_value
                    ))
        property_paths_and_values = sanitized_property_paths_and_values
    return {
        property_path: property_value
        for property_path, property_value in property_paths_and_values
    }


def _convert_property_value_trees_to_schema_and_data(
        flattened_property_value_tree: FlattenedPropertyValueTree,
        is_root: bool = False
) -> typing.Tuple[typing.Dict[str, typing.Any], typing.Any, str, typing.Sequence[str]]:
    if () in flattened_property_value_tree:
        _, schema, data, text = _convert_property_value_to_id_schema_and_data(flattened_property_value_tree[()])
        property_value = flattened_property_value_tree[()]
        full_title = property_value['propertyID']
        titles = full_title.split('.')
        titles = [
            title.strip() for title in titles
        ]
        if titles:
            schema['title'] = {
                'en': titles[-1] or 'Property'
            }
        return schema, data, text, titles
    first_path_elements = [
        property_path[0]
        for property_path in flattened_property_value_tree
    ]
    if first_path_elements and not is_root and all(isinstance(first_path_element, int) for first_path_element in first_path_elements):
        items = [
            _convert_property_value_trees_to_schema_and_data(
                {
                    property_path[1:]: property_value
                    for property_path, property_value in flattened_property_value_tree.items()
                    if property_path[0] == index
                }
            )
            for index in sorted(first_path_elements)
        ]
        if not items:
            return {
                'title': {
                    'en': 'Array'
                },
                'type': 'array',
                'items': {
                    'title': 'Item',
                    'type': 'text'
                }
            }, [], '', ['']
        # check all schemas are the same / compatible (for quantities) and otherwise fall back to use text
        first_item_schema = copy.deepcopy(items[0][0])
        if all(item[0] == first_item_schema for item in items):
            compatible_item_schema = first_item_schema
        else:
            item_schema_types = {item[0].get('type') for item in items}
            if item_schema_types == {'quantity'}:
                used_units = {
                    item[0]['units'] for item in items
                }
                if len(used_units) == 1:
                    compatible_item_schema = first_item_schema
                else:
                    compatible_item_schema = None
            elif item_schema_types == {'object'}:
                compatible_item_schema = None  # TODO: implement this
            elif item_schema_types == {'array'}:
                compatible_item_schema = None  # TODO: implement this
            elif len(item_schema_types) == 1:
                # while other schema types generally support incompatible restrictions, e.g. limiting object_references to specific action types, these features are not used here
                compatible_item_schema = first_item_schema
            else:
                compatible_item_schema = None
        if compatible_item_schema is not None:
            item_schema = compatible_item_schema
        else:
            item_schema = {
                'type': 'text',
                'multiline': any('\n' in text for _, data, text, _ in items)
            }
        item_schema['title'] = {
            'en': 'Item'
        }
        titles = items[0][3][:-1]
        if not titles:
            titles = ['Array']
        return {
            'title': {
                'en': titles[-1]
            },
            'type': 'array',
            'items': item_schema
        }, [
            data if compatible_item_schema is not None else {
                '_type': 'text',
                'text': {
                    'en': text
                }
            }
            for _, data, text, _ in items
        ], '\n'.join(text for _, _, text, _ in items), titles
    else:
        properties = {
            property_name: _convert_property_value_trees_to_schema_and_data(
                {
                    property_path[1:]: property_value
                    for property_path, property_value in flattened_property_value_tree.items()
                    if property_path[:1] == (property_name,)
                }
            )
            for property_name in first_path_elements
        }
        if properties:
            titles = next(iter(properties.values()))[3][:-1]
        else:
            titles = []
        if not titles:
            titles = ['Object']
        return {
            'title': {
                'en': titles[-1]
            },
            'type': 'object',
            'properties': {
                path_element: schema_data_titles[0]
                for path_element, schema_data_titles in properties.items()
            },
            'propertyOrder': [],
            'required': []
        }, {
            path_element: schema_data_titles[1]
            for path_element, schema_data_titles in properties.items()
        }, '', titles  # TODO: implement text


def _insert_property_into_schema_and_data(
        schema: typing.Dict[str, typing.Any],
        data: typing.Dict[str, typing.Any],
        property_name: str,
        property_title: str,
        property_value: typing.Dict[str, typing.Any],
        property_required: bool,
        property_order_position: int
) -> None:
    if property_required:
        if property_name not in schema['required']:
            schema['required'].append(property_name)
    if property_name in schema['propertyOrder']:
        schema['propertyOrder'].remove(property_name)
    schema['propertyOrder'].insert(property_order_position, property_name)
    # if property is already in data with the correct text and schema, there is no need to duplicate it
    if property_name in data and data[property_name] == property_value and property_name in schema['properties'] and schema['properties'][property_name].get('type') == property_value.get('_type') and not schema['properties'][property_name].get('multiline') and not schema['properties']['name'].get('markdown'):
        return
    if property_name in schema['properties']:
        for i in itertools.count(1):
            alternative_property_name = f'property{i if i > 1 else ""}_{property_name}'
            if alternative_property_name not in schema['properties']:
                schema['properties'][alternative_property_name] = schema['properties'][property_name]
                data[alternative_property_name] = data[property_name]
                break
    schema['properties'][property_name] = {
        'type': property_value.get('_type'),
        'title': {
            'en': property_title
        }
    }
    data[property_name] = property_value


def _convert_property_values_to_data_and_schema(
        property_values: typing.Sequence[PropertyValue],
        name: str,
        description: str,
        description_is_markdown: bool,
        tags: typing.Sequence[str]
) -> typing.Tuple[typing.Dict[str, typing.Any], typing.Dict[str, typing.Any]]:
    flattened_property_value_tree = _map_property_values_to_paths(property_values=property_values)
    schema, data, _, _ = _convert_property_value_trees_to_schema_and_data(
        flattened_property_value_tree=flattened_property_value_tree,
        is_root=True
    )
    _insert_property_into_schema_and_data(
        schema=schema,
        data=data,
        property_name='name',
        property_title='Name',
        property_value={'_type': 'text', 'text': {'en': name}},
        property_required=True,
        property_order_position=0
    )
    if description:
        _insert_property_into_schema_and_data(
            schema=schema,
            data=data,
            property_name='description',
            property_title='Description',
            property_value={'_type': 'text', 'text': {'en': description}},
            property_required=False,
            property_order_position=1
        )
        if description_is_markdown:
            data['description']['is_markdown'] = True
            schema['properties']['description']['markdown'] = True
    if tags:
        _insert_property_into_schema_and_data(
            schema=schema,
            data=data,
            property_name='tags',
            property_title='Tags',
            property_value={'_type': 'tags', 'tags': tags},
            property_required=False,
            property_order_position=len(schema['propertyOrder'])
        )
    return data, schema
