import datetime
import hashlib
import json
import mimetypes
import os.path
import typing

import flask
import minisign
from flask import url_for

from . import minisign_keys
from .utils import get_translated_text
from .actions import get_action
from .action_types import ActionType
from .objects import find_object_references
from .dataverse_export import flatten_metadata, get_title_for_property
from .datatypes import Quantity
from .units import get_un_cefact_code_for_unit


def _unpack_single_item_arrays(json_value: typing.Any) -> typing.Any:
    if isinstance(json_value, dict):
        return {
            key: _unpack_single_item_arrays(value)
            for key, value in json_value.items()
        }
    if isinstance(json_value, (list, tuple)):
        if len(json_value) == 1:
            return _unpack_single_item_arrays(json_value[0])
        return [
            _unpack_single_item_arrays(value)
            for value in json_value
        ]
    return json_value


def generate_ro_crate_metadata(
        archive_files: typing.Dict[str, typing.Union[str, bytes]],
        infos: typing.Dict[str, typing.Any],
        user_id: int,
        object_ids: typing.Optional[typing.List[int]]
) -> typing.Dict[str, bytes]:
    result_files: typing.Dict[str, bytes] = {}
    date_created = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec='microseconds')
    description = f"SampleDB .eln export generated for user #{user_id}"
    if object_ids:
        description += " for objects #" + ', #'.join(map(str, sorted(object_ids)))
    ro_crate_metadata: typing.Dict[str, typing.Any] = {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": [
            {
                "@type": "CreativeWork",
                "@id": "ro-crate-metadata.json",
                "description": "RO-Crate Metadata File Descriptor",
                "about": {
                    "@id": "./"
                },
                "conformsTo": {
                    "@id": "https://w3id.org/ro/crate/1.1"
                },
                "sdPublisher": {
                    "@id": "SampleDB"
                },
                "version": "1.1",
                "dateCreated": date_created
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": "SampleDB .eln export",
                "description": description,
                "license": {
                    "@id": "./license"
                },
                "datePublished": date_created,
                "hasPart": []
            },
            {
                "@type": "Organization",
                "@id": "SampleDB",
                "name": "SampleDB",
                "logo": "https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/_static/img/logo.svg",
                "slogan": "SampleDB is a web-based electronic lab notebook with a focus on sample and measurement metadata.",
                "url": "https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/"
            },
            {
                "@id": "./license",
                "@type": "CreativeWork",
                "name": "No License",
                "description": "This .eln file does not include a license."
            }
        ]
    }
    directory_datasets = {
        "sampledb_export": ro_crate_metadata["@graph"][1]
    }
    exported_object_ids = {
        object_info['id']: f"./objects/{object_info['id']}/"
        for object_info in infos['objects']
    }
    exported_user_ids = {
        user_info['id']: f"./users/{user_info['id']}"
        for user_info in infos['users']
    }
    for object_info in infos['objects']:
        if object_info['action_id'] is not None:
            action = get_action(object_info['action_id'])
            if action.type_id is None:
                object_type = None
            else:
                object_type = {
                    ActionType.SAMPLE_CREATION: "sample",
                    ActionType.MEASUREMENT: "measurement",
                    ActionType.SIMULATION: "simulation",
                }.get(action.type_id, None)
        else:
            object_type = 'other'
        exported_file_ids = {
            file_info['id']: './' + file_info['path']
            for file_info in object_info['files']
            if 'path' in file_info
        }
        property_values = _convert_metadata_to_property_values(
            object_id=object_info['id'],
            data=object_info['versions'][0]['data'],
            schema=object_info['versions'][0]['schema'],
            exported_object_ids=exported_object_ids,
            exported_user_ids=exported_user_ids,
            exported_file_ids=exported_file_ids,
            property_id_prefix=f"./objects/{object_info['id']}/properties/"
        ) if object_info['versions'][0]['data'] is not None else []
        ro_crate_metadata["@graph"].extend(property_values)
        property_value_references = [
            {
                '@id': property_value['@id']
            }
            for property_value in property_values
        ]
        ro_crate_metadata["@graph"].append({
            "@id": f"./objects/{object_info['id']}/",
            "@type": "Dataset",
            "identifier": f"{object_info['id']}",
            "name": f"{get_translated_text(object_info['versions'][-1]['data'].get('name', {}).get('text', {}), 'en')}" if object_info['versions'][-1]['data'] is not None else '',
            "description": f"Object #{object_info['id']}",
            "dateCreated": object_info['versions'][0]['utc_datetime'],
            "dateModified": object_info['versions'][-1]['utc_datetime'],
            "author": [
                {"@id": f"./users/{version_user_id}"}
                for version_user_id in sorted({
                    version_info['user_id']
                    for version_info in object_info['versions']
                    if version_info['user_id'] is not None
                })
            ],
            "creator": {"@id": f"./users/{object_info['versions'][0]['user_id']}"} if object_info['versions'][0]['user_id'] is not None else None,
            "url": flask.url_for('frontend.object', object_id=object_info['id'], _external=True),
            "variableMeasured": property_value_references,
            "mentions": [],
            "comment": [],
            "isBasedOn": [
                {
                    "@id": f"./objects/{object_info['id']}/versions/{version_info['id']}/",
                }
                for version_info in object_info['versions']
            ],
            "hasPart": [
                {
                    "@id": f"./objects/{object_info['id']}/versions/{version_info['id']}/",
                }
                for version_info in object_info['versions']
            ] + [
                {
                    "@id": f"./objects/{object_info['id']}/files.json"
                }
            ]
        })
        if object_type:
            ro_crate_metadata["@graph"][-1]["genre"] = object_type
        current_version_info = object_info['versions'][-1]
        if current_version_info.get('data') and isinstance(current_version_info['data'].get('tags'), dict) and current_version_info['data']['tags'].get('_type') == 'tags' and current_version_info['data']['tags'].get('tags'):
            ro_crate_metadata["@graph"][-1]["keywords"] = ', '.join(current_version_info['data']['tags']['tags'])
        if current_version_info.get('data'):
            referenced_object_ids = find_object_references(
                object_id=typing.cast(int, object_info['id']),
                version_id=typing.cast(int, current_version_info['id']),
                object_data=typing.cast(typing.Optional[typing.Dict[str, typing.Any]], current_version_info['data']),
                find_previous_referenced_object_ids=False,
                include_fed_references=False
            )
            for referenced_object_id, _previously_reference_object_id, _object_reference_type in referenced_object_ids:
                if referenced_object_id in exported_object_ids:
                    ro_crate_metadata["@graph"][-1]["mentions"].append({"@id": exported_object_ids[referenced_object_id]})
        if not ro_crate_metadata["@graph"][-1]["mentions"]:
            del ro_crate_metadata["@graph"][-1]["mentions"]
        directory_datasets[f"sampledb_export/objects/{object_info['id']}/files"] = ro_crate_metadata["@graph"][-1]
        directory_datasets[f"sampledb_export/objects/{object_info['id']}/comments"] = ro_crate_metadata["@graph"][-1]
        directory_datasets["sampledb_export"]["hasPart"].append({
            "@id": f"./objects/{object_info['id']}/"
        })
        for version_info in object_info['versions']:
            property_values = _convert_metadata_to_property_values(
                object_id=object_info['id'],
                data=version_info['data'],
                schema=version_info['schema'],
                exported_object_ids=exported_object_ids,
                exported_user_ids=exported_user_ids,
                exported_file_ids=exported_file_ids,
                property_id_prefix=f"./objects/{object_info['id']}/versions/{version_info['id']}/properties/"
            ) if version_info['data'] is not None else []
            ro_crate_metadata["@graph"].extend(property_values)
            property_value_references = [
                {
                    '@id': property_value['@id']
                }
                for property_value in property_values
            ]
            ro_crate_metadata["@graph"].append({
                "@id": f"./objects/{object_info['id']}/versions/{version_info['id']}/",
                "@type": "Dataset",
                "name": f"{get_translated_text(version_info['data'].get('name', {}).get('text', {}), 'en')}" if version_info['data'] is not None else '',
                "description": f"Object #{object_info['id']} version #{version_info['id']}",
                "dateCreated": version_info['utc_datetime'],
                "creator": {"@id": f"./users/{version_info['user_id']}"} if version_info['user_id'] is not None else None,
                "author": [
                    {"@id": f"./users/{other_version_user_id}"}
                    for other_version_user_id in sorted({
                        other_version_info['user_id']
                        for other_version_info in object_info['versions']
                        if other_version_info['user_id'] is not None and other_version_info['id'] <= version_info['id']
                    })
                ],
                "url": flask.url_for('frontend.object_version', object_id=object_info['id'], version_id=version_info['id'], _external=True),
                "variableMeasured": property_value_references,
                "hasPart": [
                    {
                        "@id": f"./objects/{object_info['id']}/versions/{version_info['id']}/schema.json",
                    },
                    {
                        "@id": f"./objects/{object_info['id']}/versions/{version_info['id']}/data.json"
                    }
                ]
            })
            previous_version_refs = []
            for other_version_info in object_info['versions']:
                if other_version_info['id'] < version_info['id']:
                    previous_version_refs.append({
                        "@id": f"./objects/{object_info['id']}/versions/{other_version_info['id']}/"
                    })
            if previous_version_refs:
                ro_crate_metadata["@graph"][-1]['isBasedOn'] = previous_version_refs

            schema_json = json.dumps(version_info['schema'], indent=2).encode('utf-8')
            result_files[f"sampledb_export/objects/{object_info['id']}/versions/{version_info['id']}/schema.json"] = schema_json
            ro_crate_metadata["@graph"].append({
                "@id": f"./objects/{object_info['id']}/versions/{version_info['id']}/schema.json",
                "@type": "File",
                "description": f"Schema for Object #{object_info['id']} version #{version_info['id']}",
                "name": "schema.json",
                "encodingFormat": "application/json",
                "contentSize": str(len(schema_json)),
                "sha256": hashlib.sha256(schema_json).hexdigest()
            })

            data_json = json.dumps(version_info['data'], indent=2).encode('utf-8')
            result_files[f"sampledb_export/objects/{object_info['id']}/versions/{version_info['id']}/data.json"] = data_json
            ro_crate_metadata["@graph"].append({
                "@id": f"./objects/{object_info['id']}/versions/{version_info['id']}/data.json",
                "@type": "File",
                "description": f"Data for Object #{object_info['id']} version #{version_info['id']}",
                "name": "data.json",
                "encodingFormat": "application/json",
                "contentSize": str(len(data_json)),
                "sha256": hashlib.sha256(data_json).hexdigest()
            })

        for comment in object_info['comments']:
            ro_crate_metadata["@graph"].append({
                "@id": f"./objects/{object_info['id']}/comments/{comment['id']}",
                "@type": "Comment",
                "parentItem": {
                    "@id": f"./objects/{object_info['id']}/"
                },
                "author": {"@id": f"./users/{comment['author_id']}"} if comment['author_id'] is not None else None,
                "dateCreated": comment['utc_datetime'],
                "text": comment['content']
            })
            directory_datasets[f"sampledb_export/objects/{object_info['id']}/comments"]['comment'].append({
                "@id": f"./objects/{object_info['id']}/comments/{comment['id']}"
            })

        files_json = json.dumps(object_info['files'], indent=2).encode('utf-8')
        result_files[f"sampledb_export/objects/{object_info['id']}/files.json"] = files_json
        ro_crate_metadata["@graph"].append({
            "@id": f"./objects/{object_info['id']}/files.json",
            "@type": "File",
            "description": f"Data about files for Object #{object_info['id']}",
            "name": "files.json",
            "encodingFormat": "application/json",
            "contentSize": str(len(files_json)),
            "sha256": hashlib.sha256(files_json).hexdigest()
        })

        for file_info in object_info['files']:
            if 'path' in file_info:
                file_name = 'sampledb_export/' + file_info['path']
                file_content = archive_files[file_name]
                relative_file_name = './' + file_info['path']

                charset = None
                if isinstance(file_content, str):
                    file_content = file_content.encode('utf-8')
                    charset = 'UTF-8'

                file_hash = hashlib.sha256(file_content).hexdigest()

                file_extension = os.path.splitext(relative_file_name)[1]
                supported_mime_types = flask.current_app.config['MIME_TYPES']
                if file_extension in flask.current_app.config['MIME_TYPES']:
                    file_type = supported_mime_types[file_extension]
                else:
                    file_type, _ = mimetypes.guess_type(relative_file_name)

                if charset is not None:
                    file_type = f'{file_type}; charset={charset}'

                ro_crate_metadata["@graph"].append({
                    "@id": relative_file_name,
                    "@type": "File",
                    "name": relative_file_name.rsplit('/', 1)[-1],
                    "description": f"File #{file_info['id']} for Object #{object_info['id']}",
                    "author": {
                        "@id": f"./users/{file_info['uploader_id']}"
                    } if file_info['uploader_id'] is not None else None,
                    "dateCreated": file_info['utc_datetime'],
                    "encodingFormat": file_type,
                    "contentSize": str(len(file_content)),
                    "contentUrl": flask.url_for('frontend.object_file', object_id=object_info['id'], file_id=file_info['id'], _external=True),
                    "sha256": file_hash
                })
                result_files[file_name] = file_content

                directory_datasets[f"sampledb_export/objects/{object_info['id']}/files"]["hasPart"].append({
                    "@id": relative_file_name
                })
            else:
                continue

    for user_info in infos['users']:
        ro_crate_metadata["@graph"].append({
            "@id": f"./users/{user_info['id']}",
            "@type": "Person",
            "name": user_info['name'],
            "url": flask.url_for('frontend.user_profile', user_id=user_info['id'], _external=True)
        })
        if user_info.get('orcid_id'):
            ro_crate_metadata["@graph"][-1]['identifier'] = user_info['orcid_id']

    result_files['sampledb_export/ro-crate-metadata.json'] = json.dumps(_unpack_single_item_arrays(ro_crate_metadata), indent=2).encode('utf-8')
    result_files['sampledb_export/ro-crate-metadata.json.minisig'] = _sign_ro_crate_metadata(result_files['sampledb_export/ro-crate-metadata.json'])
    return result_files


