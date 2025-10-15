# coding: utf-8
"""
RESTful API for SampleDB
"""

import base64
import datetime
import json
import typing

import flask

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic.instruments import get_instrument
from ...logic.instrument_log_entries import get_instrument_log_entries, get_instrument_log_entry, get_instrument_log_file_attachment, get_instrument_log_object_attachment, get_instrument_log_categories, create_instrument_log_entry, create_instrument_log_file_attachment, create_instrument_log_object_attachment, update_instrument_log_entry, hide_instrument_log_object_attachment, hide_instrument_log_file_attachment
from ...logic import errors, instrument_log_entries
from ...logic.object_permissions import get_user_object_permissions
from ...models import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

MAX_FILE_NAME_LENGTH = 256


def instrument_log_entry_to_json(log_entry: instrument_log_entries.InstrumentLogEntry) -> typing.Dict[str, typing.Any]:
    return {
        'log_entry_id': log_entry.id,
        'author': log_entry.user_id,
        'versions': [
            instrument_log_entry_version_to_json(version)
            for version in log_entry.versions
        ]
    }


def instrument_log_entry_version_to_json(version: instrument_log_entries.InstrumentLogEntryVersion) -> typing.Dict[str, typing.Any]:
    return {
        'log_entry_id': version.log_entry_id,
        'version_id': version.version_id,
        'utc_datetime': version.utc_datetime.replace(tzinfo=None).isoformat(timespec='microseconds'),
        'content': version.content,
        'categories': [
            category_to_json(category)
            for category in version.categories
        ],
        'event_utc_datetime': version.event_utc_datetime.replace(tzinfo=None).isoformat(timespec='microseconds') if version.event_utc_datetime is not None else None,
        'content_is_markdown': version.content_is_markdown,
    }


def file_attachment_to_json(file_attachment: instrument_log_entries.InstrumentLogFileAttachment) -> typing.Dict[str, typing.Any]:
    return {
        'file_attachment_id': file_attachment.id,
        'file_name': file_attachment.file_name if not file_attachment.is_hidden else None,
        'base64_content': base64.b64encode(file_attachment.content).decode('ascii') if not file_attachment.is_hidden else None,
        'is_hidden': file_attachment.is_hidden
    }


def object_attachment_to_json(object_attachment: instrument_log_entries.InstrumentLogObjectAttachment) -> typing.Dict[str, typing.Any]:
    return {
        'object_attachment_id': object_attachment.id,
        'object_id': object_attachment.object_id if not object_attachment.is_hidden else None,
        'is_hidden': object_attachment.is_hidden
    }


def category_to_json(category: instrument_log_entries.InstrumentLogCategory) -> typing.Dict[str, typing.Any]:
    return {
        'category_id': category.id,
        'title': category.title
    }


