.. _customization:

Customization
=============

SampleDB provides several methods for customizing a specific SampleDB instance.

Configuration
-------------

There are several :ref:`Configuration Variables <customization_configuration>` which can be used to set the name and description of the SampleDB instance and to set instance-specific links (e.g. to a privacy policy or help page).

Custom Stylesheets
------------------

The file ``sampledb/static/css/custom.css`` can be used to define custom CSS rules to change the appearance of SampleDB.

To use this while using a Docker container to run SampleDB, you will need to bind mount the file to the path ``/home/sampledb/sampledb/static/css/custom.css``, .e.g using the ``--volume`` parameter for the ``docker run`` command or using a ``volumes`` section in a ``docker-compose.yml`` file.

Custom Templates
----------------

SampleDB uses `Jinja <https://jinja.palletsprojects.com/en/>`_ templates to render its web frontend. While you can, in theory, overwrite those templates to provide your own, this may lead to issues when upgrading the SampleDB version. However, the following templates are explicitly provided to be overwritten for the purpose of customization:

custom/alerts.html
``````````````````

This template is included right above system alerts which usually report success or failure on user actions, e.g. having signed in or having created an object. By introducing custom HTML, you can add alerts to be shown on all pages, or by checking the ``request.endpoint`` variable in Jinja, you can ensure these alerts are only shown on specific pages.

.. code-block:: html+jinja
    :caption: A custom alerts template for alerts on the sign-in page

    {% if request.endpoint == 'frontend.sign_in' %}
      <div class="alert alert-info">
        <strong>Note:</strong> Contact an <a href="mailto:administrator@example.org">administrator</a> to request an account.
      </div>
    {% endif %}

custom/head.html
````````````````

This template is included in the HTML head section and can be used to include custom stylesheets (in addition to the ``custom.css`` file described above), custom scripts and other elements. Note that SampleDB is configured with a fairly restrictive `Content Security Policy <https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP>`_, which will block inline scripts or stylesheets as well as those from other servers/origins. Place any scripts or stylesheets in the ``sampledb/static/`` folder to make sure they will not be blocked.

.. code-block:: html+jinja
    :caption: A custom head template including a CSS file from the ``sampledb/static`` directory

    <link rel="stylesheet" href="{{ fingerprinted_static('example.css') }}">

custom/scripts.html
```````````````````

This template is included at the end of the HTML body section, right after scripts for SampleDB have been included, so that jQuery and other scripts are already available. This can be used to include custom scripts and other elements. As noted above, you will need to use the ``sampledb/static/`` folder to make sure the scripts will not be blocked.

.. code-block:: html+jinja
    :caption: A custom scripts template including a JavaScript file from the ``sampledb/static`` directory

    <script src="{{ fingerprinted_static('example.js') }}"></script>
