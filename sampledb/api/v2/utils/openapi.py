import functools
import inspect
import json
import re
import typing
import http
from dataclasses import dataclass

import flask
import pydantic.json_schema
import yaml
from pydantic import BaseModel

from ...utils import Resource, ResponseData, make_json_response
from .validation import validate, ValidatingError
from .responses import make_response, ResultUnion, ReturnValue, RedirectResponseModel, ErrorModel, NoContentModel


@dataclass(frozen=True, kw_only=True, slots=True)
class OpenAPIMethodInformation:
    default_status_code: int
    path_model: typing.Optional[typing.Type[BaseModel]]
    query_model: typing.Optional[typing.Type[BaseModel]]
    request_body_model: typing.Optional[type]
    return_type_hint: typing.Optional[type]


class GenericOperationCallable[R: Resource](typing.Protocol):
    def __call__(self_, self: R, **kwargs: typing.Any) -> ResponseData:
        ...


class BareCallable[R: Resource](typing.Protocol):
    def __call__(self_, self: R) -> ResultUnion:
        ...


class PathCallable[R: Resource, PM: BaseModel](typing.Protocol):
    def __call__(self_, self: R, path: PM) -> ResultUnion:
        ...


class QueryCallable[R: Resource, QM: BaseModel](typing.Protocol):
    def __call__(self_, self: R, query: QM) -> ResultUnion:
        ...


class RequestBodyCallable[R: Resource, ReqM](typing.Protocol):
    def __call__(self_, self: R, request_body: ReqM) -> ResultUnion:
        ...


class PathQueryCallable[R: Resource, PM: BaseModel, QM: BaseModel](typing.Protocol):
    def __call__(self_, self: R, path: PM, query: QM) -> ResultUnion:
        ...


class PathRequestBodyCallable[R: Resource, PM: BaseModel, ReqM](typing.Protocol):
    def __call__(self_, self: R, path: PM, request_body: ReqM) -> ResultUnion:
        ...


class PathQueryRequestBodyCallable[R: Resource, PM: BaseModel, QM: BaseModel, ReqM](typing.Protocol):
    def __call__(self_, self: R, path: PM, query: QM, request_body: ReqM) -> ResultUnion:
        ...


R = typing.TypeVar('R', bound=Resource)
PM = typing.TypeVar('PM', bound=BaseModel)
QM = typing.TypeVar('QM', bound=BaseModel)
ReqM = typing.TypeVar('ReqM')  # , bound=BaseModel)


