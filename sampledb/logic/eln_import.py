import dataclasses
import datetime
import hashlib
import io
import json
import os.path
import typing
import zipfile

from flask_babel import gettext

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
from . import errors
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

    @classmethod
    def from_database(cls, eln_import: eln_imports.ELNImport) -> 'ELNImport':
        return cls(
            id=eln_import.id,
            file_name=eln_import.file_name,
            user_id=eln_import.user_id,
            upload_utc_datetime=eln_import.upload_utc_datetime,
            import_utc_datetime=eln_import.import_utc_datetime,
            invalid_reason=eln_import.invalid_reason,
            user=User.from_database(eln_import.user)
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


@dataclasses.dataclass(frozen=True)
class ParsedELNDatabaseFile:
    name: str
    title: typing.Optional[str]
    description: typing.Optional[str]
    content: bytes
    user_id: typing.Optional[str]


@dataclasses.dataclass(frozen=True)
class ParsedELNURLFile:
    url: str
    title: typing.Optional[str]
    description: typing.Optional[str]
    user_id: str


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
) -> typing.Tuple[typing.List[int], typing.List[str]]:
    errors = []

    eln_import = eln_imports.ELNImport.query.filter_by(id=eln_import_id).first()
    if eln_import is None:
        return [], ['Unknown ELN import']
    if eln_import.import_utc_datetime is not None:
        return [], ['This ELN file has already been imported']
    user_id = eln_import.user_id

    parsed_data = parse_eln_file(eln_import_id=eln_import_id)
    if action_type_ids is None:
        action_type_ids = []
        for object_info in parsed_data.objects:
            action_type_ids.append(object_info.type_id)
    elif len(action_type_ids) != len(parsed_data.objects):
        return [], ['Invalid Action Type ID information for this ELN file']

    eln_import.import_utc_datetime = datetime.datetime.now(datetime.timezone.utc)
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
        users_by_id[None] = user

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
                user_id=user_id,
                action_id=action_ids_by_action_type_id[action_type_id],
                data=initial_version_info.data,
                schema=initial_version_info.schema,
                eln_import_id=eln_import_id,
                eln_object_id=object_info.id,
                utc_datetime=None,
                data_validator_arguments={'file_names_by_id': None, 'strict': False, 'allow_disabled_languages': True}
            )
        except Exception:
            errors.append(f'Failed to import object #{object_index}')
            continue
        db.session.add(eln_imports.ELNImportObject(
            object_id=imported_object.id,
            eln_import_id=eln_import_id,
            url=object_info.url
        ))
        db.session.commit()
        for version_index, version_id in enumerate(version_ids[1:]):
            version_info = versions_by_id[version_id]
            try:
                update_object(
                    object_id=imported_object.id,
                    data=version_info.data,
                    schema=version_info.schema,
                    user_id=user_id,
                    data_validator_arguments={'file_names_by_id': None, 'strict': False, 'allow_disabled_languages': True}
                )
            except Exception:
                errors.append(f'Failed to import object #{object_index} version #{version_index}')
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
                    create_log_entry=False
                ).id
            elif isinstance(file_info, ParsedELNURLFile):
                if file_info.user_id:
                    file_user_id = users_by_id[file_info.user_id].id

                file_id = create_url_file(
                    object_id=imported_object.id,
                    user_id=file_user_id,
                    url=file_info.url,
                    create_log_entry=False
                ).id
            else:
                errors.append(f'Failed to import file #{file_index} for object #{object_index}')
                continue
            update_file_information(
                object_id=imported_object.id,
                file_id=file_id,
                user_id=file_user_id,
                title=file_info.title or '',
                description=file_info.description or ''
            )
        for comment_info in object_info.comments:
            create_comment(
                object_id=imported_object.id,
                user_id=users_by_id[comment_info.author_id].id,
                content=comment_info.text,
                utc_datetime=comment_info.date_created,
                create_log_entry=False
            )
    return imported_object_ids, errors


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
        import_notes={}
    )

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
            _eln_assert(zip_file.testzip() is None, ".eln file must be valid .zip file")

            member_names = zip_file.namelist()
            root_path_names = set()
            for member_name in member_names:
                path_name, file_name = os.path.split(member_name)
                root_path_names.add(path_name.split('/')[0])
            _eln_assert(len(root_path_names) == 1, ".eln file must contain a single root directory")
            root_path_name = list(root_path_names)[0]

            ro_crate_metadata_file_name = root_path_name + '/ro-crate-metadata.json'
            _eln_assert(ro_crate_metadata_file_name in member_names, ".eln file must contain ro-crate-metadata.json in its root directory")
            try:
                with zip_file.open(root_path_name + '/ro-crate-metadata.json') as ro_crate_metadata_file:
                    ro_crate_metadata = json.load(ro_crate_metadata_file)
            except Exception:
                raise errors.InvalidELNFileError("ro-crate-metadata.json must contain a JSON-encoded object")
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
            _eln_assert(root_node.get('version') == '1.0' or metadata_node.get('version') == '1.0', "ro-crate-metadata.json @graph root node or ro-crate-metadata.json node must have version 1.0")
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
                _eln_assert(all(isinstance(key, str) for key in sdpublisher), "ro-crate-metadata.json @graph sdPublisher is invalid")
            _eln_assert(sdpublisher.get('@type') == 'Organization', "ro-crate-metadata.json @graph sdPublisher is invalid")
            if sdpublisher.get('name') == 'SampleDB':
                eln_dialect = 'SampleDB'
            else:
                eln_dialect = None
            _eln_assert(isinstance(root_node.get('hasPart'), list), "ro-crate-metadata.json @graph root node must have parts")

            for object_node_ref in root_node['hasPart']:
                _eln_assert(isinstance(object_node_ref, dict), "Invalid reference")
                _eln_assert(list(object_node_ref.keys()) == ['@id'], "Invalid reference")
                _eln_assert(object_node_ref['@id'] in graph_nodes_by_id, "Reference to unknown ID")

                object_node = graph_nodes_by_id[object_node_ref['@id']]
                _eln_assert(isinstance(object_node.get('name'), str), "Missing name for Dataset")
                name = object_node['name']

                parsed_data.import_notes[object_node["@id"]] = []

                _eln_assert(isinstance(object_node.get('description', ''), str), "Invalid description for Dataset")
                description = object_node.get('description', '')

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
                        original_object_id_str = object_node_ref['@id'][len('./objects/'):]
                        original_object_id = int(original_object_id_str)
                        _eln_assert(str(original_object_id) == original_object_id_str and original_object_id > 0, "Invalid @id for Dataset for SampleDB .eln file")
                    except ValueError:
                        _eln_assert(False, "Invalid @id for Dataset for SampleDB .eln file")
                    _eln_assert(isinstance(url, str), "Invalid url for Dataset for SampleDB .eln file")
                    _eln_assert(url.endswith(object_node_ref['@id'][1:]), "Invalid url for Dataset for SampleDB .eln file")
                    eln_source_url = url[:-len(object_node_ref['@id'][2:])]
                else:
                    eln_source_url = None

                if eln_dialect == 'SampleDB' and 'genre' in object_node:
                    genre = object_node.get('genre')
                    _eln_assert(isinstance(genre, str), "Invalid genre for Dataset for SampleDB .eln file")
                    _eln_assert(genre in {'sample', 'measurement', 'simulation', 'other'}, "Invalid genre for Dataset for SampleDB .eln file")
                    if genre == 'other':
                        object_type = None
                    else:
                        object_type = typing.cast(str, genre)
                    object_type_id = {
                        None: None,
                        'sample': ActionType.SAMPLE_CREATION,
                        'measurement': ActionType.MEASUREMENT,
                        'simulation': ActionType.SIMULATION
                    }.get(object_type)
                else:
                    object_type = None
                    object_type_id = None

                _eln_assert(isinstance(object_node.get('comment', []), list), "Invalid comment list for Dataset")
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
                    },
                    'description': {
                        '_type': 'text',
                        'text': {'en': description},
                    },
                    'import_note': {
                        '_type': 'text',
                        'text': {
                            'en': 'The metadata for this object could not be imported.',
                            'de': 'Die Metadaten für dieses Objekt konnten nicht importiert werden.'
                        }
                    }
                }
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
                        },
                        'description': {
                            'type': 'text',
                            'title': {
                                'en': 'Description',
                                'de': 'Beschreibung'
                            },
                            'multiline': True
                        },
                        'import_note': {
                            'type': 'text',
                            'languages': ['en', 'de'],
                            'title': {
                                'en': 'Import Note',
                                'de': 'Import-Hinweis'
                            }
                        }
                    },
                    'required': ['name'],
                    'propertyOrder': ['name', 'description', 'import_note']
                }

                _eln_assert(isinstance(object_node.get('hasPart', []), list), "Invalid parts list for Dataset")
                for object_part_ref in object_node.get('hasPart', []):
                    _eln_assert(isinstance(object_part_ref, dict), "Invalid reference")
                    _eln_assert(list(object_part_ref.keys()) == ['@id'], "Invalid reference")
                    _eln_assert(object_part_ref['@id'] in graph_nodes_by_id, "Reference to unknown ID")
                    object_part = graph_nodes_by_id[object_part_ref['@id']]
                    if object_part['@type'] == 'File':
                        _eln_assert(isinstance(object_part.get('name'), str), "Invalid name for File")
                        if 'description' in object_part:
                            _eln_assert(isinstance(object_part.get('description'), str), "Invalid description for File")
                        file_path = object_part['@id']
                        if file_path.startswith('./'):
                            file_path = file_path[1:]
                        elif not file_path.startswith('/'):
                            file_path = '/' + file_path
                        file_path = root_path_name + file_path
                        _eln_assert(file_path in member_names, "File not found in .eln file (1)")
                        file_name = os.path.split(file_path)[1]
                        with zip_file.open(file_path) as file:
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
                        if eln_dialect == 'SampleDB' and object_part['@id'] == object_node_ref['@id'] + '/files.json':
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
                                files.append(ParsedELNURLFile(
                                    url=file_url,
                                    title=file_info.get('title'),
                                    description=file_info.get('description'),
                                    user_id=f'./users/{author_sampledb_id}',
                                ))
                        else:
                            author_ref = object_part.get('author')
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
                            files.append(ParsedELNDatabaseFile(
                                name=file_name,
                                title=object_part['name'],
                                description=object_part.get('description'),
                                content=file_data,
                                user_id=author_id,
                            ))
                    if eln_dialect == 'SampleDB' and object_part['@type'] == 'Dataset':
                        _eln_assert(object_part['@id'].startswith(object_node['@id'] + '/version/'), "SampleDB .eln file must only contain versions as Dataset parts of objects")
                        try:
                            version_id = int(object_part['@id'].rsplit('/', maxsplit=1)[1])
                        except ValueError:
                            raise errors.InvalidELNFileError("SampleDB .eln file must only contain versions as Dataset parts of objects")
                        _eln_assert(isinstance(object_part.get('hasPart'), list), "SampleDB .eln file must contain data and schema for each version")
                        _eln_assert(len(object_part['hasPart']) == 2, "SampleDB .eln file must contain data and schema for each version")
                        _eln_assert({'@id': object_part['@id'] + '/data.json'} in object_part['hasPart'], "SampleDB .eln file must contain data and schema for each version")
                        _eln_assert({'@id': object_part['@id'] + '/schema.json'} in object_part['hasPart'], "SampleDB .eln file must contain data and schema for each version")
                        data_file_name = object_part['@id'] + '/data.json'
                        if data_file_name.startswith('./'):
                            data_file_name = data_file_name[1:]
                        elif not data_file_name.startswith('/'):
                            data_file_name = '/' + data_file_name
                        data_file_name = root_path_name + data_file_name
                        _eln_assert(data_file_name in member_names, "SampleDB .eln file must contain data and schema for each version")
                        schema_file_name = object_part['@id'] + '/schema.json'
                        if schema_file_name.startswith('./'):
                            schema_file_name = schema_file_name[1:]
                        elif not schema_file_name.startswith('/'):
                            schema_file_name = '/' + schema_file_name
                        schema_file_name = root_path_name + schema_file_name
                        _eln_assert(schema_file_name in member_names, "SampleDB .eln file must contain data and schema for each version")
                        try:
                            with zip_file.open(data_file_name) as data_file:
                                version_data = json.load(data_file)
                            with zip_file.open(schema_file_name) as schema_file:
                                version_schema = json.load(schema_file)
                        except Exception:
                            raise errors.InvalidELNFileError("SampleDB .eln file must contain data and schema for each version")
                        if version_schema is None or version_data is None:
                            versions.append(ParsedELNVersion(
                                version_id=version_id,
                                data=None,
                                schema=None
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
                                    schema=version_schema
                                ))
                            except errors.ValidationError as e:
                                versions.append(ParsedELNVersion(
                                    version_id=version_id,
                                    data=fallback_data,
                                    schema=fallback_schema
                                ))
                                parsed_data.import_notes[object_node["@id"]].append(gettext('Invalid data or schema in version %(version_id)s of object %(eln_object_id)s (%(error)s)', version_id=version_id, eln_object_id=object_node['@id'], error=e))
                if not versions:
                    versions.append(ParsedELNVersion(
                        version_id=0,
                        data=fallback_data,
                        schema=fallback_schema
                    ))
                    if eln_dialect:
                        parsed_data.import_notes[object_node["@id"]].append(gettext('Importing metadata for .eln files from %(eln_dialect)s is not yet supported.', eln_dialect=eln_dialect))
                    else:
                        parsed_data.import_notes[object_node["@id"]].append(gettext('Importing metadata for .eln files from this ELN is not yet supported.'))
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
