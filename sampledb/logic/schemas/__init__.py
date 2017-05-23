# coding: utf-8
"""
Logic package for sampledb schemas

The structure of sample and measurement information is defined using schemas,
JSON-like objects similar to JSON schema. Instead of the primitive types used
in JSON schema, sampledb schemas can use the following types:

- bool
- text
- quantity
- datetime
- sample
"""

from .validate_schema import validate_schema
from .generate_placeholder import generate_placeholder
from .validate import validate