def method(
        *,
        default_status_code: int = 200,
        request_body_context_builder: typing.Optional[typing.Callable[[PM], typing.Any]] = None
) -> typing.Callable[
    [
        typing.Union[
            BareCallable[R],
            PathCallable[R, PM],
            QueryCallable[R, QM],
            RequestBodyCallable[R, ReqM],
            PathQueryCallable[R, PM, QM],
            PathRequestBodyCallable[R, PM, ReqM],
            PathQueryRequestBodyCallable[R, PM, QM, ReqM],
        ]
    ],
    GenericOperationCallable[R]
]:
    def method_decorator_impl(
            func: typing.Union[
                BareCallable[R],
                PathCallable[R, PM],
                QueryCallable[R, QM],
                RequestBodyCallable[R, ReqM],
                PathQueryCallable[R, PM, QM],
                PathRequestBodyCallable[R, PM, ReqM],
                PathQueryRequestBodyCallable[R, PM, QM, ReqM],
            ]
    ) -> GenericOperationCallable[R]:
        type_hints = typing.get_type_hints(func)
        path_model: typing.Optional[typing.Type[PM]] = type_hints.get('path')
        assert path_model is None or issubclass(path_model, BaseModel)
        query_model: typing.Optional[typing.Type[QM]] = type_hints.get('query')
        assert query_model is None or issubclass(query_model, BaseModel)
        request_body_model: typing.Optional[typing.Type[ReqM]] = type_hints.get('request_body')
        if isinstance(request_body_model, typing.TypeAliasType):
            request_body_model = request_body_model.__value__
        # no assert for request_body_model to be BaseModel or None, as various other inputs currently exist, e.g. for permissions
        return_type_hint: typing.Optional[type] = type_hints.get('return')
        assert return_type_hint is not None

        class KWArgsDict(typing.TypedDict, total=False):
            path: PM
            query: QM
            request_body: ReqM

        @functools.wraps(func)
        def method_impl(self: R, **kwargs: typing.Any) -> ResponseData:
            new_kwargs: KWArgsDict = {}
            try:
                if path_model is not None:
                    new_kwargs['path'] = validate(
                        path_model,
                        kwargs
                    )
                if query_model is not None:
                    new_kwargs['query'] = validate(
                        query_model,
                        {
                            key: values[0] if len(values) == 1 else values
                            for key, values in flask.request.args.lists()
                        }
                    )
                if request_body_model is not None:
                    new_kwargs['request_body'] = validate(
                        request_body_model,
                        flask.request.get_json(force=True) if flask.request.content_length else None,
                        context=request_body_context_builder(new_kwargs['path']) if request_body_context_builder is not None else None
                    )
            except ValidatingError as e:
                # TODO: refactor special error handling for ObjectFiles
                msg, _, loc = e.message.rpartition(" (")
                if not msg:
                    return make_json_response(
                        e.response[0],
                        status=e.response[1]
                    )
                assert loc.endswith(")")
                loc = loc[:-1]
                for prefix in "database.without_preview_image.", "database.with_preview_image.", "local_reference.", "url.":
                    if loc.startswith(prefix):
                        e.message = f"{msg} ({loc.removeprefix(prefix)})"
                        break
                return make_json_response(
                    e.response[0],
                    status=e.response[1]
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
            return_type_hint=return_type_hint
        )
        return method_impl
    return method_decorator_impl


def _generate_description_by_status_code(
        status_code: int
) -> str:
    status = http.HTTPStatus(status_code)
    return f"{status.phrase}: {status.description.replace('--', '—')}"


@functools.cache
def generate_openapi_spec() -> typing.Dict[str, typing.Any]:
    spec_dict: typing.Dict[str, typing.Any] = {
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
            "responses": {},
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
        rule_path = re.sub(r'<[^:>]+:([^>]+)>', r'{\1}', rule_path)
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
                if typing.get_origin(request_body_model) is typing.Union and len(typing.get_args(request_body_model)) == 2 and type(None) in typing.get_args(request_body_model):
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
                if typing.get_origin(return_type_hint) is typing.Union:
                    return_type_options = list(typing.get_args(return_type_hint))
                else:
                    return_type_options = [return_type_hint]
                for return_type_option in return_type_options:
                    if inspect.isclass(return_type_option) and issubclass(return_type_option, ErrorModel):
                        assert str(return_type_option.STATUS_CODE) not in spec_dict["paths"][rule_path][method]["responses"]
                        return_type_option_json_schema = return_type_option.model_json_schema(by_alias=True, ref_template="#/components/schemas/{model}")
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
                        response_title = return_type_option_json_schema['title'].removeprefix('Model')
                        response = {
                            "description": _generate_description_by_status_code(return_type_option.STATUS_CODE),
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": f"#/components/schemas/{return_type_option_json_schema['title']}"
                                    }
                                }
                            }
                        }
                        if response_title in spec_dict["components"]["responses"]:
                            assert spec_dict["components"]["responses"][response_title] == response, str((response, spec_dict["components"]["responses"][response_title]))
                        spec_dict["components"]["responses"][response_title] = response
                        spec_dict["paths"][rule_path][method]["responses"][str(return_type_option.STATUS_CODE)] = {
                            "$ref": f"#/components/responses/{response_title}"
                        }
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

    return spec_dict


class OpenAPISpecJSON(Resource):
    def get(self) -> ResponseData:
        return flask.Response(json.dumps(generate_openapi_spec(), indent=2), mimetype='application/json')


class OpenAPISpecYAML(Resource):
    def get(self) -> ResponseData:
        return flask.Response(yaml.dump(generate_openapi_spec()), mimetype='application/yaml')
