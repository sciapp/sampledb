# coding: utf-8
"""
RESTful API for SampleDB
"""

import collections
import base64
import flask

from flask_restful import Resource
import wtforms.validators

from .authentication import object_permissions_required, Permissions
from ...logic.actions import get_action
from ...logic.objects import get_object
from ...logic.files import File, get_file_for_object, get_files_for_object, create_local_file, create_url_file, create_database_file
from ...logic import errors

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def file_info_to_json(file_info: File, include_content: bool = True):
    file_json = {
        'object_id': file_info.object_id,
        'file_id': file_info.id,
        'storage': file_info.storage
    }
    if file_info.storage in {'local', 'database'}:
        file_json.update({
            'original_file_name': file_info.original_file_name
        })
        if include_content:
            with file_info.open() as f:
                base64_content = base64.b64encode(f.read())
            file_json.update({
                'base64_content': base64_content.decode('utf-8')
            })
    if file_info.storage == 'url':
        file_json.update({
            'url': file_info.data['url']
        })
    return file_json


class ObjectFile(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, file_id: int):
        try:
            file_info = get_file_for_object(object_id=object_id, file_id=file_id)
            if file_info is None:
                raise errors.FileDoesNotExistError()
        except errors.FileDoesNotExistError:
            return {
                "message": "file {} of object {} does not exist".format(file_id, object_id)
            }, 404
        if file_info.is_hidden:
            return {
                "message": "file {} of object {} has been hidden".format(file_id, object_id)
            }, 403
        return file_info_to_json(file_info)


class ObjectFiles(Resource):
    @object_permissions_required(Permissions.WRITE)
    def post(self, object_id: int):
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, dict):
            return {
                "message": "JSON object body required"
            }, 400
        object = get_object(object_id=object_id)
        action = get_action(action_id=object.action_id)
        if not action.type.enable_files:
            return {
                "message": "Adding files is not enabled for objects of this type"
            }, 403
        if 'object_id' in request_json:
            if request_json['object_id'] != object.object_id:
                return {
                    "message": "object_id must be {}".format(object.object_id)
                }, 400
        if 'storage' not in request_json:
            return {
                "message": "storage must be set"
            }, 400
        storage = request_json['storage']
        if storage not in ('local', 'url', 'database'):
            return {
                "message": "storage must be 'local', 'database' or 'url'"
            }, 400
        if storage in {'local', 'database'}:
            for key in request_json:
                if key not in {'object_id', 'storage', 'original_file_name', 'base64_content'}:
                    return {
                        "message": "invalid key '{}'".format(key)
                    }, 400
            if 'original_file_name' not in request_json or not request_json['original_file_name']:
                return {
                    "message": "original_file_name must be set for files with local or database storage"
                }, 400
            original_file_name = request_json['original_file_name']
            if 'base64_content' not in request_json:
                return {
                    "message": "base64_content must be set for files with local or database storage"
                }, 400
            base64_content = request_json['base64_content']
            try:
                content = base64.b64decode(base64_content.encode('utf-8'), validate=True)
            except Exception:
                return {
                    "message": "base64_content must be base64 encoded"
                }, 400
            if storage == 'local':
                file = create_local_file(
                    object_id=object_id,
                    user_id=flask.g.user.id,
                    file_name=original_file_name,
                    save_content=lambda stream: stream.write(content)
                )
            else:
                file = create_database_file(
                    object_id=object_id,
                    user_id=flask.g.user.id,
                    file_name=original_file_name,
                    save_content=lambda stream: stream.write(content)
                )
        if storage == 'url':
            for key in request_json:
                if key not in {'object_id', 'storage', 'url'}:
                    return {
                        "message": "invalid key '{}'".format(key)
                    }, 400
            if 'url' not in request_json:
                return {
                    "message": "url must be set for files with url storage"
                }, 400
            url = request_json['url']
            if not _validate_url(url):
                return {
                    "message": "url must be a valid url"
                }, 400
            file = create_url_file(
                object_id=object_id,
                user_id=flask.g.user.id,
                url=url
            )
        file_url = flask.url_for(
            'api.object_file',
            object_id=file.object_id,
            file_id=file.id
        )
        return flask.redirect(file_url, code=201)

    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int):
        return [
            file_info_to_json(file_info, include_content=False)
            for file_info in get_files_for_object(object_id)
            if not file_info.is_hidden
        ]


def _validate_url(url: str) -> bool:
    """
    Validate a URL using the wtforms.validators.url validator.

    :param url: the URL to validate
    :return: whether or not the URL is valid
    """
    PseudoField = collections.namedtuple('PseudoField', ['data'])
    field = PseudoField(data=url)
    try:
        wtforms.validators.url(message="")(None, field)
    except wtforms.validators.ValidationError:
        return False
    return True
