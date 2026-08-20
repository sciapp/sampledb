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
from ..utils import Resource
from .authentication import object_permissions_required
from .utils.validation import Base64Encoded, HexString, NonEmptyString, OptionalNotNone, Url, is_expected_from_validation_info, is_valid, method, generate_example
from .utils.responses import ForbiddenErrorModel, NotFoundErrorModel, CreatedResponseModel, ReturnValue


class _Hash(BaseModel):
    hexdigest: HexString = Field(description="the hexadecimal representation of the hash", examples=["ee26b0dd4af7e749aa1a8ee3c10ae9923f618980772e473f8819a5d4940e0db27ac185f8a0e1d5f84f88bc887fd67b143732c304cc5fa9ad8e6f57f50028a8ff"])
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
    ] = Field(description="the hash algorithm used", examples=["sha512"])


class _BaseFile(BaseModel):
    object_id: typing.Annotated[
        typing.Optional[int],
        Strict(),
        is_expected_from_validation_info(lambda info: info.context.object.object_id, allow_none=True),
    ] = Field(None, description="the ID of an existing object", examples=[1])


# pyflakes doesn't like string literals in type annotations that don't correspond to a Python identifier
_base64_content = "base64_content"
_base64_preview_image = "base64_preview_image"


class _DatabaseFile(_BaseFile):
    storage: typing.Literal["database"] = Field(description="the storage type for the file", examples=["database"])
    original_file_name: NonEmptyString = Field(description="the name of the file", examples=["example.txt"])
    if typing.TYPE_CHECKING:
        content: bytes
    else:
        content: Base64Encoded(_base64_content) = Field(description="the base64 encoded content of the file", examples=["ZXhhbXBsZQ=="])
    hash: OptionalNotNone[_Hash] = Field(description="optional hash information for the file", examples=[generate_example(_Hash)])

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
        preview_image_binary_data: Base64Encoded(_base64_preview_image) = Field(description="the base64 encoded preview image for the file", examples=["iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAFklEQVR4nGP8////fwY8gAmf5PBRAAAbbgQMid1tCwAAAABJRU5ErkJggg=="])
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
    ] = Field("", description="the MIME type for the file preview image", examples=["image/png"])


class _LocalReferenceFile(_BaseFile):
    storage: typing.Literal["local_reference"] = Field(description="the storage type for the file", examples=["local_reference"])
    filepath: NonEmptyString = Field(description="the local path for the file", examples=["local_reference"])
    hash: OptionalNotNone[_Hash] = Field(description="optional hash information for the file", examples=[{"hexdigest": "ee26b0dd4af7e749aa1a8ee3c10ae9923f618980772e473f8819a5d4940e0db27ac185f8a0e1d5f84f88bc887fd67b143732c304cc5fa9ad8e6f57f50028a8ff", "algorithm": "sha512"}])


class _UrlFile(_BaseFile):
    storage: typing.Literal["url"] = Field(description="the storage type for the file", examples=["url"])
    url: Url = Field(description="the URL for the file", examples=["https://example.com"])


type _DatabaseFileUnion = typing.Annotated[_DatabaseFile, Tag("without_preview_image")] | typing.Annotated[_DatabaseFileWithPreview, Tag("with_preview_image")]
type _File = typing.Annotated[
    _DatabaseFileUnion | _LocalReferenceFile | _UrlFile,
    Field(discriminator="storage"),
]


class DatabaseFileModel(BaseModel):
    class HashInfoModel(BaseModel):
        hexdigest: str = Field(description="the hexadecimal representation of the hash", examples=["ee26b0dd4af7e749aa1a8ee3c10ae9923f618980772e473f8819a5d4940e0db27ac185f8a0e1d5f84f88bc887fd67b143732c304cc5fa9ad8e6f57f50028a8ff"])
        algorithm: str = Field(description="the hash algorithm used", examples=["sha512"])

    object_id: int = Field(description="the ID of the object the file belongs to", examples=[1])
    file_id: int = Field(description="the ID of the file", examples=[1])
    storage: str = Field(description="the storage type for the file", examples=["database"])
    original_file_name: typing.Optional[str] = Field(None, description="the name of the file", examples=["example.txt"])
    base64_content: typing.Optional[str] = Field(None, description="the base64 encoded content of the file", examples=["ZXhhbXBsZQ=="])
    hash: typing.Optional[HashInfoModel] = Field(None, description="optional hash information for the file", examples=[generate_example(HashInfoModel)])
    base64_preview_image: typing.Optional[str] = Field(None, description="the base64 encoded preview image for the file", examples=["iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAFklEQVR4nGP8////fwY8gAmf5PBRAAAbbgQMid1tCwAAAABJRU5ErkJggg=="])
    preview_image_mime_type: typing.Optional[str] = Field(None, description="the MIME type for the file preview image", examples=["image/png"])

    @classmethod
    def from_file(cls, file_info: File, include_content: bool = True) -> typing.Self:
        assert file_info.storage == 'database'
        return cls(
            object_id=file_info.object_id,
            file_id=file_info.id,
            storage=file_info.storage,
            original_file_name=file_info.original_file_name,
            base64_content=base64.b64encode(file_info.open().read()).decode('utf-8') if include_content else None,
            hash=file_info.data.get('hash') if file_info.data else None,
            base64_preview_image=base64.b64encode(file_info.preview_image_binary_data).decode('utf-8') if file_info.preview_image_binary_data and file_info.preview_image_mime_type else None,
            preview_image_mime_type=file_info.preview_image_mime_type if file_info.preview_image_binary_data and file_info.preview_image_mime_type else None,
        )