def _sign_ro_crate_metadata(
    data: bytes
) -> bytes:
    kp = minisign_keys.get_current_key_pair()
    secret_key = minisign.SecretKey.from_bytes(kp.sk_bytes)
    sig = secret_key.sign(data, trusted_comment=url_for('frontend.key_list_json', _external=True))
    return bytes(sig)


def _convert_metadata_to_property_values(
        object_id: int,
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any],
        exported_object_ids: typing.Dict[int, str],
        exported_user_ids: typing.Dict[int, str],
        exported_file_ids: typing.Dict[int, str],
        property_id_prefix: str
) -> typing.List[typing.Dict[str, typing.Any]]:
    property_values = []
    for property_data, _property_path, full_property_path in flatten_metadata(data):
        property_type = property_data.get('_type')
        if not property_type:
            continue
        property_id = '.'.join(str(path_element) for path_element in full_property_path)
        property_value: typing.Dict[str, typing.Any] = {
            "@type": "PropertyValue",
            "@id": property_id_prefix + property_id,
            "propertyID": property_id,
            "name": get_title_for_property(full_property_path, schema)
        }
        if property_type == 'text':
            property_values.append({
                "value": get_translated_text(property_data['text'], 'en'),
                **property_value
            })
        elif property_type == 'bool':
            property_values.append({
                "value": property_data['value'],
                **property_value
            })
        elif property_type == 'datetime':
            property_values.append({
                "value": datetime.datetime.strptime(property_data['utc_datetime'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=None).isoformat(timespec='microseconds'),
                **property_value
            })
        elif property_type == 'quantity':
            quantity = Quantity.from_json(property_data)
            un_cefact_code = get_un_cefact_code_for_unit(quantity.units)
            if un_cefact_code is not None:
                property_value["unitCode"] = un_cefact_code
            property_values.append({
                "value": quantity.magnitude,
                "unitText": quantity.units,
                **property_value
            })
        elif property_type in ('sample', 'measurement', 'object_reference'):
            property_values.append({
                "value": exported_object_ids.get(property_data['object_id'], flask.url_for('frontend.object', object_id=property_data['object_id'], _external=True)),
                **property_value
            })
        elif property_type == 'user':
            property_values.append({
                "value": exported_user_ids.get(property_data['user_id'], flask.url_for('frontend.user_profile', user_id=property_data['user_id'], _external=True)),
                **property_value
            })
        elif property_type == 'file':
            property_values.append({
                "value": exported_file_ids.get(property_data['file_id'], flask.url_for('frontend.object_file', object_id=object_id, file_id=property_data['file_id'], _external=True)),
                **property_value
            })
        elif property_type == 'hazards':
            hazard_texts = {1: 'Explosive', 2: 'Flammable', 3: 'Oxidizing', 4: 'Compressed Gas', 5: 'Corrosive', 6: 'Toxic', 7: 'Harmful', 8: 'Health Hazard', 9: 'Environmental Hazard'}
            property_values.append({
                "value": ", ".join(f"{hazard_texts[hazard]}" for hazard in sorted(property_data['hazards'])),
                **property_value
            })
    return property_values
