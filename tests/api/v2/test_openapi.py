import copy
import os.path

import flask
import pytest
import requests
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
                if ':' in rule_path_parameter:
                    rule_path_parameter_name = rule_path_parameter.split(':', 1)[1]
                else:
                    rule_path_parameter_name = rule_path_parameter
                rule_path = rule_path_left + '{' + rule_path_parameter_name + '}' + rule_path_right
            assert rule_path in spec_dict['paths']
            path_spec = spec_dict['paths'][rule_path]
            assert {method.lower() for method in rule.methods} - {'options', 'head'} == set(path_spec)




def test_descriptions_and_examples(spec_dict):
    for path, schema in sampledb.api.v2.utils.openapi.iterate_over_schema_dicts(spec_dict):
        for property_name, property_schema in schema['properties'].items():
            assert 'description' in property_schema, f'missing description for {property_name} in schema {schema} at {path}'
            assert 'examples' in property_schema and len(property_schema['examples']) == 1, f'missing description for {property_name} in schema {schema} at {path}'


def test_no_duplicate_components(spec_dict):
    component_schemas = list(spec_dict['components']['schemas'].values())
    for path, schema in sampledb.api.v2.utils.openapi.iterate_over_schema_dicts(spec_dict):
        if path[:2] != ['components', 'schemas']:
            assert schema not in component_schemas, f"schema at {path} also found as component schema {[key for key, value in spec_dict['components']['schemas'].items() if value == schema][0]}"


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


def test_error_for_params_without_model(flask_server):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.logic.authentication.add_other_authentication(user.id, 'username', 'password')
    auth = ('username', 'password')

    r = requests.get(flask_server.base_url + 'api/v2/users/', auth=auth)
    assert r.status_code == 200

    r = requests.get(flask_server.base_url + 'api/v2/users/', auth=auth, json={'key': 'value'})
    assert r.status_code == 400
    assert r.json() == {
        "detail": "A request body is not permitted",
        "errors": [],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    r = requests.get(flask_server.base_url + f'api/v2/users/{user.id}', auth=auth, params={'limit': 5})
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Extra inputs are not permitted (limit)",
        "errors": [{
            "detail": "Extra inputs are not permitted",
            "query_parameter": "limit",
            "input": ["5"]
        }],
        "status": 400,
        "title": "Failed to validate URL query parameters.",
        "type": "http://localhost/api/v2/errors/QueryValidationFailed",
    }
