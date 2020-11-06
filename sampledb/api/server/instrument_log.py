# coding: utf-8
"""
RESTful API for SampleDB
"""

import base64
import json

import flask
from flask_restful import Resource

from .authentication import multi_auth
from ...logic.instruments import get_instrument
from ...logic.instrument_log_entries import get_instrument_log_entries, get_instrument_log_entry, get_instrument_log_file_attachment, get_instrument_log_object_attachment, get_instrument_log_categories, create_instrument_log_entry, create_instrument_log_file_attachment, create_instrument_log_object_attachment, InstrumentLogEntry, InstrumentLogEntryVersion, InstrumentLogFileAttachment, InstrumentLogObjectAttachment, InstrumentLogCategory
from ...logic import errors
from ...logic.object_permissions import get_user_object_permissions, Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

MAX_FILE_NAME_LENGTH = 256


def instrument_log_entry_to_json(log_entry: InstrumentLogEntry):
    return {
        'log_entry_id': log_entry.id,
        'author': log_entry.user_id,
        'versions': [
            instrument_log_entry_version_to_json(version)
            for version in log_entry.versions
        ]
    }


def instrument_log_entry_version_to_json(version: InstrumentLogEntryVersion):
    return {
        'log_entry_id': version.log_entry_id,
        'version_id': version.version_id,
        'utc_datetime': version.utc_datetime.isoformat(),
        'content': version.content,
        'categories': [
            category_to_json(category)
            for category in version.categories
        ],
    }


def file_attachment_to_json(file_attachment: InstrumentLogFileAttachment):
    return {
        'file_attachment_id': file_attachment.id,
        'file_name': file_attachment.file_name if not file_attachment.is_hidden else None,
        'base64_content': base64.b64encode(file_attachment.content).decode('ascii') if not file_attachment.is_hidden else None,
        'is_hidden': file_attachment.is_hidden
    }


def object_attachment_to_json(object_attachment: InstrumentLogObjectAttachment):
    return {
        'object_attachment_id': object_attachment.id,
        'object_id': object_attachment.object_id if not object_attachment.is_hidden else None,
        'is_hidden': object_attachment.is_hidden
    }


def category_to_json(category: InstrumentLogCategory):
    return {
        'category_id': category.id,
        'title': category.title
    }


class InstrumentLogEntries(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int):
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
    def post(self, instrument_id: int):
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
            unexpected_keys = set(data.keys()) - {'content', 'category_ids', 'file_attachments', 'object_attachments'}
            if unexpected_keys:
                raise ValueError()
            content = data['content']
            category_ids = data.get('category_ids', [])
            file_attachments = data.get('file_attachments', [])
            object_attachments = data.get('object_attachments', [])
        except Exception:
            return {
                "message": "expected json object containing content, category_ids, file_attachments and object attachments"
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

        log_entry = create_instrument_log_entry(
            instrument_id=instrument.id,
            user_id=flask.g.user.id,
            content=content,
            category_ids=category_ids
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
    def get(self, instrument_id: int, log_entry_id: int):
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


class InstrumentLogEntryFileAttachments(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int, log_entry_id: int):
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
    def get(self, instrument_id: int, log_entry_id: int, file_attachment_id: int):
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
    def get(self, instrument_id: int, log_entry_id: int):
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
    def get(self, instrument_id: int, log_entry_id: int, object_attachment_id: int):
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
    def get(self, instrument_id: int):
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
    def get(self, instrument_id: int, category_id: int):
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
