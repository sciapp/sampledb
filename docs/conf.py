# coding: utf-8

import os
import sys
import vcversioner
import datetime

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_dir)

# Project information

service_name = 'SampleDB'
service_url = 'https://iffsamples.fz-juelich.de'
service_legal_notice = 'https://pgi-jcns.fz-juelich.de/portal/pages/imprint.html'
contact_email = 'f.rhiem@fz-juelich.de'

project = service_name
copyright = '{}, PGI / JCNS Scientific IT-Systems'.format(datetime.date.today().year)
author = 'Florian Rhiem'

# The full version, including alpha/beta/rc tags
release = vcversioner.find_version(root=base_dir).version

# The short X.Y version
version = '.'.join(release.split('.', 2)[:2])

# General configuration

source_suffix = {'.rst': 'restructuredtext'}

master_doc = 'index'

exclude_patterns = []

language = 'en'

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
    'logo': 'img/logo64.png',
    'logo_name': True,
    'logo_text_align': 'center',
    'description': "Sample and Measurement Metadata Database",
    'font_family': "'Lato', 'Helvetica Neue', 'Arial', sans-serif",
    'font_size': '16px',
    'head_font_family': "'Lato', 'Helvetica Neue', 'Arial', sans-serif",
    'body_text_align': 'justify',
    'show_powered_by': False,
    'extra_nav_links': {
        'Source Code': 'https://github.com/sciapp/sampledb',
        'Issues': 'https://github.com/sciapp/sampledb/issues',
        'Contact': 'mailto:{}'.format(contact_email),
        'Legal Notice': service_legal_notice,
        'PGI/JCNS-TA': 'https://pgi-jcns.fz-juelich.de',
    }
}

# Options for other output methods

htmlhelp_basename = '{}doc'.format(service_name)

latex_elements = {}
latex_documents = [
    (master_doc, '{}.tex'.format(service_name), '{} Documentation'.format(service_name),
     author, 'manual'),
]

man_pages = [
    (master_doc, service_name.lower(), '{} Documentation'.format(service_name),
     [author], 1)
]

texinfo_documents = [
    (master_doc, service_name, '{} Documentation'.format(service_name),
     author, service_name, 'Sample and measurement metadata database',
     'Miscellaneous'),
]

epub_title = project
epub_exclude_files = ['search.html']


def setup(app):
    app.add_css_file('css/custom.css')


rst_prolog = """
.. |service_url| replace:: {service_url}
.. |service_name| replace:: {service_name}
.. |service_invitation_url| replace:: {service_url}/users/invitation
.. |service_actions_url| replace:: {service_url}/actions
.. |service_instruments_url| replace:: {service_url}/instruments

.. _let us know: https://github.com/sciapp/sampledb/issues/new

""".format(
    service_name=service_name,
    service_url=service_url,
    contact_email=contact_email
)
