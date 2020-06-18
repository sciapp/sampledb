.. _jupyterhub_support:

JupyterHub Support
==================

JupyterHub is a web application that can provide Jupyter notebook servers to multiple users. This can allow your users to run Jupyter notebooks on one of your systems, giving them access to their data and a software environment configured for your facility. For general information on JupyterHub, see `the JupyterHub documentation <https://jupyterhub.readthedocs.io/>`_

SampleDB can interface with JupyterHub with the help of a notebook templating server. This way metadata stored for a sample or measurement in SampleDB can be inserted into a Jupyter notebook, which can then be run on the JupyterHub, allowing your users to start a data analysis with a few clicks.

If you do not wish to run a JupyterHub instance, you can still run the notebook templating server and configure it so that the generated notebooks can be downloaded by the users. In that case, you can skip the following step.

JupyterHub
----------

You can find information on how to set up JupyterHub in the `Get Started guide <https://jupyterhub.readthedocs.io/en/stable/getting-started/index.html>`_ for JupyterHub. During this setup, you will pick an ``Authenticator`` and a ``Spawner``. Depending on the ``Spawner``, you will also have to configure how persistent storage is handled for the JupyterHub. The rest of this guide assumes that there is some form of persistent storage, which the notebook templating server can write notebooks to.

Notebook Templating Server
--------------------------

Depending on your specific configuration of JupyterHub, you will need to write and set up a notebook templating server. SampleDB will redirect the user to a URL containing the name of the desired template and a selection of metadata, e.g.: ``https://jupyterhub.example.com/templates/t/some_instrument/data_analysis.ipynb?params={%22measurement_name%22:%22Experiment-12345%22}`` In this example:

- ``https://jupyterhub.example.com/templates/`` is the base URL of a notebook templating server,
- ``/t/`` is a separator,
- ``/some_instrument/data_analysis.ipynb`` is the name of the template, and
- the GET parameter ``params`` with the value ``{%22measurement_name%22:%22Experiment-12345%22}`` contains the selected metadata.

The templating server will check if the requested template exists and if so, ask the user for confirmation and will insert the properties in ``params`` into the notebook as a new cell. The resulting notebook is then stored on the persistent storage for your JupyterHub and the user is redirected to it.

If the name of a template contains a parameter name in braces, e.g. ``Data_Analysis_{measurement_name}.ipynb``, then the value of that parameter is inserted into the name when generating the notebook.

For more information and a Flask blueprint for writing a server for your JupyterHub instance, see `the notebook_templates project page <https://github.com/sciapp/notebook_templates>`_.

Notebook Templates
------------------

The notebook templates themselves are simply regular Jupyter notebooks, which expect some variables to be defined in the cell inserted by the templating server. A template might, for example, rely on the path to a data file being passed to it as a parameter and then open that file for analysis.

SampleDB configuration
----------------------

To configure SampleDB to use your JupyterHub and the notebook templating server, you should set the SAMPLEDB_JUPYTERHUB_NAME, SAMPLEDB_JUPYTERHUB_URL and SAMPLEDB_JUPYTERHUB_TEMPLATES_URL :ref:`configuration values <jupyterhub_configuration>`. For actions with a notebook template, SampleDB will then add a button for creating a Jupyter notebook.

Actions
-------

Notebook templates are defined for each action, as they depend on the type of metadata that's available. Notebook templates are added to the schema as the top-level property ``notebookTemplates``, which contains a list of objects.

Each of the objects represents one notebook template, with a ``title``, its relative ``url`` and a its ``params``. Each template parameter in ``params`` is mapped to the path to the actual data in the schema as a list of keys, as shown in the following example:

.. code-block:: javascript

    "notebookTemplates": [
      {
        "title": "Data Analysis",
        "url": "some_instrument/data_analysis.ipynb",
        "params": {
          "measurement_name": [
            "name",
            "text"
          ],
          "created": [
            "created",
            "utc_datetime"
          ]
        }
      }
    ]

Here the template parameter ``measurement_name`` will be filled with the ``text`` of the ``name`` property of an existing object, and the parameter ``created`` will contain the value of the ``created`` property as a string containing the UTC datetime.
