# coding: utf-8
"""

"""

import json
import os

import flask
import jsonschema

from sampledb.logic.datatypes import JSONEncoder
from sampledb.frontend import frontend
from sampledb.rest_api.objects import SCHEMA_DIR

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe.custom.json'), 'r'))
data = json.load(open(os.path.join(os.path.dirname(__file__), '..', '..', 'example_data', 'ombe.json'), 'r'))

jsonschema.Draft4Validator.check_schema(schema)
jsonschema.validate(data, schema)


def to_datatype(obj):
    return json.loads(json.dumps(obj), object_hook=JSONEncoder.object_hook)


@frontend.route('/test')
def render_schema():
    flask.current_app.jinja_env.filters['to_datatype'] = to_datatype
    return flask.render_template('objects/forms/form_base.html', schema=schema, data=data)


@frontend.route('/test/2')
def render_data():
    flask.current_app.jinja_env.filters['to_datatype'] = to_datatype
    return flask.render_template('objects/view/base.html', schema=schema, data=data)

