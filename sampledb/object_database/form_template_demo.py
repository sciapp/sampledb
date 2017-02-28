# coding: utf-8
"""

"""

import flask
import json
import jsonschema
import os

from .views import object_api, SCHEMA_DIR

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


schema = json.load(open(os.path.join(SCHEMA_DIR, 'ombe.custom.json'), 'r'))

jsonschema.Draft4Validator.check_schema(schema)


@object_api.route('/test')
def render_schema():
    return flask.render_template('form_base.html', schema=schema)