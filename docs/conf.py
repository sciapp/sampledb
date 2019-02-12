# coding: utf-8

import os
import sys
import vcversioner
import datetime

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_dir)

# Project information

service_name = 'iffSamples'
service_description = 'iffSamples is the sample and measurement metadata database at PGI and JCNS.'
service_url = 'https://iffsamples.fz-juelich.de'
service_imprint = 'https://pgi-jcns.fz-juelich.de/portal/pages/imprint.html'
contact_email = 'f.rhiem@fz-juelich.de'

project = service_name
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
        service_name: service_url,
        'PGI/JCNS-TA': 'https://pgi-jcns.fz-juelich.de',
        'Contact': 'mailto:{}'.format(contact_email),
        'Imprint': service_imprint,
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
    app.add_stylesheet('css/custom.css')


rst_prolog = """
.. |service_url| replace:: {service_url}
.. |service_description| replace:: {service_description}
.. |service_name| replace:: {service_name}
.. |service_invitation_url| replace:: {service_url}/users/invitation
.. |service_actions_url| replace:: {service_url}/actions
.. |service_instruments_url| replace:: {service_url}/instruments

.. _let us know: mailto:{contact_email}

""".format(
    service_name=service_name,
    service_description=service_description,
    service_url=service_url,
    contact_email=contact_email
)
