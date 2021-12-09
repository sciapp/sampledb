# coding: utf-8
"""
Export all SampleDB information readable by the user to an archive.
"""

import datetime
import io
import json
import os
import tarfile
import time
import typing
import zipfile

import flask

from .. import logic


def get_archive_files(user_id: int, object_ids: typing.Optional[typing.List[int]] = None) -> typing.Dict[str, bytes]:
    archive_files = {}
    if object_ids is None:
        relevant_instrument_ids = {
            instrument.id
            for instrument in logic.instruments.get_instruments()
        }
    else:
        relevant_instrument_ids = set()
    relevant_action_ids = set()
    relevant_user_ids = set()
    relevant_location_ids = set()
    relevant_markdown_images = set()
    objects = logic.object_permissions.get_objects_with_permissions(
        user_id,
        logic.object_permissions.Permissions.READ
    )
    infos = {}
    object_infos = []
    for object in objects:
        if object_ids is not None and object.id not in object_ids:
            continue

        archive_files[f"sampledb_export/{object.id}.rdf"] = logic.rdf.generate_rdf(user_id, object.id)

        object_infos.append({
            'id': object.id,
            'action_id': object.action_id,
            'versions': [],
            'comments': [],
            'location_assignments': [],
            'publications': [],
            'files': []
        })
        relevant_action_ids.add(object.action_id)

        for object_version in logic.objects.get_object_versions(object.id):
            relevant_user_ids.add(object_version.user_id)
            object_infos[-1]['versions'].append(
                {
                    'id': object_version.version_id,
                    'user_id': object_version.user_id,
                    'utc_datetime': object_version.utc_datetime.isoformat(),
                    'schema': object_version.schema,
                    'data': object_version.data
                }
            )

            for referenced_user_id, _ in logic.objects.find_user_references(object_version, False):
                relevant_user_ids.add(referenced_user_id)

            for markdown in logic.markdown_to_html.get_markdown_from_object_data(object_version.data):
                relevant_markdown_images.update(logic.markdown_images.find_referenced_markdown_images(logic.markdown_to_html.markdown_to_safe_html(markdown)))

        for comment in logic.comments.get_comments_for_object(object.id):
            relevant_user_ids.add(comment.user_id)
            object_infos[-1]['comments'].append({
                'id': comment.id,
                'author_id': comment.user_id,
                'content': comment.content,
                'utc_datetime': comment.utc_datetime.isoformat()
            })

        for location_assignment in logic.locations.get_object_location_assignments(object.id):
            relevant_user_ids.add(location_assignment.user_id)
            relevant_user_ids.add(location_assignment.responsible_user_id)
            relevant_location_ids.add(location_assignment.location_id)
            object_infos[-1]['location_assignments'].append({
                'id': location_assignment.id,
                'assigning_user_id': location_assignment.user_id,
                'responsible_user_id': location_assignment.responsible_user_id,
                'location_id': location_assignment.location_id,
                'utc_datetime': location_assignment.utc_datetime.isoformat(),
            })

        log_entries = logic.object_log.get_object_log_entries(object.id, user_id)
        publication_log_entries = {
            (log_entry.data['doi'], log_entry.data['title']): log_entry
            for log_entry in log_entries
            if log_entry.type == logic.object_log.ObjectLogEntryType.LINK_PUBLICATION
        }
        for publication_info in logic.publications.get_publications_for_object(object.id):
            object_infos[-1]['publications'].append({
                'doi': publication_info.doi,
                'title': publication_info.title,
                'object_name': publication_info.object_name
            })
            if (publication_info.doi, publication_info.title) in publication_log_entries:
                publication_log_entry = publication_log_entries[(publication_info.doi, publication_info.title)]
                object_infos[-1]['publications'][-1]['user_id'] = publication_log_entry.user_id
                object_infos[-1]['publications'][-1]['utc_datetime'] = publication_log_entry.utc_datetime.isoformat()

        for file_info in logic.files.get_files_for_object(object.id):
            if not file_info.is_hidden:
                relevant_user_ids.add(file_info.user_id)
                object_infos[-1]['files'].append({
                    'id': file_info.id,
                    'hidden': False,
                    'title': file_info.title,
                    'description': file_info.description,
                    'uploader_id': file_info.user_id,
                    'utc_datetime': file_info.utc_datetime.isoformat()
                })
                if file_info.storage in {'local', 'database'}:
                    object_infos[-1]['files'][-1]['original_file_name'] = file_info.original_file_name
                    try:
                        file_bytes = file_info.open(read_only=True).read()
                    except Exception:
                        pass
                    else:
                        file_name = os.path.basename(file_info.original_file_name)
                        object_infos[-1]['files'][-1]['path'] = f'objects/{object.id}/files/{file_info.id}/{file_name}'
                        archive_files[f"sampledb_export/objects/{object.id}/files/{file_info.id}/{file_name}"] = file_bytes
                elif file_info.storage == 'url':
                    object_infos[-1]['files'][-1]['url'] = file_info.url
            else:
                object_infos[-1]['files'].append({
                    'id': file_info.id,
                    'hidden': True,
                    'hide_reason': file_info.hide_reason
                })
    infos['objects'] = object_infos

    action_infos = []
    for action_info in logic.actions.get_actions():
        if action_info.id in relevant_action_ids:
            relevant_user_ids.add(action_info.user_id)
            relevant_instrument_ids.add(action_info.instrument_id)
            action_permissions = logic.action_permissions.get_user_action_permissions(action_info.id, user_id)
            if logic.action_permissions.Permissions.READ in action_permissions:
                action_translation = logic.action_translations.get_action_translation_for_action_in_language(
                    action_id=action_info.id,
                    language_id=logic.languages.Language.ENGLISH
                )
                action_type_translation = logic.action_type_translations.get_action_type_translation_for_action_type_in_language(
                    action_type_id=action_info.type_id,
                    language_id=logic.languages.Language.ENGLISH
                )
                action_infos.append({
                    'id': action_info.id,
                    'type': action_type_translation.object_name.lower(),
                    'name': action_translation.name,
                    'user_id': action_info.user_id,
                    'instrument_id': action_info.instrument_id,
                    'description': action_translation.description,
                    'description_is_markdown': action_info.description_is_markdown,
                    'short_description': action_translation.short_description,
                    'short_description_is_markdown': action_info.short_description_is_markdown
                })
                if action_info.description_is_markdown:
                    relevant_markdown_images.update(logic.markdown_images.find_referenced_markdown_images(logic.markdown_to_html.markdown_to_safe_html(action_translation.description)))
                if action_info.short_description_is_markdown:
                    relevant_markdown_images.update(logic.markdown_images.find_referenced_markdown_images(logic.markdown_to_html.markdown_to_safe_html(action_translation.short_description)))
    infos['actions'] = action_infos

    instrument_infos = []
    for instrument_info in logic.instruments.get_instruments():
        if instrument_info.id in relevant_instrument_ids:
            relevant_user_ids.update({user.id for user in instrument_info.responsible_users})
            instrument_translation = logic.instrument_translations.get_instrument_translation_for_instrument_in_language(
                instrument_id=instrument_info.id,
                language_id=logic.languages.Language.ENGLISH
            )
            instrument_infos.append({
                'id': instrument_info.id,
                'name': instrument_translation.name,
                'description': instrument_translation.description,
                'description_is_markdown': instrument_info.description_is_markdown,
                'short_description': instrument_translation.short_description,
                'short_description_is_markdown': instrument_info.short_description_is_markdown,
                'instrument_scientist_ids': [user.id for user in instrument_info.responsible_users],
                'instrument_log_entries': []
            })
            user_is_instrument_responsible = user_id in [user.id for user in instrument_info.responsible_users]
            if user_is_instrument_responsible:
                instrument_infos[-1]['notes'] = instrument_translation.notes
                instrument_infos[-1]['notes_is_markdown'] = instrument_info.notes_is_markdown
            if instrument_info.users_can_view_log_entries or user_is_instrument_responsible:
                for log_entry in logic.instrument_log_entries.get_instrument_log_entries(instrument_info.id):
                    relevant_user_ids.add(log_entry.user_id)
                    instrument_infos[-1]['instrument_log_entries'].append({
                        'id': log_entry.id,
                        'author_id': log_entry.user_id,
                        'file_attachments': [],
                        'object_attachments': [],
                        'versions': []
                    })
                    for version in log_entry.versions:
                        instrument_infos[-1]['instrument_log_entries'][-1]['versions'].append({
                            'log_entry_id': log_entry.id,
                            'version_id': version.version_id,
                            'content': version.content,
                            'utc_datetime': version.utc_datetime.isoformat(),
                            'categories': []
                        })
                        for category in version.categories:
                            instrument_infos[-1]['instrument_log_entries'][-1]['versions'][-1]['categories'].append({
                                'id': category.id,
                                'title': category.title
                            })
                    file_attachments = logic.instrument_log_entries.get_instrument_log_file_attachments(log_entry.id)
                    for file_attachment in file_attachments:
                        file_name = os.path.basename(file_attachment.file_name)
                        file_path = f'instruments/{instrument_info.id}/log_entries/{log_entry.id}/files/{file_attachment.id}/{file_name}'
                        instrument_infos[-1]['instrument_log_entries'][-1]['file_attachments'].append({
                            'file_name': file_attachment.file_name,
                            'path': file_path
                        })
                        archive_files["sampledb_export/" + file_path] = file_attachment.content

                    object_attachments = logic.instrument_log_entries.get_instrument_log_object_attachments(log_entry.id)
                    for object_attachment in object_attachments:
                        instrument_infos[-1]['instrument_log_entries'][-1]['object_attachments'].append({
                            'object_id': object_attachment.object_id
                        })
            if instrument_info.description_is_markdown:
                relevant_markdown_images.update(logic.markdown_images.find_referenced_markdown_images(logic.markdown_to_html.markdown_to_safe_html(instrument_translation.description)))
            if instrument_info.short_description_is_markdown:
                relevant_markdown_images.update(logic.markdown_images.find_referenced_markdown_images(logic.markdown_to_html.markdown_to_safe_html(instrument_translation.short_description)))
            if user_is_instrument_responsible and instrument_info.notes_is_markdown:
                relevant_markdown_images.update(logic.markdown_images.find_referenced_markdown_images(logic.markdown_to_html.markdown_to_safe_html(instrument_translation.notes)))
    infos['instruments'] = instrument_infos

    user_infos = []
    for user_info in logic.users.get_users(exclude_hidden=False):
        if user_info.id in relevant_user_ids:
            user_infos.append({
                'id': user_info.id,
                'name': user_info.name,
                'orcid_id': f'https://orcid.org/{user_info.orcid}' if user_info.orcid else None,
                'affiliation': user_info.affiliation if user_info.affiliation else None,
                'role': user_info.role if user_info.role else None
            })
    infos['users'] = user_infos

    locations = logic.locations.get_locations()
    all_relevant_location_ids = set()
    while relevant_location_ids:
        new_relevant_location_ids = set()
        for location_info in locations:
            if location_info.id in relevant_location_ids:
                new_relevant_location_ids.add(location_info.parent_location_id)
        all_relevant_location_ids.update(relevant_location_ids)
        relevant_location_ids = new_relevant_location_ids - all_relevant_location_ids

    location_infos = []
    for location_info in locations:
        if location_info.id in all_relevant_location_ids:
            location_infos.append({
                'id': location_info.id,
                'parent_id': location_info.parent_location_id,
                'name': location_info.name,
                'description': location_info.description
            })
    infos['locations'] = location_infos

    for file_name in relevant_markdown_images:
        content = logic.markdown_images.get_markdown_image(file_name, user_id)
        if content is not None:
            archive_files[f'sampledb_export/markdown_files/{file_name}'] = content

    archive_files['sampledb_export/data.json'] = json.dumps(infos, indent=2)

    readme_text = f"""SampleDB Export
===============

The file data.json contains information on objects from the SampleDB instance at {flask.url_for('frontend.index', _external=True)} in JSON format. Aside from information on the objects themselves, it also contains information on relevant actions, instruments, users and locations.
"""
    if len(archive_files) > 1:
        readme_text += """
The objects directory contains files uploaded for the objects in data.json.
"""
    readme_text += f"""
This archive was created for user #{user_id} at {datetime.datetime.now().isoformat()}.
"""

    archive_files["sampledb_export/README.txt"] = readme_text

    for file_name, file_content in archive_files.items():
        if isinstance(file_content, str):
            archive_files[file_name] = file_content.encode('utf-8')

    return archive_files


def get_zip_archive(user_id: int, object_ids: typing.Optional[typing.List[int]] = None) -> bytes:
    archive_files = get_archive_files(user_id, object_ids=object_ids)
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, 'w') as zip_file:
        for file_name, file_content in archive_files.items():
            zip_file.writestr(file_name, file_content)
    return zip_bytes.getvalue()


def get_tar_gz_archive(user_id: int, object_ids: typing.Optional[typing.List[int]] = None) -> bytes:
    archive_files = get_archive_files(user_id, object_ids=object_ids)
    tar_bytes = io.BytesIO()
    with tarfile.open('sampledb_export.tar.gz', 'w:gz', fileobj=tar_bytes) as tar_file:
        for file_name, file_content in archive_files.items():
            tar_info = tarfile.TarInfo(file_name)
            tar_info.size = len(file_content)
            tar_info.mode = 0o444
            tar_info.mtime = time.time()
            tar_file.addfile(tar_info, fileobj=io.BytesIO(file_content))
    return tar_bytes.getvalue()


FILE_FORMATS = {
    '.zip': ('.zip Archive', get_zip_archive, 'application/zip'),
    '.tar.gz': ('.tar.gz Archive', get_tar_gz_archive, 'application/gzip')
}