class InstrumentLogEntries(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        log_entries = get_instrument_log_entries(instrument_id)
        return [instrument_log_entry_to_json(log_entry) for log_entry in log_entries]

    @multi_auth.login_required
    def post(self, instrument_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_create_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be created by instrument scientists"
            }, 403
        try:
            data = json.loads(flask.request.data)
            unexpected_keys = set(data.keys()) - {'content', 'content_is_markdown', 'category_ids', 'file_attachments', 'object_attachments', 'event_utc_datetime'}
            if unexpected_keys:
                raise ValueError()
            content_is_markdown = data.get('content_is_markdown', False)
            content = data['content']
            category_ids = data.get('category_ids', [])
            file_attachments = data.get('file_attachments', [])
            object_attachments = data.get('object_attachments', [])
            event_utc_datetime_str = data.get('event_utc_datetime', None)
        except Exception:
            return {
                "message": "expected json object containing content, content_is_markdown, category_ids, file_attachments, object attachments and event_utc_datetime"
            }, 400
        if content is None:
            content = ''
        if not isinstance(content, str):
            return {
                "message": "expected string or null for content"
            }, 400
        try:
            if not isinstance(category_ids, list):
                raise TypeError()
            for category_id in category_ids:
                if not isinstance(category_id, int):
                    raise TypeError()
        except TypeError:
            return {
                "message": "expected list containing integer numbers for category_ids"
            }, 400

        existing_category_ids = {
            category.id
            for category in get_instrument_log_categories(instrument_id)
        }
        unknown_category_ids = set(category_ids) - existing_category_ids
        if unknown_category_ids:
            return {
                "message": f"unknown category_ids: {', '.join(map(str, unknown_category_ids))}"
            }, 400

        if not isinstance(content_is_markdown, bool):
            return {
                "message": "expected true or false for content_is_markdown"
            }, 400

        try:
            if not isinstance(file_attachments, list):
                raise TypeError()
            for file_attachment in file_attachments:
                if not isinstance(file_attachment, dict):
                    raise TypeError()
                if set(file_attachment.keys()) - {'file_name', 'base64_content'}:
                    raise ValueError()
                if not isinstance(file_attachment['file_name'], str):
                    raise TypeError()
                file_attachment['file_name'] = file_attachment['file_name'].strip()
                if not isinstance(file_attachment['base64_content'], str):
                    raise TypeError()
                file_attachment['content'] = base64.b64decode(file_attachment['base64_content'].encode('ascii'))
        except Exception:
            return {
                "message": "expected list containing dicts containing file_name and base64_content for file_attachments"
            }, 400

        for file_attachment in file_attachments:
            if not file_attachment['file_name'] or len(file_attachment['file_name']) > MAX_FILE_NAME_LENGTH:
                return {
                    "message": f"file attachment names must not be empty and must contain at most {MAX_FILE_NAME_LENGTH} characters"
                }, 400

        try:
            if not isinstance(object_attachments, list):
                raise TypeError()
            for object_attachment in object_attachments:
                if not isinstance(object_attachment, dict):
                    raise TypeError()
                if set(object_attachment.keys()) - {'object_id'}:
                    raise ValueError()
                if not isinstance(object_attachment['object_id'], int):
                    raise TypeError()
                if object_attachment['object_id'] < 0:
                    raise ValueError()
        except Exception:
            return {
                "message": "expected list containing dicts containing object_id for object_attachments"
            }, 400

        unknown_object_ids = set()
        attached_object_ids = []
        for object_attachment in object_attachments:
            object_id = object_attachment['object_id']
            try:
                permissions = get_user_object_permissions(object_id, flask.g.user.id)
                if Permissions.READ not in permissions:
                    raise errors.ObjectDoesNotExistError()
            except errors.ObjectDoesNotExistError:
                unknown_object_ids.add(object_id)
            else:
                if object_id in attached_object_ids:
                    return {
                        "message": f"duplicate object id in object_attachments: {object_id}"
                    }, 400
                attached_object_ids.append(object_id)
        if unknown_object_ids:
            return {
                "message": f"unknown object ids in object_attachments: {', '.join(map(str, unknown_object_ids))}"
            }, 400

        if not (content or file_attachments or object_attachments):
            return {
                "message": "log entry must contain content or an attachment"
            }, 400

        if event_utc_datetime_str is None:
            event_utc_datetime = None
        else:
            try:
                event_utc_datetime = datetime.datetime.strptime(event_utc_datetime_str, '%Y-%m-%dT%H:%M:%S.%f')
            except Exception:
                return {
                    "message": "event_utc_datetime must be in ISO format including microseconds, e.g. 2024-01-02T03:04:05.678910"
                }, 400
            if abs(event_utc_datetime.year - datetime.date.today().year) > 1000:
                return {
                    "message": "event_utc_datetime must be not be more than 1000 years before or after the current date"
                }, 400

        log_entry = create_instrument_log_entry(
            instrument_id=instrument.id,
            user_id=flask.g.user.id,
            content=content,
            content_is_markdown=content_is_markdown,
            category_ids=category_ids,
            event_utc_datetime=event_utc_datetime
        )

        for file_attachment in file_attachments:
            create_instrument_log_file_attachment(
                instrument_log_entry_id=log_entry.id,
                file_name=file_attachment['file_name'],
                content=file_attachment['content']
            )

        for object_id in attached_object_ids:
            create_instrument_log_object_attachment(
                instrument_log_entry_id=log_entry.id,
                object_id=object_id
            )

        return None, 201, {
            'Location': flask.url_for(
                'api.instrument_log_entry',
                instrument_id=instrument_id,
                log_entry_id=log_entry.id,
                _external=True
            )
        }


class InstrumentLogEntry(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return instrument_log_entry_to_json(log_entry)


class InstrumentLogEntryVersions(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return [
            instrument_log_entry_version_to_json(version)
            for version in log_entry.versions
        ]

    @multi_auth.login_required
    def post(self, instrument_id: int, log_entry_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        expected_version_id = len(log_entry.versions) + 1
        try:
            data = json.loads(flask.request.data)
            unexpected_keys = set(data.keys()) - {'version_id', 'log_entry_id', 'content', 'category_ids', 'content_is_markdown', 'file_attachments', 'object_attachments', 'event_utc_datetime'}
            if unexpected_keys:
                raise ValueError()
            version_id = data.get('version_id', expected_version_id)
            if data.get('log_entry_id', log_entry_id) != log_entry_id:
                return {
                    "message": f"log_entry_id must be {log_entry_id}"
                }, 400
            content_is_markdown = data.get('content_is_markdown', False)
            content = data['content']
            category_ids = data.get('category_ids', [])
            file_attachments = data.get('file_attachments', None)
            object_attachments = data.get('object_attachments', None)
            event_utc_datetime_str = data.get('event_utc_datetime', None)
        except Exception:
            return {
                "message": "expected json object containing version_id, log_entry_id, content, content_is_markdown, category_ids, file_attachments, object attachments and event_utc_datetime"
            }, 400
        if version_id != expected_version_id:
            return {
                "message": f"version_id must be {expected_version_id}"
            }, 400
        if content is None:
            content = ''
        if not isinstance(content, str):
            return {
                "message": "expected string or null for content"
            }, 400
        try:
            if not isinstance(category_ids, list):
                raise TypeError()
            for category_id in category_ids:
                if not isinstance(category_id, int):
                    raise TypeError()
        except TypeError:
            return {
                "message": "expected list containing integer numbers for category_ids"
            }, 400

        if not isinstance(content_is_markdown, bool):
            return {
                "message": "expected true or false for content_is_markdown"
            }, 400

        existing_category_ids = {
            category.id
            for category in get_instrument_log_categories(instrument_id)
        }
        unknown_category_ids = set(category_ids) - existing_category_ids
        if unknown_category_ids:
            return {
                "message": f"unknown category_ids: {', '.join(map(str, unknown_category_ids))}"
            }, 400

        if file_attachments is not None:
            try:
                if not isinstance(file_attachments, list):
                    raise TypeError()
                for file_attachment in file_attachments:
                    if not isinstance(file_attachment, dict):
                        raise TypeError()
                    if set(file_attachment.keys()) - {'file_name', 'base64_content'}:
                        raise ValueError()
                    if not isinstance(file_attachment['file_name'], str):
                        raise TypeError()
                    file_attachment['file_name'] = file_attachment['file_name'].strip()
                    if not isinstance(file_attachment['base64_content'], str):
                        raise TypeError()
                    file_attachment['content'] = base64.b64decode(file_attachment['base64_content'].encode('ascii'))
            except Exception:
                return {
                    "message": "expected list containing dicts containing file_name and base64_content for file_attachments"
                }, 400

            for file_attachment in file_attachments:
                if not file_attachment['file_name'] or len(file_attachment['file_name']) > MAX_FILE_NAME_LENGTH:
                    return {
                        "message": f"file attachment names must not be empty and must contain at most {MAX_FILE_NAME_LENGTH} characters"
                    }, 400

        if object_attachments is not None:
            try:
                if not isinstance(object_attachments, list):
                    raise TypeError()
                for object_attachment in object_attachments:
                    if not isinstance(object_attachment, dict):
                        raise TypeError()
                    if set(object_attachment.keys()) - {'object_id'}:
                        raise ValueError()
                    if not isinstance(object_attachment['object_id'], int):
                        raise TypeError()
                    if object_attachment['object_id'] < 0:
                        raise ValueError()
            except Exception:
                return {
                    "message": "expected list containing dicts containing object_id for object_attachments"
                }, 400

            unknown_object_ids = set()
            attached_object_ids = []
            for object_attachment in object_attachments:
                object_id = object_attachment['object_id']
                try:
                    permissions = get_user_object_permissions(object_id, flask.g.user.id)
                    if Permissions.READ not in permissions:
                        raise errors.ObjectDoesNotExistError()
                except errors.ObjectDoesNotExistError:
                    unknown_object_ids.add(object_id)
                else:
                    if object_id in attached_object_ids:
                        return {
                            "message": f"duplicate object id in object_attachments: {object_id}"
                        }, 400
                    attached_object_ids.append(object_id)
            if unknown_object_ids:
                return {
                    "message": f"unknown object ids in object_attachments: {', '.join(map(str, unknown_object_ids))}"
                }, 400

        if not (content or file_attachments or (file_attachments is None and [file_attachment for file_attachment in log_entry.file_attachments if not file_attachment.is_hidden]) or object_attachments or (object_attachments is None and [object_attachment for object_attachment in log_entry.object_attachments if not object_attachment.is_hidden])):
            return {
                "message": "log entry must contain content or an attachment"
            }, 400

        if event_utc_datetime_str is None:
            event_utc_datetime = None
        else:
            try:
                event_utc_datetime = datetime.datetime.strptime(event_utc_datetime_str, '%Y-%m-%dT%H:%M:%S.%f')
            except Exception:
                return {
                    "message": "event_utc_datetime must be in ISO format including microseconds, e.g. 2024-01-02T03:04:05.678910"
                }, 400
            if abs(event_utc_datetime.year - datetime.date.today().year) > 1000:
                return {
                    "message": "event_utc_datetime must be not be more than 1000 years before or after the current date"
                }, 400
        log_entry = update_instrument_log_entry(
            log_entry_id=log_entry.id,
            content=content,
            category_ids=category_ids,
            content_is_markdown=content_is_markdown,
            event_utc_datetime=event_utc_datetime,
        )

        if file_attachments is not None:
            existing_file_attachments = {
                (file_attachment.file_name, file_attachment.content): file_attachment
                for file_attachment in log_entry.file_attachments
                if not file_attachment.is_hidden
            }
            for file_attachment in file_attachments:
                if (file_attachment['file_name'], file_attachment['content']) in existing_file_attachments:
                    continue
                create_instrument_log_file_attachment(
                    instrument_log_entry_id=log_entry.id,
                    file_name=file_attachment['file_name'],
                    content=file_attachment['content']
                )
            for file_attachment in log_entry.file_attachments:
                if not file_attachment.is_hidden and (file_attachment.file_name, file_attachment.content) not in {(file_attachment['file_name'], file_attachment['content']) for file_attachment in file_attachments}:
                    hide_instrument_log_file_attachment(file_attachment.id)

        if object_attachments is not None:
            previously_attached_object_ids = {
                object_attachment.object_id: object_attachment
                for object_attachment in log_entry.object_attachments
            }
            for object_id in attached_object_ids:
                if object_id in previously_attached_object_ids:
                    object_attachment = previously_attached_object_ids[object_id]
                    if object_attachment.is_hidden:
                        hide_instrument_log_object_attachment(object_attachment.id, set_hidden=False)
                    continue
                try:
                    create_instrument_log_object_attachment(log_entry.id, object_id)
                except errors.ObjectDoesNotExistError:
                    continue
            for object_id in set(previously_attached_object_ids) - set(attached_object_ids):
                object_attachment = previously_attached_object_ids[object_id]
                if not object_attachment.is_hidden:
                    hide_instrument_log_object_attachment(object_attachment.id, set_hidden=True)

        return None, 201, {
            'Location': flask.url_for(
                'api.instrument_log_entry_version',
                instrument_id=instrument_id,
                log_entry_id=log_entry.id,
                log_entry_version_id=log_entry.versions[-1].version_id,
                _external=True
            )
        }


class InstrumentLogEntryVersion(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int, log_entry_version_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        versions_by_id = {
            version.version_id: version
            for version in log_entry.versions
        }
        if log_entry_version_id not in versions_by_id:
            return {
                "message": f"version {log_entry_version_id} for log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return instrument_log_entry_version_to_json(versions_by_id[log_entry_version_id])


class InstrumentLogEntryFileAttachments(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return [
            file_attachment_to_json(file_attachment)
            for file_attachment in log_entry.file_attachments
        ]


class InstrumentLogEntryFileAttachment(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int, file_attachment_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        try:
            file_attachment = get_instrument_log_file_attachment(file_attachment_id)
            if file_attachment.log_entry_id != log_entry_id:
                raise errors.InstrumentLogFileAttachmentDoesNotExistError()
        except errors.InstrumentLogFileAttachmentDoesNotExistError:
            return {
                "message": f"file attachment {file_attachment_id} for log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return file_attachment_to_json(file_attachment)


class InstrumentLogEntryObjectAttachments(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return [
            object_attachment_to_json(object_attachment)
            for object_attachment in log_entry.object_attachments
        ]


class InstrumentLogEntryObjectAttachment(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int, object_attachment_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log entries for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        try:
            log_entry = get_instrument_log_entry(log_entry_id)
            if log_entry.instrument_id != instrument_id:
                raise errors.InstrumentLogEntryDoesNotExistError()
        except errors.InstrumentLogEntryDoesNotExistError:
            return {
                "message": f"log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        try:
            object_attachment = get_instrument_log_object_attachment(object_attachment_id)
            if object_attachment.log_entry_id != log_entry_id:
                raise errors.InstrumentLogObjectAttachmentDoesNotExistError()
        except errors.InstrumentLogObjectAttachmentDoesNotExistError:
            return {
                "message": f"object attachment {object_attachment_id} for log entry {log_entry_id} for instrument {instrument_id} does not exist"
            }, 404
        return object_attachment_to_json(object_attachment)


class InstrumentLogCategories(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log categories for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        categories = get_instrument_log_categories(instrument_id)
        return [
            category_to_json(category)
            for category in categories
        ]


class InstrumentLogCategory(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, category_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        if not instrument.users_can_view_log_entries and flask.g.user not in instrument.responsible_users:
            return {
                "message": f"log categories for instrument {instrument_id} can only be accessed by instrument scientists"
            }, 403
        categories = get_instrument_log_categories(instrument_id)
        for category in categories:
            if category.id == category_id:
                return category_to_json(category)
        return {
            "message": f"log category {category_id} for instrument {instrument_id} does not exist"
        }, 404
