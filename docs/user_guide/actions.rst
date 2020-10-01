.. _actions:

Actions
=======

Processes like **creating a sample**, **performing a measurement** or **running a simulation** are represented as actions in |service_name| and whenever such an action is performed a new :ref:`Object <objects>` should be created in |service_name|.

Either generic or associated with an :ref:`Instrument <instruments>`, each action contains a name, a description and a :ref:`Schema <metadata>`.

You can view a list of actions at |service_actions_url|. Similar to instruments, users can select **favorites** by clicking the star next to an action's name.

Action Types
------------

The type of an Action describes the general kind of process it represents, such as **Sample Creation**. There are three built-in action types for creating samples, performing a measurement or running a simulation, but administrators can create custom action types.

Custom Actions
--------------

Users can create custom actions to represent their own processes or instruments that are not yet part of |service_name|. These actions can either be private, only usable by the users who created them, or public, usable by anyone.

To create a custom action, users can either use an existing action as a template or write a :ref:`Schema <metadata>` from scratch.

.. note::
    Custom Actions are an advanced feature that most users of |service_name| will not need. If you would like your instrument or action to be included without writing your own schema, please `let us know`_.

    .. only:: iffSamples

        If you would like to try working with custom actions, please `use the development and testing deployment of iffSamples <https://docker.iff.kfa-juelich.de/dev-sampledb/>`_.

.. _metadata:

Metadata and Schemas
--------------------

A schema specifies what metadata should be recorded when performing an action. The metadata should contain all the information required to reproduce what a user did.

To edit simple schemas, users can use the graphical schema editor. To access more advanced features like arrays, users can instead edit the schema directly in a text-based editor by setting the *Use Schema Editor* setting to *No* in their preferences.

.. figure:: ../static/img/generated/schema_editor.png
    :scale: 50 %
    :alt: Editing an action using the schema editor

    Editing an action using the schema editor

Schemas are defined using `JSON <https://www.json.org/>`_. Each schema must at least include a text property called ``name``.

.. code-block:: json
    :caption: A basic schema containing a sample name, creation datetime, tags and a description

    {
      "title": "Basic Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text",
          "minLength": 1,
          "maxLength": 100
        },
        "created": {
          "title": "Creation Datetime",
          "type": "datetime"
        },
        "tags": {
          "title": "Tags",
          "type": "tags"
        },
        "description": {
          "title": "Description",
          "type": "text",
          "minLength": 0,
          "multiline": true
        }
      },
      "propertyOrder": ["name", "created", "tags", "description"],
      "required": ["name", "created"]
    }

Data types
``````````

Currently, the following basic data types are supported for metadata:

- Texts
- Booleans
- Quantities
- Datetimes

These can be used to form the following composite data types:

- Arrays
- Objects

Additionally, there are special data types:

- :ref:`Tags <tags>`
- :ref:`Hazards <hazards>`
- User References
- Object References
    - Sample References
    - Measurement References

All metadata property definitions require a ``title`` and a ``type`` property. They can also contain a ``note`` property with information for users. Some data types allow or require additional properties.

Objects
^^^^^^^

Objects represent complex composite data types containing named properties. They may have a default value (``default``), a list of required properties (``required``) and a list containing the order of properties (``propertyOrder``). Additionally, they require a schema for each of their properties (``properties``).

.. code-block:: json
    :caption: An object property containing a name as a text property and a creation date as a datetime property with a property order and a required property

    {
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        },
        "created": {
          "title": "Creation Datetime",
          "type": "datetime"
        },
      },
      "propertyOrder": ["name", "created"],
      "required": ["name"]
    }

Arrays
^^^^^^

Arrays represent a list of items. Arrays may have a minium (``minItems``) and maximum number of items (``maxItems``) and a default value (``default``). Additionally, they require a schema for their items (``items``).

