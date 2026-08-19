import copy
import os.path

import pytest
import yaml
from openapi_spec_validator import validate

import sampledb.api.v2.utils.openapi


@pytest.fixture
def spec_dict(flask_server):
    # set known server name to allow repeatable URL generation
    flask_server.app.config['SERVER_NAME'] = 'localhost'
    with flask_server.app.test_request_context():
        return sampledb.api.v2.utils.openapi.generate_openapi_spec()


def test_valid_spec(spec_dict):
    validate(spec_dict)


def test_openapi_spec_all_paths(flask_server, spec_dict):
    for rule in flask_server.app.url_map.iter_rules():
        if rule.endpoint.startswith('api_v2.') and rule.endpoint not in ('api_v2.errors', 'api_v2.openapi_json', 'api_v2.openapi_yaml'):
            assert rule.rule.startswith('/api/v2')
            rule_path = rule.rule[len('/api/v2'):]
            while '<' in rule_path:
                rule_path_left, rule_path_right = rule_path.split('<', 1)
                rule_path_parameter, rule_path_right = rule_path_right.split('>', 1)
                rule_path_parameter_name = rule_path_parameter.split(':', 1)[1]
                rule_path = rule_path_left + '{' + rule_path_parameter_name + '}' + rule_path_right
            assert rule_path in spec_dict['paths']
            path_spec = spec_dict['paths'][rule_path]
            assert {method.lower() for method in rule.methods} - {'options', 'head'} == set(path_spec)


def test_descriptions_and_examples(spec_dict):
    def is_schema_entry(path, value):
        return isinstance(value, dict) and value.get('type') == 'object' and 'properties' in value
    def iterate_over_list(spec_list, path):
        for index, value in enumerate(spec_list):
            value_path = path + [str(index)]
            if is_schema_entry(value_path, value):
                yield (value_path, value)
            if isinstance(value, dict):
                yield from iterate_over_dict(value, value_path)
            elif isinstance(value, list):
                yield from iterate_over_list(value, value_path)
    def iterate_over_dict(spec_dict, path):
        for key, value in spec_dict.items():
            if key in ('examples', 'example'):
                continue
            value_path = path + [key]
            if is_schema_entry(value_path, value):
                yield (value_path, value)
            if isinstance(value, dict):
                yield from iterate_over_dict(value, value_path)
            elif isinstance(value, list):
                yield from iterate_over_list(value, value_path)
    for path, schema in iterate_over_dict(spec_dict, []):
        for property_name, property_schema in schema['properties'].items():
            assert 'description' in property_schema, f'missing description for {property_name} in schema {schema} at {path}'
            assert 'examples' in property_schema and len(property_schema['examples']) == 1, f'missing description for {property_name} in schema {schema} at {path}'


def test_openapi_spec_in_docs(spec_dict):
    server_independent_spec_dict = copy.deepcopy(spec_dict)
    del server_independent_spec_dict["servers"]
    del server_independent_spec_dict["security"]
    del server_independent_spec_dict["components"]["securitySchemes"]
    docs_yaml_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',  '..', 'docs', 'static',  'api_v2_openapi.yaml')
    current_yaml_file_content = open(docs_yaml_file_path, 'r').read()
    generated_yaml_file_content = yaml.dump(server_independent_spec_dict)
    with open(docs_yaml_file_path, 'w') as f:
        f.write(generated_yaml_file_content)
    assert current_yaml_file_content == generated_yaml_file_content
