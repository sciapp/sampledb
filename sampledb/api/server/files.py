import base64
import typing
from dataclasses import dataclass
from functools import cached_property

import flask
from pydantic import AfterValidator, BaseModel, Field, Strict, Tag, model_validator
from pydantic_core import PydanticCustomError

from ...logic import errors
from ...logic.actions import get_action
from ...logic.files import (DEFAULT_HASH_ALGORITHM, SUPPORTED_HASH_ALGORITHMS,
                            File, create_database_file,
                            create_local_file_reference, create_url_file,
                            get_file_for_object, get_files_for_object)
from ...logic.objects import get_object
from ...models import Object, Permissions
from ..utils import Resource, ResponseData
from .authentication import object_permissions_required
from .validation_utils import (Base64Encoded, HexString, NonEmptyString,
                               OptionalNotNone, Url, ValidatingError,
                               is_expected_from_validation_info, is_valid,
                               validate)


@dataclass(frozen=True, slots=True)
class _ValidationContext:
    object: Object
    supported_mime_types: frozenset[str]


class _Hash(BaseModel):
    hexdigest: HexString
    algorithm: typing.Annotated[
        str,
        is_valid(
            lambda v, i: v in SUPPORTED_HASH_ALGORITHMS,
            lambda i: PydanticCustomError(
                "unexpected",
                f"Algorithm should be one of: {", ".join(SUPPORTED_HASH_ALGORITHMS)}",
                {"allowed": SUPPORTED_HASH_ALGORITHMS},
            ),
        ),
    ]


class _BaseFile(BaseModel):
    object_id: typing.Annotated[
        typing.Optional[int],
        Strict(),
        is_expected_from_validation_info(lambda info: info.context.object.object_id, allow_none=True),
    ] = None


# pyflakes doesn't like string literals in type annotations that don't correspond to a Python identifier
_base64_content = "base64_content"
_base64_preview_image = "base64_preview_image"


class _DatabaseFile(_BaseFile):
    storage: typing.Literal["database"]
    original_file_name: NonEmptyString
    if typing.TYPE_CHECKING:
        content: bytes
    else:
        content: Base64Encoded(_base64_content)
    hash: OptionalNotNone[_Hash]

    @cached_property
    def hash_info(self) -> File.HashInfo:
        info = File.HashInfo.from_binary_data(
            algorithm=DEFAULT_HASH_ALGORITHM if self.hash is None else self.hash.algorithm,
            binary_data=self.content,
        )
        assert info is not None, "algorithm is validated to be supported"
        if self.hash is not None and self.hash.hexdigest != info.hexdigest:
            raise PydanticCustomError(
                "unexpected",
                "Hash hexdigest should be {expected}",
                {"expected": info.hexdigest},
            )
        return info

    @model_validator(mode="after")
    def check_hash_info(self) -> typing.Self:
        self.hash_info  # pylint: disable=pointless-statement
        return self


class _DatabaseFileWithPreview(_DatabaseFile):
    if typing.TYPE_CHECKING:
        preview_image_binary_data: bytes
    else:
        preview_image_binary_data: Base64Encoded(_base64_preview_image)
    preview_image_mime_type: typing.Annotated[
        str,
        AfterValidator(lambda value: value.lower()),
        is_valid(
            lambda v, i: v in i.context.supported_mime_types,
            lambda i: PydanticCustomError(
                "unexpected",
                f"MIME type should be one of: {", ".join(i.context.supported_mime_types)}",
                {"allowed": i.context.supported_mime_types},
            ),
        ),
    ] = ""


class _LocalReferenceFile(_BaseFile):
    storage: typing.Literal["local_reference"]
    filepath: NonEmptyString
    hash: OptionalNotNone[_Hash]


class _UrlFile(_BaseFile):
    storage: typing.Literal["url"]
    url: Url


type _DatabaseFileUnion = typing.Annotated[_DatabaseFile, Tag("without_preview_image")] | typing.Annotated[_DatabaseFileWithPreview, Tag("with_preview_image")]
type _File = typing.Annotated[
    _DatabaseFileUnion | _LocalReferenceFile | _UrlFile,
    Field(discriminator="storage"),
]


def file_info_to_json(file_info: File, include_content: bool = True) -> typing.Dict[str, typing.Any]:
    file_json = {
        'object_id': file_info.object_id,
        'file_id': file_info.id,
        'storage': file_info.storage
    }
    if file_info.storage == 'database':
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
        if file_info.preview_image_binary_data and file_info.preview_image_mime_type:
            file_json['base64_preview_image'] = base64.b64encode(file_info.preview_image_binary_data).decode('utf-8')
            file_json['preview_image_mime_type'] = file_info.preview_image_mime_type
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
        object = get_object(object_id=object_id)
        if object.action_id is not None:
            action = get_action(action_id=object.action_id)
            if action.type is None or not action.type.enable_files:
                return {
                    "message": "Adding files is not enabled for objects of this type"
                }, 403
        try:
            request_data: _File = validate(
                _File,
                request_json,
                context=_ValidationContext(
                    object,
                    frozenset(flask.current_app.config["MIME_TYPES"].values()),
                ),
            )
        except ValidatingError as e:
            msg, _, loc = e.message.rpartition(" (")
            if not msg:
                return e.response
            assert loc.endswith(")")
            loc = loc[:-1]
            for prefix in "database.without_preview_image.", "database.with_preview_image.", "local_reference.", "url.":
                if loc.startswith(prefix):
                    e.message = f"{msg} ({loc.removeprefix(prefix)})"
                    break
            return e.response
        if request_data.storage == "database":
            file = create_database_file(
                object_id=object_id,
                user_id=flask.g.user.id,
                file_name=request_data.original_file_name,
                save_content=lambda stream: typing.cast(None, stream.write(request_data.content)),
                hash=request_data.hash_info,
                preview_image_binary_data=getattr(request_data, "preview_image_binary_data", None),
                preview_image_mime_type=getattr(request_data, "preview_image_mime_type", None)
            )
        elif request_data.storage == "local_reference":
            try:
                file = create_local_file_reference(
                    object_id=object_id,
                    user_id=flask.g.user.id,
                    filepath=request_data.filepath,
                    hash=None if request_data.hash is None else File.HashInfo(
                        algorithm=request_data.hash.algorithm,
                        hexdigest=request_data.hash.hexdigest,
                    ),
                )
            except errors.UnauthorizedRequestError:
                return {
                    "message": "user not authorized to add this path"
                }, 403
        else:
            assert request_data.storage == "url"
            file = create_url_file(
                object_id=object_id,
                user_id=flask.g.user.id,
                url=request_data.url,
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
