import base64
import typing
from collections.abc import Callable, Sequence
from contextlib import suppress
from itertools import groupby

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, TypeAdapter, ValidationError, ValidationInfo, model_validator, SerializerFunctionWrapHandler, WrapSerializer
from pydantic_core import ErrorDetails, PydanticCustomError

from ....logic import errors, users
from ....logic.utils import parse_url
from ....models import Permissions


class _ErrorDict(typing.TypedDict):
    msg: str
    input: typing.NotRequired[typing.Any]


type _ValidationError = _ErrorDict | dict[int, _ValidationError] | dict[str, _ValidationError]


def generate_example(model: type[BaseModel]) -> dict[str, typing.Any]:
    return {
        field_name: field_info.examples[0]  # type: ignore[index]
        for field_name, field_info in model.model_fields.items()
    }


def _error_details_to_returned_error(error_details: list[ErrorDetails], idx: int = 0, /) -> _ValidationError:
    match error_details:
        case [{"type": type_, "loc": loc, "msg": msg, "input": input_}] if len(loc) == idx:
            if type_ == "missing":
                return {"msg": msg}
            if type_ in ("model_type", "model_attributes_type"):
                msg = "Input should be an object"
            return {"msg": msg, "input": input_}
    return {
        i: _error_details_to_returned_error(list(es), idx + 1)
        for i, es in groupby(error_details, lambda e: e["loc"][idx])
    }


class ValidatingError(ValueError):
    def __init__(self, e: _ValidationError, /) -> None:
        super().__init__(e)
        self.error_details = e
        loc = []
        # depth first search for `_ErrorDict`, keeping track of path in `loc`
        while True:
            try:
                error_dict = TypeAdapter(_ErrorDict).validate_python(e, extra="forbid", strict=True)
            except ValidationError:
                loc_part, e = typing.cast(tuple[int | str, _ValidationError], next(iter(e.items())))
                loc.append(str(loc_part))
            else:
                msg = error_dict["msg"]
                break
        # TODO: refactor error handling specific to ObjectFiles
        for prefix in [
            ["database", "without_preview_image"],
            ["database", "with_preview_image"],
            ["local_reference"],
            ["url"]
        ]:
            if len(loc) > len(prefix) and loc[:len(prefix)] == prefix:
                loc = loc[len(prefix):]
                break
        self.message = f"{msg} ({".".join(loc)})" if loc else msg

    def error_details_by_path(self) -> dict[Sequence[str | int], _ErrorDict]:
        error_dict_by_path: dict[Sequence[str | int], _ErrorDict] = {}
        e_queue: list[tuple[list[str | int], typing.Any]] = [([], self.error_details)]
        while e_queue:
            path, e = e_queue.pop(0)
            if not isinstance(e, dict):
                continue
            if tuple(e.keys()) in [("msg", "input"), ("msg",)]:
                for prefix in [
                    ["database", "without_preview_image"],
                    ["database", "with_preview_image"],
                    ["local_reference"],
                    ["url"]
                ]:
                    if len(path) > len(prefix) and path[:len(prefix)] == prefix:
                        path = path[len(prefix):]
                        break
                error_dict_by_path[tuple(path)] = typing.cast(_ErrorDict, e)
            else:
                for key, value in e.items():
                    e_queue.append((path + [key,], value))
        return error_dict_by_path


@typing.overload
def validate[Model: BaseModel](model: type[Model], data: typing.Any, /, *, context: typing.Any = None) -> Model:
    ...


@typing.overload
def validate(type_: typing.Any, data: typing.Any, /, *, context: typing.Any = None) -> typing.Any:
    ...


def validate(model_or_type: typing.Any, data: typing.Any, /, *, context: typing.Any = None) -> typing.Any:
    try:
        if isinstance(model_or_type, type) and issubclass(model_or_type, BaseModel):
            return model_or_type.model_validate(data, context=context, extra="forbid")
        if not isinstance(model_or_type, TypeAdapter):
            model_or_type = TypeAdapter(model_or_type)
        return model_or_type.validate_python(data, context=context, extra="forbid")
    except ValidationError as e:
        raise ValidatingError(_error_details_to_returned_error(e.errors(include_url=False)))


type NonEmptyString = typing.Annotated[str, Field(min_length=1)]


def _is_expected[T](value: T, *, expected: T, allow_none: bool = False) -> T:
    assert not allow_none or expected is not None, "`allow_none=True` doesn't make sense if `expected is None`"
    if allow_none and value is None or value == expected:
        return value
    raise PydanticCustomError(
        "unexpected",
        "Input should be {expected}",
        {"expected": expected},
    )


def is_expected_from_validation_info[ContextT, T](getter: Callable[[ValidationInfo[ContextT]], T], /, *, allow_none: bool = False) -> AfterValidator:
    return AfterValidator(lambda value, info: _is_expected(value, expected=getter(info), allow_none=allow_none))