class UrlFileModel(BaseModel):
    object_id: int = Field(description="the ID of the object the file belongs to", examples=[1])
    file_id: int = Field(description="the ID of the file", examples=[1])
    storage: str = Field(description="the storage type for the file", examples=["url"])
    url: typing.Optional[str] = Field(None, description="the URL of the file", examples=["https://example.com"])

    @classmethod
    def from_file(cls, file_info: File) -> typing.Self:
        assert file_info.storage == 'url'
        return cls(
            object_id=file_info.object_id,
            file_id=file_info.id,
            storage=file_info.storage,
            url=file_info.url if file_info.storage == 'url' else None
        )


def file_model_from_file(file_info: File, include_content: bool = True) -> DatabaseFileModel | UrlFileModel:
    if file_info.storage == 'database':
        return DatabaseFileModel.from_file(file_info, include_content=include_content)
    if file_info.storage == 'url':
        return UrlFileModel.from_file(file_info)
    assert False


class ObjectFile(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])
        file_id: int = Field(description="the ID of an existing file for this object", examples=[1])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ReturnValue[DatabaseFileModel | UrlFileModel] | NotFoundErrorModel | ForbiddenErrorModel:
        """
        Get an object file.
        """
        try:
            file_info = get_file_for_object(object_id=path.object_id, file_id=path.file_id)
            if file_info is None:
                raise errors.FileDoesNotExistError()
        except errors.FileDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"file {path.file_id} of object {path.object_id} does not exist"
            )
        if file_info.is_hidden:
            return ForbiddenErrorModel(
                error="Forbidden",
                message=f"file {path.file_id} of object {path.object_id} has been hidden"
            )
        return ReturnValue(file_model_from_file(file_info=file_info))


class ObjectFiles(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    @dataclass(frozen=True, slots=True)
    class ValidationContext:
        object: Object
        supported_mime_types: frozenset[str]

        @classmethod
        def from_path(cls, path: ObjectFiles.PathModel) -> typing.Self:
            return cls(
                object=get_object(object_id=path.object_id),
                supported_mime_types=frozenset(flask.current_app.config["MIME_TYPES"].values()),
            )

    @object_permissions_required(Permissions.WRITE)
    @method(request_body_context_builder=ValidationContext.from_path)
    def post(self, path: PathModel, request_body: _File) -> CreatedResponseModel | ForbiddenErrorModel:
        """
        Create a new file for an object.
        """
        object = get_object(object_id=path.object_id)
        if object.action_id is not None:
            action = get_action(action_id=object.action_id)
            if action.type is None or not action.type.enable_files:
                return ForbiddenErrorModel(
                    error="Forbidden",
                    message="Adding files is not enabled for objects of this type"
                )
        if request_body.storage == "database":
            file = create_database_file(
                object_id=path.object_id,
                user_id=flask.g.user.id,
                file_name=request_body.original_file_name,
                save_content=lambda stream: typing.cast(None, stream.write(request_body.content)),
                hash=request_body.hash_info,
                preview_image_binary_data=getattr(request_body, "preview_image_binary_data", None),
                preview_image_mime_type=getattr(request_body, "preview_image_mime_type", None)
            )
        elif request_body.storage == "local_reference":
            try:
                file = create_local_file_reference(
                    object_id=path.object_id,
                    user_id=flask.g.user.id,
                    filepath=request_body.filepath,
                    hash=None if request_body.hash is None else File.HashInfo(
                        algorithm=request_body.hash.algorithm,
                        hexdigest=request_body.hash.hexdigest,
                    ),
                )
            except errors.UnauthorizedRequestError:
                return ForbiddenErrorModel(
                    error="Forbidden",
                    message="user not authorized to add this path"
                )
        else:
            assert request_body.storage == "url"
            file = create_url_file(
                object_id=path.object_id,
                user_id=flask.g.user.id,
                url=request_body.url,
            )
        file_url = flask.url_for(
            '.object_file',
            object_id=file.object_id,
            file_id=file.id,
            _external=True
        )
        return CreatedResponseModel(
            location=file_url
        )

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ReturnValue[typing.List[DatabaseFileModel | UrlFileModel]]:
        """
        List all files for an object.
        """
        return ReturnValue([
            file_model_from_file(file_info=file_info, include_content=False)
            for file_info in get_files_for_object(path.object_id)
            if not file_info.is_hidden
        ])
