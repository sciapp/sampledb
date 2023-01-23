import datetime
import hashlib
import json
import mimetypes
import os.path
import typing

import flask

from .utils import get_translated_text


def generate_ro_crate_metadata(
        archive_files: typing.Dict[str, typing.Union[str, bytes]],
        infos: typing.Dict[str, typing.Any]
) -> typing.Dict[str, bytes]:
    result_files: typing.Dict[str, bytes] = {}
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
                "dateCreated": datetime.datetime.now().isoformat()
            },
            {
                "@id": "./",
                "@type": [
                    "Dataset"
                ],
                "sdPublisher": {
                    "@type": "Organization",
                    "name": "SampleDB",
                    "logo": "https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/_static/img/logo.svg",
                    "slogan": "SampleDB is a web-based electronic lab notebook with a focus on sample and measurement metadata.",
                    "url": "https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/"
                },
                "version": "1.0",
                "hasPart": []
            },
        ]
    }
    directory_datasets = {
        "sampledb_export": ro_crate_metadata["@graph"][1]
    }

    for object_info in infos['objects']:
        ro_crate_metadata["@graph"].append({
            "@id": f"./objects/{object_info['id']}",
            "@type": "Dataset",
            "name": f"{get_translated_text(object_info['versions'][-1]['data'].get('name', {}).get('text', {}), 'en')}" if object_info['versions'][-1]['data'] is not None else '',
            "description": f"Object #{object_info['id']}",
            "dateCreated": object_info['versions'][0]['utc_datetime'],
            "dateModified": object_info['versions'][-1]['utc_datetime'],
            "author": {"@id": f"./users/{object_info['versions'][0]['user_id']}"},
            "url": flask.url_for('frontend.object', object_id=object_info['id'], _external=True),
            "comment": [],
            "hasPart": [
                {
                    "@id": f"./objects/{object_info['id']}/version/{version_info['id']}",
                }
                for version_info in object_info['versions']
            ] + [
                {
                    "@id": f"./objects/{object_info['id']}/files.json"
                }
            ]
        })
        directory_datasets[f"sampledb_export/objects/{object_info['id']}/files"] = ro_crate_metadata["@graph"][-1]
        directory_datasets[f"sampledb_export/objects/{object_info['id']}/comments"] = ro_crate_metadata["@graph"][-1]
        directory_datasets["sampledb_export"]["hasPart"].append({
            "@id": f"./objects/{object_info['id']}"
        })
        for version_info in object_info['versions']:
            ro_crate_metadata["@graph"].append({
                "@id": f"./objects/{object_info['id']}/version/{version_info['id']}",
                "@type": "Dataset",
                "name": f"{get_translated_text(version_info['data'].get('name', {}).get('text', {}), 'en')}" if version_info['data'] is not None else '',
                "description": f"Object #{object_info['id']} version #{version_info['id']}",
                "dateCreated": version_info['utc_datetime'],
                "author": {"@id": f"./users/{version_info['user_id']}"},
                "url": flask.url_for('frontend.object_version', object_id=object_info['id'], version_id=version_info['id'], _external=True),
                "hasPart": [
                    {
                        "@id": f"./objects/{object_info['id']}/version/{version_info['id']}/schema.json",
                    },
                    {
                        "@id": f"./objects/{object_info['id']}/version/{version_info['id']}/data.json"
                    }
                ]
            })

            schema_json = json.dumps(version_info['schema'], indent=2).encode('utf-8')
            result_files[f"sampledb_export/objects/{object_info['id']}/version/{version_info['id']}/schema.json"] = schema_json
            ro_crate_metadata["@graph"].append({
                "@id": f"./objects/{object_info['id']}/version/{version_info['id']}/schema.json",
                "@type": "File",
                "description": f"Schema for Object #{object_info['id']} version #{version_info['id']}",
                "name": "schema.json",
                "contentType": "application/json",
                "contentSize": len(schema_json),
                "sha256": hashlib.sha256(schema_json).hexdigest()
            })

            data_json = json.dumps(version_info['data'], indent=2).encode('utf-8')
            result_files[f"sampledb_export/objects/{object_info['id']}/version/{version_info['id']}/data.json"] = data_json
            ro_crate_metadata["@graph"].append({
                "@id": f"./objects/{object_info['id']}/version/{version_info['id']}/data.json",
                "@type": "File",
                "description": f"Data for Object #{object_info['id']} version #{version_info['id']}",
                "name": "data.json",
                "contentType": "application/json",
                "contentSize": len(data_json),
                "sha256": hashlib.sha256(data_json).hexdigest()
            })

        for comment in object_info['comments']:
            ro_crate_metadata["@graph"].append({
                "@id": f"./objects/{object_info['id']}/comments/{comment['id']}",
                "@type": "Comment",
                "parentItem": {
                    "@id": f"./objects/{object_info['id']}"
                },
                "author": {"@id": f"./users/{comment['author_id']}"},
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
            "contentType": "application/json",
            "contentSize": len(files_json),
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
                    },
                    "dateCreated": file_info['utc_datetime'],
                    "contentType": file_type,
                    "contentSize": len(file_content),
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

    result_files['sampledb_export/ro-crate-metadata.json'] = json.dumps(ro_crate_metadata, indent=2).encode('utf-8')
    return result_files
