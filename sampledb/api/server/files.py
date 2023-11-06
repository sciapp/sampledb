# coding: utf-8
"""
RESTful API for SampleDB
"""

import base64
import typing

import flask

from .authentication import object_permissions_required
from ..utils import Resource, ResponseData
from ...logic import errors
from ...logic.actions import get_action
from ...logic.files import create_database_file, create_local_file_reference, create_url_file, File, get_file_for_object, get_files_for_object, SUPPORTED_HASH_ALGORITHMS, DEFAULT_HASH_ALGORITHM
from ...logic.objects import get_object
from ...logic.utils import parse_url
from ...models import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def file_info_to_json(file_info: File, include_content: bool = True) -> typing.Dict[str, typing.Any]:
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
        if file_info.data:
            file_json['hash'] = file_info.data.get('hash')
    if file_info.storage == 'url' and file_info.url is not None:
        file_json.update({
            'url': file_info.url
        })
    return file_json


class ObjectFile(Resource):
    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int, file_id: int) -> ResponseData:
        try:
            file_info = get_file_for_object(object_id=object_id, file_id=file_id)
            if file_info is None:
                raise errors.FileDoesNotExistError()
        except errors.FileDoesNotExistError:
            return {
                "message": f"file {file_id} of object {object_id} does not exist"
            }, 404
        if file_info.is_hidden:
            return {
                "message": f"file {file_id} of object {object_id} has been hidden"
            }, 403
        return file_info_to_json(file_info)


class ObjectFiles(Resource):
    @object_permissions_required(Permissions.WRITE)
    def post(self, object_id: int) -> ResponseData:
        request_json = flask.request.get_json(force=True)
        if not isinstance(request_json, dict):
            return {
                "message": "JSON object body required"
            }, 400
        object = get_object(object_id=object_id)
        if object.action_id is not None:
            action = get_action(action_id=object.action_id)
            if action.type is None or not action.type.enable_files:
                return {
                    "message": "Adding files is not enabled for objects of this type"
                }, 403
        if 'object_id' in request_json:
            if request_json['object_id'] != object.object_id:
                return {
                    "message": f"object_id must be {object.object_id}"
                }, 400
        if 'storage' not in request_json:
            return {
                "message": "storage must be set"
            }, 400
        storage = request_json['storage']
        if storage not in ('local_reference', 'url', 'database'):
            return {
                "message": "storage must be 'local_reference', 'database' or 'url'"
            }, 400
        if 'hash' in request_json:
            if not isinstance(request_json['hash'], dict):
                return {
                    "message": "hash must be a JSON object"
                }, 400
            if set(request_json['hash'].keys()) != {'hexdigest', 'algorithm'} or not isinstance(request_json['hash']['algorithm'], str) or not isinstance(request_json['hash']['hexdigest'], str):
                return {
                    "message": "hash must contain algorithm and hexdigest as strings"
                }, 400
            hash_algorithm = request_json['hash']['algorithm']
            if hash_algorithm not in SUPPORTED_HASH_ALGORITHMS:
                return {
                    "message": "only the following hash algorithms are supported: " + ", ".join(
                        SUPPORTED_HASH_ALGORITHMS)
                }, 400
            if any(c not in '0123456789abcdef' for c in request_json['hash']['hexdigest']):
                return {
                    "message": "hash hexdigest be a lowercase string of hex characters"
                }, 400
        if storage == 'database':
            for key in request_json:
                if key not in {'object_id', 'storage', 'original_file_name', 'base64_content', 'hash'}:
                    return {
                        "message": f"invalid key '{key}'"
                    }, 400
            if 'original_file_name' not in request_json or not request_json['original_file_name']:
                return {
                    "message": "original_file_name must be set for files with database storage"
                }, 400
            original_file_name = request_json['original_file_name']
            if 'base64_content' not in request_json:
                return {
                    "message": "base64_content must be set for files with database storage"
                }, 400
            base64_content = request_json['base64_content']
            try:
                content = base64.b64decode(base64_content.encode('utf-8'), validate=True)
            except Exception:
                return {
                    "message": "base64_content must be base64 encoded"
                }, 400
            if 'hash' in request_json:
                hash = File.HashInfo.from_binary_data(
                    algorithm=request_json['hash']['algorithm'],
                    binary_data=content
                )
                if hash is None:
                    return {
                        "message": "invalid hash data"
                    }, 400
                if request_json['hash']['hexdigest'] != hash.hexdigest:
                    return {
                        "message": "hash hexdigest mismatch, expected: " + hash.hexdigest
                    }, 400
            else:
                hash = File.HashInfo.from_binary_data(
                    algorithm=DEFAULT_HASH_ALGORITHM,
                    binary_data=content
                )
            file = create_database_file(
                object_id=object_id,
                user_id=flask.g.user.id,
                file_name=original_file_name,
                save_content=lambda stream: typing.cast(None, stream.write(content)),
                hash=hash
            )
        if storage == 'local_reference':
            for key in request_json:
                if key not in {'object_id', 'storage', 'filepath', 'hash'}:
                    return {
                        "message": f"invalid key '{key}'"
                    }, 400
            if 'filepath' not in request_json or not request_json['filepath']:
                return {
                    "message": "filepath must be set for files with local_reference storage"
                }, 400
            try:
                file = create_local_file_reference(
                    object_id=object_id,
                    user_id=flask.g.user.id,
                    filepath=request_json['filepath'],
                    hash=File.HashInfo(
                        algorithm=request_json['hash']['algorithm'],
                        hexdigest=request_json['hash']['hexdigest']
                    ) if 'hash' in request_json else None
                )
            except errors.UnauthorizedRequestError:
                return {
                    "message": "user not authorized to add this path"
                }, 403
        if storage == 'url':
            for key in request_json:
                if key not in {'object_id', 'storage', 'url'}:
                    return {
                        "message": f"invalid key '{key}'"
                    }, 400
            if 'url' not in request_json:
                return {
                    "message": "url must be set for files with url storage"
                }, 400
            url = request_json['url']
            try:
                parse_url(url)
            except errors.InvalidURLError:
                return {
                    "message": "url must be a valid url"
                }, 400
            except errors.URLTooLongError:
                return {
                    "message": "url exceeds length limit"
                }, 400
            except errors.InvalidIPAddressError:
                return {
                    "message": "url contains an invalid IP address"
                }, 400
            except errors.InvalidPortNumberError:
                return {
                    "message": "url contains an invalid port number"
                }, 400
            file = create_url_file(
                object_id=object_id,
                user_id=flask.g.user.id,
                url=url
            )
        file_url = flask.url_for(
            'api.object_file',
            object_id=file.object_id,
            file_id=file.id,
            _external=True
        )
        return flask.redirect(file_url, code=201)

    @object_permissions_required(Permissions.READ)
    def get(self, object_id: int) -> ResponseData:
        return [
            file_info_to_json(file_info, include_content=False)
            for file_info in get_files_for_object(object_id)
            if not file_info.is_hidden
        ]