class _PopulateMissingOrExpectFromValidationInfo[T, ContextT]:
    def __init__(self, getter: Callable[[ValidationInfo[ContextT]], T], /) -> None:
        self._getter = getter
        self._checked_by_model_validator = False

    def __call__(self, value: T, info: ValidationInfo[ContextT]) -> T:
        assert self._checked_by_model_validator, "populate_missing_or_expect_from_validation_info only makes sense on subclasses of ModelWithDefaultsFromValidationInfo"
        return _is_expected(value, expected=self._getter(info))


def populate_missing_or_expect_from_validation_info[T, ContextT](getter: Callable[[ValidationInfo[ContextT]], T], /) -> AfterValidator:
    return AfterValidator(_PopulateMissingOrExpectFromValidationInfo(getter))


class ModelWithDefaultsFromValidationInfo(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def populate_missing[ContextT](cls, data: typing.Any, info: ValidationInfo[ContextT]) -> typing.Any:
        if not isinstance(data, dict):
            return data
        for k, v in cls.model_fields.items():
            match [x.func for x in v.metadata if isinstance(x, AfterValidator) and isinstance(x.func, _PopulateMissingOrExpectFromValidationInfo)]:
                case [f]:
                    f._checked_by_model_validator = True
                    if k not in data:
                        data[k] = f._getter(info)
                case fs:
                    assert not fs, "populate_missing_or_expect_from_validation_info only makes sense when unique"
        return data


def is_valid[T, ContextT](predicate: Callable[[T, ValidationInfo[ContextT]], bool], error_generator: Callable[[ValidationInfo[ContextT]], PydanticCustomError]) -> AfterValidator:
    def check(value: T, info: ValidationInfo[ContextT]) -> T:
        if predicate(value, info):
            return value
        raise error_generator(info)

    return AfterValidator(check)


# works because defaults are not validated by Pydantic (unless it has been enabled, which makes this type erroneous)
T = typing.TypeVar("T")
OptionalNotNone = typing.Annotated[
    T | None,
    is_valid(
        lambda v, i: v is not None,
        lambda i: PydanticCustomError("none_forbidden", "Input should be absent or set to a valid value"),
    ),
    Field(default=None),  # Pydantic discourages `type` syntax (`typing.TypeAliasType`) for `default`
]


type HexString = typing.Annotated[
    str,
    is_valid(
        lambda v, i: set(v).issubset("0123456789abcdef"),
        lambda i: PydanticCustomError("hex_string", "String should be exclusively lowercase hex characters"),
    ),
]


def Base64Encoded(alias: str | None = None) -> typing.Any:
    def convert[ContextT](value: str, info: ValidationInfo[ContextT]) -> bytes:
        try:
            if not isinstance(value, str):
                raise ValueError
            return base64.b64decode(value.encode("utf-8"), validate=True)
        except Exception:
            raise PydanticCustomError("base64_parsing", "Input should be a base64 encoded string")

    if alias is None:
        return typing.Annotated[bytes, BeforeValidator(convert)]
    else:
        return typing.Annotated[bytes, BeforeValidator(convert), Field(validation_alias=alias)]


def _is_url[ContextT](value: str, info: ValidationInfo[ContextT]) -> str:
    try:
        parse_url(value)
    except errors.InvalidURLError:
        raise PydanticCustomError("url_parsing", "String should be a valid URL")
    except errors.URLTooLongError:
        raise PydanticCustomError("url_too_long", "URL exceeds length limit")
    except errors.InvalidIPAddressError:
        raise PydanticCustomError("url_parsing", "URL contains an invalid IP address")
    except errors.InvalidPortNumberError:
        raise PydanticCustomError("url_parsing", "URL contains an invalid port number")
    return value


type Url = typing.Annotated[str, AfterValidator(_is_url)]


def _user_exists(value: int) -> int:
    try:
        users.check_user_exists(value)
    except errors.UserDoesNotExistError:
        raise PydanticCustomError("no_such_user", "User should exist")
    return value


type UserId = typing.Annotated[int, AfterValidator(_user_exists)]


def _permissions_validator(value: typing.Any) -> Permissions:
    if isinstance(value, Permissions):
        return value
    if isinstance(value, str):
        with suppress(ValueError):
            return Permissions.from_name(value)
    raise PydanticCustomError("enum", "Input should be 'none', 'read', 'write' or 'grant'")


def _permissions_serializer(permissions: Permissions, handler: SerializerFunctionWrapHandler) -> str:
    return permissions.name.lower()


type PermissionsModel = typing.Annotated[Permissions, BeforeValidator(_permissions_validator), WrapSerializer(_permissions_serializer)]
