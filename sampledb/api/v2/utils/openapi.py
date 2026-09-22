import functools
import inspect
import json
import re
import typing
from collections.abc import Callable, Generator
from dataclasses import dataclass
from http import HTTPStatus

import flask
import pydantic.json_schema
import yaml
from pydantic import BaseModel

from ...utils import Resource, ResponseData
from .validation import validate, ValidatingError
from .responses import make_response, ResourceMethodResult, ReturnValue, RedirectResponseModel, ErrorDetailsModel, NoContentModel, PathErrorDetailModel, QueryErrorDetailModel, RequestBodyErrorDetailModel


@dataclass(frozen=True, kw_only=True, slots=True)
class OpenAPIMethodInformation:
    default_status_code: int
    path_model: type[BaseModel] | None
    query_model: type[BaseModel] | None
    request_body_model: type | None
    return_type_hint: type | None
    extra_error_details_models: list[type[ErrorDetailsModel]]


class GenericOperationCallable[R: Resource](typing.Protocol):
    openapi_method_info: OpenAPIMethodInformation

    def __call__(_, self: R, **kwargs: typing.Any) -> ResponseData:
        ...


class BareCallable[R: Resource](typing.Protocol):
    __name__: str

    def __call__(self_, self: R) -> ResourceMethodResult:
        ...


class PathCallable[R: Resource, PM: BaseModel](typing.Protocol):
    __name__: str

    def __call__(self_, self: R, path: PM) -> ResourceMethodResult:
        ...


class QueryCallable[R: Resource, QM: BaseModel](typing.Protocol):
    __name__: str

    def __call__(self_, self: R, query: QM) -> ResourceMethodResult:
        ...


class RequestBodyCallable[R: Resource, ReqM](typing.Protocol):
    __name__: str

    def __call__(self_, self: R, request_body: ReqM) -> ResourceMethodResult:
        ...


class PathQueryCallable[R: Resource, PM: BaseModel, QM: BaseModel](typing.Protocol):
    __name__: str

    def __call__(self_, self: R, path: PM, query: QM) -> ResourceMethodResult:
        ...


class PathRequestBodyCallable[R: Resource, PM: BaseModel, ReqM](typing.Protocol):
    __name__: str

    def __call__(self_, self: R, path: PM, request_body: ReqM) -> ResourceMethodResult:
        ...


class PathQueryRequestBodyCallable[R: Resource, PM: BaseModel, QM: BaseModel, ReqM](typing.Protocol):
    __name__: str

    def __call__(self_, self: R, path: PM, query: QM, request_body: ReqM) -> ResourceMethodResult:
        ...


R = typing.TypeVar('R', bound=Resource)
PM = typing.TypeVar('PM', bound=BaseModel)
QM = typing.TypeVar('QM', bound=BaseModel)
ReqM = typing.TypeVar('ReqM')  # , bound=BaseModel)


class PathValidationFailedModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.BAD_REQUEST
    TITLE: typing.ClassVar[str] = "Failed to validate URL path."


class QueryValidationFailedModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.BAD_REQUEST
    TITLE: typing.ClassVar[str] = "Failed to validate URL query parameters."


class RequestBodyValidationFailedModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.BAD_REQUEST
    TITLE: typing.ClassVar[str] = "Failed to validate request body data."


class MethodNotAllowedForReadOnlyUsersModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.FORBIDDEN
    TITLE: typing.ClassVar[str] = "Read-only users may not make changes via the API."