.. code-block:: json
    :caption: An array property containing texts with a default and length restrictions

    {
      "title": "Notes",
      "type": "array",
      "items": {
        "title": "Note",
        "type": "text"
      },
      "minItems": 1,
      "maxItems": 10,
      "default": [
        {
          "_type": "text",
          "text": "First default note"
        },
        {
          "_type": "text",
          "text": "Second default note"
        }
      ]
    }

Texts
^^^^^

Texts may have a minimum (``minLength``) and maximum length (``maxLength``) and a default value (``default``). Acceptable values can be restricted using a `regular expression <https://docs.python.org/3/library/re.html#regular-expression-syntax>`_ (``pattern``) and text properties can optionally contain multiple lines (``multiline``).

.. code-block:: json
    :caption: A sample name as a text property with a default, a pattern and length restrictions

    {
      "title": "Sample Name",
      "type": "text",
      "minLength": 1,
      "maxLength": 100,
      "default": "Sample-",
      "pattern": "^.+$"
    }

.. code-block:: json
    :caption: A sample description allowing multiple lines of text

    {
      "title": "Description",
      "type": "text",
      "multiline": true
    }

Booleans
^^^^^^^^

Booleans may have a default value (``default``), either ``true`` or ``false``.

.. code-block:: json
    :caption: A boolean property with a default

    {
      "title": "Lid Open?",
      "type": "bool",
      "default": true
    }

Quantities
^^^^^^^^^^

Quantities require units (``units``, can be ``1``) and may have a default value (``default``) given in the base units of the quantities' dimensions.

.. code-block:: json
    :caption: A temperature property with a default of 25°C (298.15K)

    {
      "title": "Temperature",
      "type": "quantity",
      "units": "degC",
      "default": 298.15
    }

Datetimes
^^^^^^^^^

Datetime may have a default value (``default``). Datetimes in |service_name| are written using notation ``YYYY-MM-DD hh:mm:ss`` and stored using UTC.

.. code-block:: json
    :caption: A datetime property with a default

    {
      "title": "Creation Datetime",
      "type": "datetime",
      "default": "2018-12-05 15:38:12"
    }

Tags
^^^^

Tags may have a default value (``default``). There can be only one tags property, called ``tags`` as a property of the root object.

.. code-block:: json
    :caption: A tags property with a default

    {
      "title": "Tags",
      "type": "tags",
      "default": ["tag1", "tag2"]
    }

Hazards
^^^^^^^

Hazards do not allow additional properties. There can be only one hazards property, called ``hazards`` as a property of the root object. If it exists, it must be required.

.. code-block:: json
    :caption: A hazards property

    {
      "title": "GHS hazards",
      "type": "hazards"
    }

Sample References
^^^^^^^^^^^^^^^^^

Sample references do not allow additional properties.

.. code-block:: json
    :caption: A sample reference property

    {
      "title": "Previous Sample",
      "type": "sample"
    }

Measurement References
^^^^^^^^^^^^^^^^^^^^^^

Measurement references do not allow additional properties.

.. code-block:: json
    :caption: A measurement reference property

    {
      "title": "Preparatory Measurement",
      "type": "measurement"
    }

User References
^^^^^^^^^^^^^^^

User references do not allow additional properties.

.. code-block:: json
    :caption: A measurement reference property

    {
      "title": "Client",
      "type": "user"
    }

Notebook Templates
``````````````````

Schemas may contain a list of references to notebook templates as a property of the root object called ``notebookTemplates``. Each reference in this list must contain a title, a URL and an object describing the parameters of the template.

.. code-block:: json
    :caption: A list of notebook template references

    [
      {
        "title": "Demo Notebook 1",
        "url": "demo.ipynb",
        "params": {}
      },
      {
        "title": "Demo Notebook 2",
        "url": "iffSamples/sample-#{sample_id}.ipynb",
        "params": {
          "sample_id": "object_id",
          "name": ["name", "text"],
        }
      }
    ]

.. note::

    The notebook template functionality is based on an additional webservice. Only users with access to a JupyterHub instance with this webservice and persistent storage there will be able to use it.

    If no JupyterHub URL is :ref:`configured <jupyterhub_support>`, this list will be ignored.
