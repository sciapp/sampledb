# coding: utf-8

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Project information

project = 'iffSamples'
copyright = '2018, PGI / JCNS Scientific IT-Systems'
author = 'Florian Rhiem'

# The short X.Y version
version = ''

# The full version, including alpha/beta/rc tags
release = '0.1.0'

# General configuration

source_suffix = '.rst'

master_doc = 'index'

exclude_patterns = []

language = None

templates_path = ['templates']

pygments_style = None

extensions = [
    'sphinx.ext.autodoc',
    'sphinxcontrib.httpdomain',
]

# Options for HTML output

html_theme = 'alabaster'
html_static_path = ['static']

# Options for other output methods

htmlhelp_basename = 'iffSamplesdoc'

latex_elements = {}
latex_documents = [
    (master_doc, 'iffSamples.tex', 'iffSamples Documentation',
     'Florian Rhiem', 'manual'),
]

man_pages = [
    (master_doc, 'iffsamples', 'iffSamples Documentation',
     [author], 1)
]

texinfo_documents = [
    (master_doc, 'iffSamples', 'iffSamples Documentation',
     author, 'iffSamples', 'Sample and measurement medadata database',
     'Miscellaneous'),
]

epub_title = project
epub_exclude_files = ['search.html']


def setup(app):
    app.add_stylesheet('css/custom.css')