def method(
        *,
        default_status_code: int = 200,
        request_body_context_builder: Callable[[PM], typing.Any] | None = None,
        allow_read_only: bool = False
) -> Callable[
    [
        BareCallable[R] |
        PathCallable[R, PM] |
        QueryCallable[R, QM] |
        RequestBodyCallable[R, ReqM] |
        PathQueryCallable[R, PM, QM] |
        PathRequestBodyCallable[R, PM, ReqM] |
        PathQueryRequestBodyCallable[R, PM, QM, ReqM]
    ],
    GenericOperationCallable[R]
]:
    def method_decorator_impl(
            func: (
                BareCallable[R] |
                PathCallable[R, PM] |
                QueryCallable[R, QM] |
                RequestBodyCallable[R, ReqM] |
                PathQueryCallable[R, PM, QM] |
                PathRequestBodyCallable[R, PM, ReqM] |
                PathQueryRequestBodyCallable[R, PM, QM, ReqM]
            )
    ) -> GenericOperationCallable[R]:
        extra_error_details_models: list[type[ErrorDetailsModel]] = []
        if not (allow_read_only or func.__name__ == 'get'):
            extra_error_details_models.append(MethodNotAllowedForReadOnlyUsersModel)
        type_hints = typing.get_type_hints(func)
        path_model: type[PM] | None = type_hints.get('path')
        assert path_model is None or issubclass(path_model, BaseModel)
        if path_model is not None:
            extra_error_details_models.append(PathValidationFailedModel)
        query_model: type[QM] | None = type_hints.get('query')
        assert query_model is None or issubclass(query_model, BaseModel)
        if query_model is not None:
            extra_error_details_models.append(QueryValidationFailedModel)
        request_body_model: type[ReqM] | None = type_hints.get('request_body')
        if isinstance(request_body_model, typing.TypeAliasType):
            request_body_model = request_body_model.__value__
        if request_body_model is not None:
            extra_error_details_models.append(RequestBodyValidationFailedModel)
        # no assert for request_body_model to be BaseModel or None, as various other inputs currently exist, e.g. for permissions
        return_type_hint: type | None = type_hints.get('return')
        assert return_type_hint is not None

        class KWArgsDict(typing.TypedDict, total=False):
            path: PM
            query: QM
            request_body: ReqM

        @functools.wraps(func)
        def method_impl(self: R, **kwargs: typing.Any) -> ResponseData:
            if flask.g.user.is_readonly and not (allow_read_only or func.__name__ == 'get'):
                return make_response(
                    result=MethodNotAllowedForReadOnlyUsersModel(detail=f"The {func.__name__.upper()} method for this resource is used to make changes, however user #{flask.g.user.id} is set read-only, and read-only users may not make any changes via the API."),
                    default_status_code=HTTPStatus.FORBIDDEN,
                    return_type_hint=None
                )
            new_kwargs: KWArgsDict = {}
            if path_model is not None:
                try:
                    new_kwargs['path'] = validate(
                        path_model,
                        kwargs
                    )
                except ValidatingError as e:
                    return make_response(
                        result=PathValidationFailedModel(
                            detail=e.message,
                            errors=[
                                PathErrorDetailModel(
                                    path_parameter=str(path[0]),
                                    detail=error_dict["msg"],
                                    input=error_dict.get("input"),
                                )
                                for path, error_dict in e.error_details_by_path().items()
                            ],
                        ),
                        default_status_code=default_status_code,
                        return_type_hint=return_type_hint,
                    )
            if query_model is not None:
                try:
                    new_kwargs['query'] = validate(
                        query_model,
                        {
                            key: values[0] if len(values) == 1 else values
                            for key, values in flask.request.args.lists()
                        }
                    )
                except ValidatingError as e:
                    return make_response(
                        result=QueryValidationFailedModel(
                            detail=e.message,
                            errors=[
                                QueryErrorDetailModel(
                                    query_parameter=str(path[0]),
                                    detail=error_dict["msg"],
                                    input=error_dict.get("input"),
                                )
                                for path, error_dict in e.error_details_by_path().items()
                            ],
                        ),
                        default_status_code=default_status_code,
                        return_type_hint=return_type_hint,
                    )
            if request_body_model is not None:
                try:
                    new_kwargs['request_body'] = validate(
                        request_body_model,
                        flask.request.get_json(force=True) if flask.request.content_length else None,
                        context=request_body_context_builder(new_kwargs['path']) if request_body_context_builder is not None else None
                    )
                except ValidatingError as e:
                    return make_response(
                        result=RequestBodyValidationFailedModel(
                            detail=e.message,
                            errors=[
                                RequestBodyErrorDetailModel(
                                    json_pointer="/" + "/".join(str(path_element) for path_element in path),
                                    detail=error_dict["msg"],
                                    input=error_dict.get("input"),
                                )
                                for path, error_dict in e.error_details_by_path().items()
                            ],
                        ),
                        default_status_code=default_status_code,
                        return_type_hint=return_type_hint,
                    )
            return make_response(
                result=func(self, **new_kwargs),  # type: ignore[misc]
                default_status_code=default_status_code,
                return_type_hint=return_type_hint,
            )

        method_impl.openapi_method_info = OpenAPIMethodInformation(  # type: ignore[attr-defined]
            default_status_code=default_status_code,
            path_model=path_model,
            query_model=query_model,
            request_body_model=request_body_model,
            extra_error_details_models=extra_error_details_models,
            return_type_hint=return_type_hint
        )
        return method_impl  # type: ignore[return-value]
    return method_decorator_impl


