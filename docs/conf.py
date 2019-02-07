# coding: utf-8

import os
import sys
import vcversioner
import datetime

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_dir)

# Project information

project = 'iffSamples'
copyright = '{}, PGI / JCNS Scientific IT-Systems'.format(datetime.date.today().year)
author = 'Florian Rhiem'

# The full version, including alpha/beta/rc tags
release = vcversioner.find_version(root=base_dir).version

# The short X.Y version
version = '.'.join(release.split('.', 2)[:2])

# General configuration

source_suffix = '.rst'

master_doc = 'index'

exclude_patterns = []

language = None

templates_path = ['templates']

pygments_style = None

extensions = [
    'sphinx.ext.todo',
    'sphinx.ext.autodoc',
    'sphinxcontrib.httpdomain',
]

todo_include_todos = False

# Options for HTML output

html_theme = 'alabaster'
html_static_path = ['static']
html_show_sourcelink = False

# Options for Alabaster theme
html_theme_options = {
    'description': "Sample and Measurement Metadata Database",
    'font_family': "'Lato', 'Helvetica Neue', 'Arial', sans-serif",
    'font_size': '16px',
    'head_font_family': "'Lato', 'Helvetica Neue', 'Arial', sans-serif",
    'body_text_align': 'justify',
    'show_powered_by': False,
    'extra_nav_links': {
        'iffSamples': 'https://iffsamples.fz-juelich.de',
        'PGI/JCNS-TA': 'https://pgi-jcns.fz-juelich.de',
        'Contact': 'mailto:f.rhiem@fz-juelich.de',
        'Imprint': 'https://pgi-jcns.fz-juelich.de/portal/pages/imprint.html',
    }
}

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
