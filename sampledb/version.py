# coding: utf-8
"""
This file should only contain the definition of the __version__ variable.

It may be read by multiple other files, e.g. setup.py and the status page.

The SAMPLEDB_VERSION environment variable can be used to override the static
value. This is done when building the Docker image as part of the GitLab CI
pipeline to provide the current version as returned by git describe.
"""

import os

__version__ = os.environ.get('SAMPLEDB_VERSION') or '0.31.0'