def _generate_description_by_status_code(
        status_code: int
) -> str:
    status = HTTPStatus(status_code)
    return f"{status.phrase}: {status.description.replace('--', '—')}"


@functools.cache
def generate_openapi_spec() -> dict[str, typing.Any]:
    spec_dict: dict[str, typing.Any] = {
        "openapi": "3.2.0",
        "info": {
            "title": "SampleDB API",
            "description": "HTTP API for SampleDB",
            "version": "0.2.0",
        },
        "paths": {},
        "servers": [
            {
                "url": flask.url_for('frontend.index', _external=True).rstrip('/') + '/api/v2',
                "description": "SampleDB instance"
            }
        ],
        "components": {
            "schemas": {},
            "securitySchemes": {
                "basicAuth": {
                    "type": "http",
                    "scheme": "basic"
                },
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer"
                }
            }
        },
        "security": [
            {
                "basicAuth": []
            }, {
                "bearerAuth": []
            }
        ]
    }
    for rule in flask.current_app.url_map.iter_rules():
        rule_path = rule.rule
        if not rule_path.startswith("/api/v2"):
            continue
        assert rule.endpoint.startswith('api_v2.')
        if rule.endpoint == 'api_v2.errors':
            continue
        rule_path = rule_path.removeprefix('/api/v2')
        rule_path = re.sub(r'<([^:>]+:)?([^>]+)>', r'{\2}', rule_path)
        view_function = flask.current_app.view_functions.get(rule.endpoint)
        assert view_function is not None
        resource_class = Resource.view_function_map.get(view_function)
        assert resource_class is not None, rule.endpoint
        if resource_class in (OpenAPISpecJSON, OpenAPISpecYAML):
            continue
        assert rule.methods is not None
        for method in rule.methods:
            method = method.lower()
            if method not in ('get', 'post', 'put', 'delete'):
                continue
            assert hasattr(resource_class, method)
            resource_method = getattr(resource_class, method)
            assert hasattr(resource_method, 'openapi_method_info')
            method_info = getattr(resource_method, 'openapi_method_info')
            assert isinstance(method_info, OpenAPIMethodInformation)
            if rule_path not in spec_dict["paths"]:
                spec_dict["paths"][rule_path] = {}
            spec_dict["paths"][rule_path][method] = {
                "parameters": [],
                "responses": {},
                "tags": [resource_method.__module__.rsplit('.', 1)[-1]],
            }
            assert resource_method.__doc__ is not None and resource_method.__doc__.strip(), f"{resource_method} must have a docstring"
            if resource_method.__doc__ is not None:
                docstring = resource_method.__doc__.strip()
                if '\n' in docstring:
                    summary, description = docstring.split('\n', 1)
                else:
                    summary = docstring
                    description = ''
                assert summary
                spec_dict["paths"][rule_path][method]["summary"] = summary
                if description:
                    spec_dict["paths"][rule_path][method]["description"] = description
            if method_info.path_model:
                path_model_json_schema = pydantic.json_schema.model_json_schema(method_info.path_model, ref_template="#/components/schemas/{model}")
                if '$defs' in path_model_json_schema:
                    for defs_key in path_model_json_schema['$defs']:
                        if defs_key in spec_dict["components"]["schemas"]:
                            assert spec_dict["components"]["schemas"][defs_key] == path_model_json_schema['$defs'][defs_key]
                        spec_dict["components"]["schemas"][defs_key] = path_model_json_schema['$defs'][defs_key]
                    del path_model_json_schema["$defs"]
                assert path_model_json_schema['type'] == 'object'
                for parameter_name, parameter_schema in path_model_json_schema['properties'].items():
                    spec_dict["paths"][rule_path][method]["parameters"].append({
                        "name": parameter_name,
                        "in": "path",
                        "required": parameter_name in path_model_json_schema.get('required', []),
                        "schema": parameter_schema
                    })
                    assert "description" in parameter_schema, f"missing documentation for path parameter {parameter_name} for {method.upper()} {rule}"
                    spec_dict["paths"][rule_path][method]["parameters"][-1]["description"] = parameter_schema["description"]
                    assert "examples" in parameter_schema and len(parameter_schema["examples"]) == 1, f"missing example for path parameter {parameter_name} for {method.upper()} {rule}"
                    spec_dict["paths"][rule_path][method]["parameters"][-1]["example"] = parameter_schema["examples"][0]
            if method_info.query_model:
                query_model_json_schema = pydantic.json_schema.model_json_schema(method_info.query_model, ref_template="#/components/schemas/{model}")
                if '$defs' in query_model_json_schema:
                    for defs_key in query_model_json_schema['$defs']:
                        if defs_key in spec_dict["components"]["schemas"]:
                            assert spec_dict["components"]["schemas"][defs_key] == query_model_json_schema['$defs'][defs_key]
                        spec_dict["components"]["schemas"][defs_key] = query_model_json_schema['$defs'][defs_key]
                    del query_model_json_schema["$defs"]
                assert query_model_json_schema['type'] == 'object'
                for parameter_name, parameter_schema in query_model_json_schema['properties'].items():
                    spec_dict["paths"][rule_path][method]["parameters"].append({
                        "name": parameter_name,
                        "in": "query",
                        "required": parameter_name in query_model_json_schema.get('required', []),
                        "schema": parameter_schema
                    })
                    assert "description" in parameter_schema, f"missing documentation for query parameter {parameter_name} for {method.upper()} {rule}"
                    spec_dict["paths"][rule_path][method]["parameters"][-1]["description"] = parameter_schema["description"]
                    assert "examples" in parameter_schema and len(parameter_schema["examples"]) == 1, f"missing example for query parameter {parameter_name} for {method.upper()} {rule}"
                    spec_dict["paths"][rule_path][method]["parameters"][-1]["example"] = parameter_schema["examples"][0]
            if method_info.request_body_model:
                request_body_required = True
                request_body_model = method_info.request_body_model
                if typing.get_origin(request_body_model) is typing.Union and len(typing.get_args(request_body_model)) == 2 and type(None) in typing.get_args(request_body_model):  # pylint: disable=consider-alternative-union-syntax
                    request_body_required = False
                    request_body_model = next(filter(lambda t: t is not None, typing.get_args(request_body_model)))
                if inspect.isclass(request_body_model) and issubclass(request_body_model, BaseModel):
                    request_body_model_json_schema = pydantic.json_schema.model_json_schema(request_body_model, ref_template="#/components/schemas/{model}")
                else:
                    request_body_model_json_schema = pydantic.TypeAdapter(request_body_model).json_schema(ref_template="#/components/schemas/{model}")
                if request_body_model_json_schema.get('type') == 'object':
                    for property_name, property_schema in request_body_model_json_schema.get('properties', {}).items():
                        assert "description" in property_schema, f"missing documentation for property {property_name} for {method.upper()} {rule} and model {request_body_model}"
                        assert "examples" in property_schema, f"missing example for property {property_name} for {method.upper()} {rule} and model {request_body_model}"
                if '$defs' in request_body_model_json_schema:
                    for defs_key in request_body_model_json_schema['$defs']:
                        if defs_key in spec_dict["components"]["schemas"]:
                            assert spec_dict["components"]["schemas"][defs_key] == request_body_model_json_schema['$defs'][defs_key]
                        spec_dict["components"]["schemas"][defs_key] = request_body_model_json_schema['$defs'][defs_key]
                        if spec_dict["components"]["schemas"][defs_key].get('type') == 'object':
                            for property_name, property_schema in spec_dict["components"]["schemas"][defs_key].get('properties', {}).items():
                                assert "description" in property_schema, f"missing documentation for property {property_name} for {method.upper()} {rule} and model {defs_key}"
                                assert "examples" in property_schema, f"missing example for property {property_name} for {method.upper()} {rule} and model {defs_key}"
                    del request_body_model_json_schema["$defs"]
                spec_dict["paths"][rule_path][method]["requestBody"] = {
                    "content": {
                        "application/json": {
                            "schema": request_body_model_json_schema
                        }
                    },
                    "required": request_body_required,
                }
            if method_info.return_type_hint:
                return_type_hint = method_info.return_type_hint
                if typing.get_origin(return_type_hint) is typing.Union:  # pylint: disable=consider-alternative-union-syntax
                    return_type_options = list(typing.get_args(return_type_hint))
                else:
                    return_type_options = [return_type_hint]
                error_descriptions_per_status_code: dict[int, list[str]] = {}
                for return_type_option in return_type_options + method_info.extra_error_details_models:
                    if inspect.isclass(return_type_option) and issubclass(return_type_option, ErrorDetailsModel):
                        base_error_details_model_json_schema = ErrorDetailsModel.model_json_schema(ref_template="#/components/schemas/{model}")
                        specific_error_details_model_json_schema = return_type_option.model_json_schema(ref_template="#/components/schemas/{model}")
                        for key in set(base_error_details_model_json_schema.keys()).union(set(specific_error_details_model_json_schema.keys())):
                            if key == 'title':
                                continue
                            if key == 'description':
                                assert specific_error_details_model_json_schema.get(key) is None
                                continue
                            assert base_error_details_model_json_schema.get(key) == specific_error_details_model_json_schema.get(key)
                        if return_type_option.STATUS not in error_descriptions_per_status_code:
                            error_descriptions_per_status_code[return_type_option.STATUS] = []
                        if return_type_option.TITLE not in error_descriptions_per_status_code[return_type_option.STATUS]:
                            error_descriptions_per_status_code[return_type_option.STATUS].append(return_type_option.TITLE)
                        if str(return_type_option.STATUS) not in spec_dict["paths"][rule_path][method]["responses"]:
                            return_type_option_json_schema = base_error_details_model_json_schema
                            if '$defs' in return_type_option_json_schema:
                                for defs_key in return_type_option_json_schema['$defs']:
                                    if defs_key in spec_dict["components"]["schemas"]:
                                        assert spec_dict["components"]["schemas"][defs_key] == return_type_option_json_schema['$defs'][defs_key]
                                    spec_dict["components"]["schemas"][defs_key] = return_type_option_json_schema['$defs'][defs_key]
                                del return_type_option_json_schema['$defs']
                            if return_type_option_json_schema['title'] in spec_dict["components"]["schemas"]:
                                assert spec_dict["components"]["schemas"][return_type_option_json_schema['title']] == return_type_option_json_schema
                            spec_dict["components"]["schemas"][return_type_option_json_schema['title']] = return_type_option_json_schema
                            assert return_type_option_json_schema['title'].endswith('Model')
                            response = {
                                "description": error_descriptions_per_status_code[return_type_option.STATUS][0],
                                "content": {
                                    "application/problem+json": {
                                        "schema": {
                                            "$ref": f"#/components/schemas/{return_type_option_json_schema['title']}"
                                        }
                                    }
                                }
                            }
                            spec_dict["paths"][rule_path][method]["responses"][str(return_type_option.STATUS)] = response
                        else:
                            if len(error_descriptions_per_status_code[return_type_option.STATUS]) > 1:
                                spec_dict["paths"][rule_path][method]["responses"][str(return_type_option.STATUS)]["description"] = 'Either: ' + ' Or: '.join(error_descriptions_per_status_code[return_type_option.STATUS])
                            else:
                                spec_dict["paths"][rule_path][method]["responses"][str(return_type_option.STATUS)]["description"] = error_descriptions_per_status_code[return_type_option.STATUS][0]
                    elif inspect.isclass(return_type_option) and issubclass(return_type_option, RedirectResponseModel):
                        assert str(return_type_option.STATUS_CODE) not in spec_dict["paths"][rule_path][method]["responses"]
                        spec_dict["paths"][rule_path][method]["responses"][str(return_type_option.STATUS_CODE)] = {
                            "description": _generate_description_by_status_code(return_type_option.STATUS_CODE),
                            "headers": {
                                "Location": {
                                    "content": {
                                        "text/plain": {
                                            "schema": {
                                                "type": "string",
                                                "description": "the URL the resource can be found at",
                                                "examples": ["https://example.com"]
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    elif inspect.isclass(return_type_option) and issubclass(return_type_option, NoContentModel):
                        assert str(return_type_option.STATUS_CODE) not in spec_dict["paths"][rule_path][method]["responses"]
                        spec_dict["paths"][rule_path][method]["responses"][str(return_type_option.STATUS_CODE)] = {
                            "description": _generate_description_by_status_code(return_type_option.STATUS_CODE)
                        }
                    elif inspect.isclass(return_type_option) and issubclass(return_type_option, BaseModel):
                        assert str(method_info.default_status_code) not in spec_dict["paths"][rule_path][method].get("responses", {})
                        return_type_option_json_schema = return_type_option.model_json_schema(by_alias=True, ref_template="#/components/schemas/{model}")
                        if '$defs' in return_type_option_json_schema:
                            for defs_key in return_type_option_json_schema['$defs']:
                                if defs_key in spec_dict["components"]["schemas"]:
                                    assert spec_dict["components"]["schemas"][defs_key] == return_type_option_json_schema['$defs'][defs_key]
                                spec_dict["components"]["schemas"][defs_key] = return_type_option_json_schema['$defs'][defs_key]
                            del return_type_option_json_schema['$defs']
                        spec_dict["paths"][rule_path][method]["responses"][str(method_info.default_status_code)] = {
                            "description": _generate_description_by_status_code(method_info.default_status_code),
                            "content": {
                                "application/json": {
                                    "schema": return_type_option_json_schema
                                }
                            }
                        }
                    elif typing.get_origin(return_type_option) is list and len(typing.get_args(return_type_option)) == 1 and inspect.isclass(typing.get_args(return_type_option)[0]) and issubclass(typing.get_args(return_type_option)[0], BaseModel):
                        assert str(method_info.default_status_code) not in spec_dict["paths"][rule_path][method].get("responses", {})
                        return_type_option_json_schema = pydantic.TypeAdapter(return_type_option).json_schema(by_alias=True, ref_template="#/components/schemas/{model}")
                        if '$defs' in return_type_option_json_schema:
                            for defs_key in return_type_option_json_schema['$defs']:
                                if defs_key in spec_dict["components"]["schemas"]:
                                    assert spec_dict["components"]["schemas"][defs_key] == return_type_option_json_schema['$defs'][defs_key]
                                spec_dict["components"]["schemas"][defs_key] = return_type_option_json_schema['$defs'][defs_key]
                            del return_type_option_json_schema['$defs']
                        spec_dict["paths"][rule_path][method]["responses"][str(method_info.default_status_code)] = {
                            "description": _generate_description_by_status_code(method_info.default_status_code),
                            "content": {
                                "application/json": {
                                    "schema": return_type_option_json_schema
                                }
                            }
                        }
                    elif typing.get_origin(return_type_option) is ReturnValue:
                        assert len(typing.get_args(return_type_option)) == 1
                        return_type_option = typing.get_args(return_type_option)[0]
                        assert str(method_info.default_status_code) not in spec_dict["paths"][rule_path][method].get("responses", {})
                        return_type_option_json_schema = pydantic.TypeAdapter(return_type_option).json_schema(by_alias=True, ref_template="#/components/schemas/{model}")
                        if '$defs' in return_type_option_json_schema:
                            for defs_key in return_type_option_json_schema['$defs']:
                                if defs_key in spec_dict["components"]["schemas"]:
                                    assert spec_dict["components"]["schemas"][defs_key] == return_type_option_json_schema['$defs'][defs_key]
                                spec_dict["components"]["schemas"][defs_key] = return_type_option_json_schema['$defs'][defs_key]
                            del return_type_option_json_schema['$defs']
                        spec_dict["paths"][rule_path][method]["responses"][str(method_info.default_status_code)] = {
                            "description": _generate_description_by_status_code(method_info.default_status_code),
                            "content": {
                                "application/json": {
                                    "schema": return_type_option_json_schema
                                }
                            }
                        }
                    else:
                        assert False, f"Unhandled return model option {return_type_option} for rule {rule_path} and method {method}"
            if not spec_dict["paths"][rule_path][method]["responses"]:
                del spec_dict["paths"][rule_path][method]["responses"]

    _remove_duplicate_schemas(spec_dict)
    return spec_dict


def _is_schema_entry(path: list[str], value: typing.Any) -> bool:
    return isinstance(value, dict) and value.get('type') == 'object' and 'properties' in value


def _iterate_over_list(spec_list: list[typing.Any], path: list[str]) -> Generator[tuple[list[str], dict[str, typing.Any]]]:
    for index, value in enumerate(spec_list):
        value_path = path + [str(index)]
        if _is_schema_entry(value_path, value):
            yield (value_path, value)
        if isinstance(value, dict):
            yield from _iterate_over_dict(value, value_path)
        elif isinstance(value, list):
            yield from _iterate_over_list(value, value_path)


def _iterate_over_dict(spec_dict: dict[str, typing.Any], path: list[str]) -> Generator[tuple[list[str], dict[str, typing.Any]]]:
    for key, value in spec_dict.items():
        if key in ('examples', 'example'):
            continue
        value_path = path + [key]
        if _is_schema_entry(value_path, value):
            yield (value_path, value)
        if isinstance(value, dict):
            yield from _iterate_over_dict(value, value_path)
        elif isinstance(value, list):
            yield from _iterate_over_list(value, value_path)


def iterate_over_schema_dicts(spec_dict: dict[str, typing.Any]) -> Generator[tuple[list[str], dict[str, typing.Any]]]:
    return _iterate_over_dict(spec_dict, [])


def _remove_duplicate_schemas(spec_dict: dict[str, typing.Any]) -> None:
    schemas_to_replace_with_references = []
    for path, schema in iterate_over_schema_dicts(spec_dict):
        if path[:2] != ['components', 'schemas']:
            component_schema_keys = [key for key, value in spec_dict['components']['schemas'].items() if value == schema]
            if component_schema_keys:
                assert len(component_schema_keys) == 1
                schemas_to_replace_with_references.append((path, component_schema_keys[0]))

    for path, component_schema_key in schemas_to_replace_with_references:
        reference = {
            "$ref": f"#/components/schemas/{component_schema_key}"
        }
        spec_dict_part = spec_dict
        for path_step in path[:-1]:
            spec_dict_part = spec_dict_part[path_step]
        spec_dict_part[path[-1]] = reference


class OpenAPISpecJSON(Resource):
    def get(self) -> ResponseData:
        return flask.Response(json.dumps(generate_openapi_spec(), indent=2), mimetype='application/json')


class OpenAPISpecYAML(Resource):
    def get(self) -> ResponseData:
        return flask.Response(yaml.dump(generate_openapi_spec()), mimetype='application/yaml')
