.. _metadata:

Metadata and Schemas
====================

A schema specifies what metadata should be recorded when performing an action. The metadata should contain all the information required to reproduce what a user did.

Simple schemas can be created and edited using the graphical schema editor:

.. figure:: ../static/img/generated/schema_editor.png
    :alt: Editing an action using the schema editor

    Editing an action using the schema editor

To access more advanced features like arrays and conditions, users can instead edit the schema directly in a text-based editor by setting the *Use Schema Editor* setting to *No* in their preferences.

.. figure:: ../static/img/generated/disable_schema_editor.png
    :alt: Disabling the graphical schema editor

    Disabling the graphical schema editor

Schemas are defined using `JSON <https://www.json.org/>`_. They consist of nested JSON objects, with each object having a ``title`` and a ``type`` attribute, and more attributes depending on the ``type`` (note: when discussing JSON, what is called an "attribute" here is usually called a "property", this would be ambiguous however, as the metadata fields of an object are also called properties in SampleDB). The root object of each schema must have the ``object`` type and contain at least a text attribute called ``name``, as shown here:

.. code-block:: json
    :caption: A minimal schema containing only the object name

    {
      "type": "object",
      "title": "Object Information",
      "properties": {
        "name": {
          "title": "Name",
          "type": "text"
        }
      },
      "propertyOrder": ["name"],
      "required": ["name"]
    }

Data types
----------

Currently, the following basic data types are supported for metadata:

- :ref:`Texts <metadata_texts>`
- :ref:`Booleans <metadata_booleans>`
- :ref:`Quantities <metadata_quantities>`
- :ref:`Datetimes <metadata_datetimes>`
- :ref:`Time Series <metadata_timeseries>`

These can be used to form the following composite data types:

- :ref:`Arrays <metadata_arrays>`
- :ref:`Objects <metadata_objects>`

Additionally, there are special data types:

- :ref:`Tags <metadata_tags>`
- :ref:`Hazards <metadata_hazards>`
- :ref:`plotly Charts <metadata_plotly_charts>`
- :ref:`User References <metadata_user_references>`
- :ref:`Object References <metadata_object_references>`
    - Sample References
    - Measurement References
    - Generic Object References
- :ref:`Files <metadata_files>`
- :ref:`Schema Templates <metadata_schema_templates>`

In the following, each data type and the attributes in a schema of each type are listed.

.. _metadata_objects:

Objects
```````

Objects represent complex composite data types containing named properties. All SampleDB schemas start with an object (the root object), which consists of various other properties, mapping the name of each property to its subschema. In the minimal example above, the root object contains only a name, but you can add many more properties, as long as they all have a unique name.

.. code-block:: json
    :caption: A minimal schema containing only the object name

    {
      "type": "object",
      "title": "Example Object Information",
      "properties": {
        "name": {
          "title": "Name",
          "type": "text"
        }
        "created": {
          "title": "Creation Datetime",
          "type": "datetime"
        }
      },
      "propertyOrder": ["name", "created"],
      "required": ["name"]
    }

Object instances are JSON objects mapping the property names to the property data.

.. code-block:: json
    :caption: An object instance for the schema above.

    {
      "name": {
        "_type": "text",
        "text": "Demo Object"
      }
      "created": {
        "_type": "datetime",
        "utc_datetime": "2021-07-22 01:23:45"
      }
    }


type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``object``.

title
^^^^^

The title for the object as a JSON string or object, e.g. ``"Sample Information"`` or ``{"en": "Simulation Parameters"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given object property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

properties
^^^^^^^^^^

This JSON object maps names to the subschemas for other properties. The names may consist of latin characters (a-z and A-Z), digits (0-9) and underscores, but must begin with a character and must not end with an underscore. These names are, for example, used for the advanced search.

.. code-block:: json
    :caption: The properties attribute from the example above.

    "properties": {
      "name": {
        "title": "Name",
        "type": "text"
      }
      "created": {
        "title": "Creation Datetime",
        "type": "datetime"
      }
    }

.. note:: As mentioned above, the root object must have a required property called ``name`` with the type ``"text"``. This is the object name used on SampleDB to represent the object. Even though it is not process-specific, it might have process-specific restrictions, which is why it needs to be included in the schema.

.. note:: Try to use consistent property names between schemas, as this can greatly simplify searches, automated data entry or data analysis.

propertyOrder
^^^^^^^^^^^^^

As the ``properties`` JSON objects does not necessarily preserve the order of properties when processed by SampleDB, this attribute can set the desired order of properties when creating or displaying objects created with this schema. It is optional, though recommended to ensure consistent behavior. The property names are given as JSON strings in a JSON array, e.g. ``["name", "created"]``.

required
^^^^^^^^

This JSON array lists the names of all properties which must be set for an object to be valid, e.g. ``["name"]`` if only the ``name`` property must be set.

.. note:: For the root object, the ``name`` property must be required. If a ``hazards`` property exists in the root object, it must also be required.

.. note:: Sometimes, the behavior of required properties of type ``text`` may appear confusing, as even an empty text (``""``) is technically a text. If you want a text property to be non-empty, you can set a ``minLength`` for it in addition to setting it as required. See the text data type below for more information.

default
^^^^^^^

An object instance may be provided as the ``default`` attribute, e.g. for creating a new object. This should be a JSON object mapping each property name to its default data. The default must be a valid instance of the object schema, so the properties in it must fulfill all restrictions from their individual subschemas.

.. code-block:: json
    :caption: A default attribute for the example above.

    "default": {
      "name": {
        "_type": "text",
        "text": "Demo Object"
      }
      "created": {
        "_type": "datetime",
        "utc_datetime": "2021-07-22 01:23:45"
      }
    }

displayProperties
^^^^^^^^^^^^^^^^^

This attribute can be set to a JSON array containing the names of properties that should be displayed in a list of objects for the action this schema belongs to.

.. note:: This attribute may only be set for the root object.

.. note:: For some data types, it may be impossible to display them in the table, e.g. due to size restrictions. If you encounter issues with a property that should be possible to display but isn't shown correctly, you can `report it on GitHub <https://github.com/sciapp/sampledb/issues/new>`_.


batch
^^^^^

This attribute is a boolean that sets whether or not the action for this root object should create a batch of objects. If set to ``true``, the user will be able to enter how many objects should be created during object creation, and that number of objects will be created with identical data except for the name. By default, it is set to ``false``.

.. note:: This attribute may only be set for the root object.

batch_name_format
^^^^^^^^^^^^^^^^^

If the ``batch`` attribute is set to ``true``, this string attribute sets the format for the suffix that will be attached to the name of the objects created as a batch. It must follow the Python string format syntax and will be provided with the index of the individual object in that batch (starting with 1). If no ``batch_name_format`` is provided, the index will be used by itself. If the user set the name as ``Demo`` and were to create three items in a batch, then the default would result in the names ``Demo1``, ``Demo2`` and ``Demo3``, while a ``batch_name_format`` set to ``"-{:03d}"`` would result in the names ``Demo-001``, ``Demo-002`` and ``Demo-003``.

.. note:: This attribute may only be set for the root object.

notebookTemplates
^^^^^^^^^^^^^^^^^

A JSON array containing information about Jupyter notebook templates. For more information, see :ref:`jupyterhub_support`.

.. note:: This attribute may only be set for the root object.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.

style
^^^^^

This attribute is a string or dict mapping ``"form"``, ``"view"`` and ``"inline_edit"`` to strings or null, indicating how the object should be displayed. A string will be used for both editing and viewing object data, while a dict can specify the style depending on whether the user is editing the data or viewing the data, with or without inline editing enabled. By default, the object properties will be listed vertically. The ``horizontal`` style can be used on objects with very few properties to list them horizontally, side-by-side, as long as sufficient space is available. A regular object, outside of a list or table array, can also have the ``collapsible`` or ``expandable`` styles, which allow the object to be collapsed and expanded by the user, hiding all information other than the title. An ``expandable`` object will start as collapsed but can be expanded, while a ``collapsible`` object will start as expanded and can be collapsed.

.. note:: Using a style other than the default may lead to issues when entering or viewing object data. Please test the action and how its objects are displayed. If you encounter issues with a style, you can `report it on GitHub <https://github.com/sciapp/sampledb/issues/new>`_.

show_more
^^^^^^^^^

This attribute is a string array describing which properties to hide in the object view until a "show more"-button is pressed.

workflow_views
^^^^^^^^^^^^^^

This attribute can be used to enable and define one or more workflow views. Workflow views display contents of related objects referencing or referenced by this object
on the object page.

By default, all directly related objects will be displayed, however you can filter the objects by action or action type. By setting ``referencing_action_id`` or ``referenced_action_id`` to a single ID or a list of IDs, you can limit the referencing or referenced objects to specific actions IDs. By setting ``referencing_action_type_id`` or ``referenced_action_type_id`` you can do the same by action type. ``referencing_filter_operator`` and ``referenced_filter_operator`` can each be set to ``"and"`` or ``"or"`` to control whether both action ID and action type ID filters needs to be fulfilled. If both filters are set and ``filter_operator`` is set to ``"and"`` (the default), both action and action type will have to match for an object to be included in the workflow view. If ``filter_operator`` is instead set to ``"or"`` only one of those filters will have to match.

The workflow view also allows setting a custom ``title`` for the object page section section, e.g. ``{"en": "Processing"}`` or ``"Measurements"``.
By setting ``show_action_ínfo`` to ``false`` you can disable displaying action information, which is enabled by default.

Use the ``show_more`` or ``workflow_show_more`` attributes in the linked objects' schemas to limit what object data will be shown as a preview.

The ``sorting_properties`` can be set to a list of property names which will be used for sorting the objects, starting with the first datetime property from the list found for an object and falling back to the object creation datetime for objects which contain none of the listed datetime properties.

.. code-block:: json
    :caption: A workflow view definition including samples (``-99``) and measurements (``-98``) referencing the object as well as referenced objects created using the action with ID ``1``

    "workflow_views": [
        {
            "referencing_action_type_id": [-98, -99],
            "referenced_action_id": 1,
            "title": {"en": "Processing", "de": "Bearbeitung"}
        }
    ]

.. figure:: ../static/img/generated/workflow.png
    :alt: A workflow view, containing previews of related measurements

    A workflow view, containing previews of related measurements

Recursive workflows can be defined by defining filters in the ``recursion_filters`` dictionary.
These workflows also include objects referenced by or referencing other objects in the workflow based on the base workflow configuration.
To set up a recursive view  ``recursion_filters`` dictionary, recursive workflows can be configured.
If ``referenced_action_id`` and/or ``referenced_action_type_id`` are provided as single IDs or lists of IDs only referenced objects having matching actions are included. To disable a filter you can also set it to ``null``.
Similarly, the filters ``referencing_action_id`` and ``referencing_action_type_id`` apply to referencing objects.
If these values are omitted or set to ``null``, no additional filter is applied for the recursion.
``referencing_filter_operator`` and ``referenced_filter_operator`` can be set to ``"and"`` or ``"or"`` for this as well, just as for the workflow view, to control whether only one (``"or"``) or both (``"and"``) filters need to be matched. Unlike the default for the workflow view, ``filter_operator`` defaults to ``"or"``.
The maximum recursion depth of the view can be configured by providing a positive integer for ``max_depth``.

.. code-block:: json
    :caption: A recursive workflow view definition including samples (``-99``) and measurements (``-98``) referencing the object as well as referenced objects created using the action with ID ``1``. Only referenced objects created using the action with ID ``1`` are handled recursively to a maximum recursion depth of ``2``.

    "workflow_views": [
        {
            "referencing_action_type_id": [-98, -99],
            "referenced_action_id": 1,
            "recursion_filters": {
                "referenced_action_id": 1,
                "referencing_action_id": [],
                "max_depth": 2
            },
            "title": {"en": "Processing", "de": "Bearbeitung"}
        }
    ]

workflow_show_more
^^^^^^^^^^^^^^^^^^

This attribute works the same as ``show_more``, but is only applied when the object is included in a workflow view.


.. _metadata_arrays:

Arrays
``````

Array properties represent a list of properties of the same type called ``items``. While each property in an object must have an individual subschema, all items in an array share their subschema.

.. code-block:: json
    :caption: An array property containing texts, with a default and length restrictions

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

type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``array``.

title
^^^^^

The title for the array as a JSON string or object, e.g. ``"Preparation Steps"`` or ``{"en": "Notes"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given array property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

items
^^^^^

This JSON object contains the subschema for the items in this array. Arrays may contain all other data types (aside from the special types ``tags`` and ``hazards``, which may only occur in the root object).

.. code-block:: json
    :caption: The items attribute from the example above.

    "items": {
      "title": "Note",
      "type": "text"
    }

minItems
^^^^^^^^

A number that sets how many items must at least be present in the array for it to be valid, e.g. ``1``. By default, there is no minimum number of items.

maxItems
^^^^^^^^

A number that sets how many items must at most be present in the array for it to be valid, e.g. ``10``. By default, there is no limit to the number of items.

default
^^^^^^^

A JSON array containing the default data for the individual items. See also the ``defaultItems`` attribute below.

.. code-block:: json
    :caption: The default attribute from the example above.

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

defaultItems
^^^^^^^^^^^^

If the ``default`` attribute is not set, this number can be used to set how many items should be present by default, e.g. if it is common to have at least one item, but this is not a strict requirement, ``defaultItems`` could be set to ``1``.

style
^^^^^

This attribute is a string or dict mapping ``"form"``, ``"view"`` and ``"inline_edit"`` to strings or null, indicating how the array should be displayed. A string will be used for both editing and viewing object data, while a dict can specify the style depending on whether the user is editing the data or viewing the data, with or without inline editing enabled. By default, the items will be shown one after another, but sometimes a different behavior may be desired. If the items are objects, using the ``table`` style may be useful to create a table with the items as rows and their properties in the columns. For top-level tables with many columns, the ``full_width_table`` style can be used to let the table be as wide as the browser window permits. Alternatively, if the items should be in the columns and their properties should be in the rows, the ``horizontal_table`` style can be used. If the items are neither objects nor arrays, the ``list`` style may be useful to create a simple list. If the items are texts with a list of choices, then the style ``choice`` will result in a dropdown allowing the user to select multiple items. If the items are objects with a ``datetime`` property named datetime, the ``timeline`` style will show a timeline plot for the array items.

.. note:: Using a style other than the default may lead to issues when entering or viewing object data. Please test the action and how its objects are displayed. If you encounter issues with a style, you can `report it on GitHub <https://github.com/sciapp/sampledb/issues/new>`_.

note
^^^^

A note to display below the field when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Please describe the process in detail."`` or ``{"en": "Can be filled in later."}``.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.


.. _metadata_texts:

Texts
`````

Text properties represent various types of textual data:

- Single line texts
- Multi line texts
- Rich text using Markdown
- A selection from a list of predefined texts (displayed as a dropdown field)


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

.. code-block:: json
    :caption: A sample description allowing Markdown content

    {
      "title": "Description",
      "type": "text",
      "markdown": true
    }

.. code-block:: json
    :caption: A measurement option using predefined choices

    {
      "title": "Measurement Option",
      "type": "text",
      "choices": [
        "Option A",
        "Option B"
      ]
    }

type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``text``.

title
^^^^^

The title for the text as a JSON string or object, e.g. ``"Description"`` or ``{"en": "Substrate"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

dataverse_export
^^^^^^^^^^^^^^^^

This attribute is a boolean that controls whether this property should be exported as part of a :ref:`dataverse_export` or not, although the exporting user will still have the choice to enable or disable this property during the export. By default, it is set to ``false``.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.

note
^^^^

A note to display below the field when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Please describe the process in detail."`` or ``{"en": "Can be filled in later."}``.

tooltip
^^^^^^^

A tooltip to display when hovering the mouse cursor over the property title, as a JSON string or object, e.g. ``"A detailed process description"`` or ``{"en": "A detailed process description"}``.

placeholder
^^^^^^^^^^^

The placeholder for the text when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Description"`` or ``{"en": "Substrate"}``.

default
^^^^^^^

The default value for this property, as a JSON string or object, e.g. ``"Example"`` or ``{"en": "Example"}``. If there are ``choices`` defined for this property, then the default must be one of the choices.


.. code-block:: json
    :caption: The default attribute from one of the examples above

    "default": "Sample-"

minLength
^^^^^^^^^

This attribute sets the minimum number of characters for the value of this property, e.g. ``1``. By default, there is no minimum length.

maxLength
^^^^^^^^^

This attribute sets the maximum number of characters for the value of this property, e.g. ``1``. By default, there is no maximum length.

pattern
^^^^^^^

A JSON string containing a `regular expression <https://docs.python.org/3/library/re.html#regular-expression-syntax>`_ limiting what values are valid for this property, e.g. ``^Sample-[0-9]{4}$`` to ensure only values starting with ``Sample-`` followed by a four digit number will be valid.

languages
^^^^^^^^^

Either a JSON array containing the allowed language codes for this property, e.g. ``["en", "de"]`` or the JSON string ``"all"`` to allow all languages enabled for user input. By default, this attribute is set to ``["en"]`` only allowing english language input.

choices
^^^^^^^

A JSON array of acceptable values, either as JSON objects or JSON strings. If choices are provided, the value for this property must be one of the choices and a dropdown menu will be used to let the user select the choice. If this property is not required, not selecting a choice at all and therefore not providing a value for this property will also be valid.

.. code-block:: json
    :caption: The choices attribute from one of the examples above

    "choices": [
      "Option A",
      "Option B"
    ]

.. note:: For properties with ``choices`` set, you cannot provide a ``placeholder`` value and should not set a ``minLength``, ``maxLength`` or ``pattern``. Setting ``choices``, ``multiline`` and ``markdown`` are all mutually exclusive.

multiline
^^^^^^^^^

This attribute is a boolean that sets whether or not the value of this property may contain multiple lines. By default, this is ``false`` and the field when creating or editing an object using this schema will be for a single line only.

.. note:: Setting ``choices``, ``multiline`` and ``markdown`` are all mutually exclusive.

markdown
^^^^^^^^

This attribute is a boolean that sets whether or not the value of this property should be rich text based on the Markdown syntax. If this attribute is true, users will be able to input multiple lines and use a Markdown editor to include formatting, images and other rich text elements in the value of this property. By default, this is ``false``.

.. note:: Setting ``choices``, ``multiline`` and ``markdown`` are all mutually exclusive.


.. _metadata_booleans:

Booleans
````````

Booleans represent a value that is either true or false.

.. code-block:: json
    :caption: A boolean property with a default

    {
      "title": "Lid Open?",
      "type": "bool",
      "default": true
    }

type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``bool``.

title
^^^^^

The title for the boolean as a JSON string or object, e.g. ``"Pressurization"`` or ``{"en": "Target Set"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

dataverse_export
^^^^^^^^^^^^^^^^

This attribute is a boolean that controls whether this property should be exported as part of a :ref:`dataverse_export` or not, although the exporting user will still have the choice to enable or disable this property during the export. By default, it is set to ``false``.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.

note
^^^^

A note to display below the field when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Set if chamber was pressurized."`` or ``{"en": "Check box if a target was set"}``.

tooltip
^^^^^^^

A tooltip to display when hovering the mouse cursor over the property title, as a JSON string or object, e.g. ``"Whether the chamber was pressurized"`` or ``{"en": "Whether a target was set"}``.

default
^^^^^^^

The default value for this property as a boolean, so ``true`` or ``false``.

.. _metadata_quantities:

Quantities
``````````

Properties of the ``quantity`` type represent physical quantities and unitless numbers. The ``units`` attribute is mandatory, so for unitless numbers it must be set to ``1``.

.. code-block:: json
    :caption: A temperature property with a default of 25°C (298.15K)

    {
      "title": "Temperature",
      "type": "quantity",
      "units": "degC",
      "default": 298.15
    }

type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``quantity``.

title
^^^^^

The title for the quantity as a JSON string or object, e.g. ``"Temperature"`` or ``{"en": "Detector Distance"}``.

placeholder
^^^^^^^^^^^

The placeholder for the text when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Temperature in K"`` or ``{"en": "Detector Distance (horizontal)"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

dataverse_export
^^^^^^^^^^^^^^^^

This attribute is a boolean that controls whether this property should be exported as part of a :ref:`dataverse_export` or not, although the exporting user will still have the choice to enable or disable this property during the export. By default, it is set to ``false``.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.

note
^^^^

A note to display below the field when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Temperature in measurement chamber"`` or ``{"en": "Horizontal distance between sample and detector"}``.

tooltip
^^^^^^^

A tooltip to display when hovering the mouse cursor over the property title, as a JSON string or object, e.g. ``"The temperature as measured by sensor T1"`` or ``{"en": "The nominal detector distance"}``.

default
^^^^^^^

The default value for this property as a number or a :ref:`quantity object <metadata_quantity_object>`.
A number is interpreted as value in base units, so if ``units`` is set to ``nm`` and you want to set a default of 10nm, you need to set ``default`` to ``0.00000001`` as it will be interpreted in meters. If there are multiple units, the first one will be used for the default.

.. code-block:: json
    :caption: A quantity object default. In this case the ``units`` property is optional as it could be derived from the schema.

    "size": {
      "title": "Size",
      "type": "quantity",
      "units": "nm",
      "default": {
        "magnitude": 10,
        "units": "nm"
      }
    }

units
^^^^^

A JSON array of strings or a single string containing the units for this property, e.g. ``"nm"``,  ``"degC"`` or ``["cm", "mm"]``.

.. note:: These units will be parsed using the `pint Python Package <https://pint.readthedocs.io/en/latest/index.html>`_ with additional `units defined by SampleDB <https://github.com/sciapp/sampledb/blob/develop/sampledb/logic/unit_definitions.txt>`_.

display_digits
^^^^^^^^^^^^^^

This attribute is the number of decimal places to be shown when displaying the magnitude, e.g. ``2`` to show ``1.2345`` as ``1.23``. The magnitude will be rounded for this, though due to the `limitations of floating point representation <https://docs.python.org/3/tutorial/floatingpoint.html>`_, small rounding errors may occur. Also due to limitations, at most 15 decimal places can be displayed.

min_magnitude
^^^^^^^^^^^^^

The minimum value for this property as a number. This should be a value in base units, so if ``units`` is set to ``nm`` and you want to set the minimum to 10nm, you need to set ``min_magnitude`` to ``0.00000001`` as it will be interpreted in meters.

max_magnitude
^^^^^^^^^^^^^

The maximum value for this property as a number. This should be a value in base units, so if ``units`` is set to ``nm`` and you want to set the maximum to 10nm, you need to set ``max_magnitude`` to ``0.00000001`` as it will be interpreted in meters.

calculation
^^^^^^^^^^^

This JSON object defines how to automatically calculate a value for this property, depending on the values of other properties, if no different value has been provided by the user. The ``formula`` attribute defines the calculation logic and follows the syntax of ``math.evaluate`` from `Math.JS <https://mathjs.org/>`_. The ``property_names`` attribute contains names of other quantity properties, either as an array of names or as a JSON object mapping names used in the ``formula`` attribute to a path to another property, whose values are referenced in the ``formula`` attribute. Such paths are relative to the current property and contain strings for property names, ``".."`` for going up one level in the schema, integers for absolute array indices, strings containing ``+`` or ``-`` and an integer for relative array indices, or strings containing ``*`` to represent all array indices. The optional attribute ``digits`` may be an integer between 0 and 15 which defines the number of decimals the calculation result should be rounded to. The example below shows calculations for several properties referencing each other in the ``formula`` attribute:

.. code-block:: javascript
    :caption: An example schema with calculation attributes

    {
        "title": "Calculation Example",
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "distance": {
                "title": "Distance",
                "type": "quantity",
                "units": "m",
                "calculation": {
                    "property_names": [
                        "time",
                        "speed"
                    ],
                    "formula": "time * speed"
                }
            },
            "time": {
                "title": "Time",
                "type": "quantity",
                "units": "s",
                "calculation": {
                    "property_names": [
                        "distance",
                        "speed"
                    ],
                    "formula": "distance / speed"
                }
            },
            "speed": {
                "title": "Speed",
                "type": "quantity",
                "units": "m / s",
                "calculation": {
                    "property_names": {
                        "d": ["distance"],
                        "t": ["distance", "..", "time"]
                    },
                    "formula": "d / t"
                }
            }
        },
        "propertyOrder": [
            "name",
            "distance",
            "time",
            "speed"
        ],
        "required": [
            "name"
        ]
    }


.. note::

    As the formula does not perform unit conversion, both the property this attribute is set for as well as the properties it depends on must have fixed units. If the units do not match, e.g. due to a schema upgrade, the calculation will not be performed.


.. _metadata_quantity_object:

Quantity Objects
^^^^^^^^^^^^^^^^

Quantity data is stored in the notation shown in the codebox below.
It includes the magnitude in base units, a unit to use, the magnitude in given unit, dimensionality and the type, which is ``quantity`` for quantities.

When this is used as input for a quantity default value, a minimal set of parameters is sufficient, e.g. ``units``, if the unit to use cannot be derived unambiguously from the schema, and either ``magnitude`` or ``magnitude_in_base_units``.

.. code-block:: json
    :caption: A complete quantity object

    {
        "_type": "quantity",
        "magnitude": 100,
        "units": "cm",
        "magnitude_in_base_units": 1.0,
        "dimensionality": "dimensionless"
    }

.. _metadata_datetimes:

Datetimes
`````````

Datetime properties represent points in time. They are stored using ``YYYY-MM-DD hh:mm:ss`` notation and UTC, though users may enter and display them in differing timezones.

.. code-block:: json
    :caption: A datetime property with a default value

    {
      "title": "Creation Datetime",
      "type": "datetime",
      "default": "2018-12-05 15:38:12"
    }

type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``datetime``.

title
^^^^^

The title for the datetime as a JSON string or object, e.g. ``"Creation Date"`` or ``{"en": "Use Before"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

dataverse_export
^^^^^^^^^^^^^^^^

This attribute is a boolean that controls whether this property should be exported as part of a :ref:`dataverse_export` or not, although the exporting user will still have the choice to enable or disable this property during the export. By default, it is set to ``false``.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.

style
^^^^^

This attribute is a string or dict mapping ``"form"``, ``"view"`` and ``"inline_edit"`` to strings or null, indicating how the datetime should be displayed. A string will be used for both editing and viewing object data, while a dict can specify the style depending on whether the user is editing the data or viewing the data, with or without inline editing enabled. By default, the datetime will be shown as date and time, formatted according to the user's locale. If using the ``date`` or ``time`` styles, datetimes will still contain both a date and a time, but only one of those will be displayed, the time for the ``time`` style or the date for the ``date`` style. When editing a datetime property, both date and time will be shown and can be edited, independent of the style.

.. note:: Using a style other than the default may lead to issues when entering or viewing object data. Please test the action and how its objects are displayed. If you encounter issues with a style, you can `report it on GitHub <https://github.com/sciapp/sampledb/issues/new>`_.

note
^^^^

A note to display below the field when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Use experiment starting time"`` or ``{"en": "Include cool down time in estimate"}``.

tooltip
^^^^^^^

A tooltip to display when hovering the mouse cursor over the property title, as a JSON string or object, e.g. ``"The experiment starting time"`` or ``{"en": "The time the experiment was started"}``.

default
^^^^^^^

A default value for the property, as a JSON string using ``YYYY-MM-DD hh:mm:ss`` notation and UTC, e.g. ``"2021-07-23 08:00:00"``. If no default is given, the current date and time when creating or editing an object using this schema will be used as the default.


.. _metadata_tags:

Tags
````

Tags are keywords that can be used to categorize and quickly find objects relating to a specific topic. They may only be used as a property of the root object with the name ``tags``. The tag values themselves may only consist of lowercase characters, digits and underscores.

.. code-block:: json
    :caption: A tags property with default tags

    {
      "title": "Tags",
      "type": "tags",
      "default": ["tag1", "tag2"]
    }

type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``tags``.

title
^^^^^

The title for the tags as a JSON string or object, e.g. ``"Tags"`` or ``{"en": "Keywords"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

dataverse_export
^^^^^^^^^^^^^^^^

This attribute is a boolean that controls whether this property should be exported as part of a :ref:`dataverse_export` or not, although the exporting user will still have the choice to enable or disable this property during the export. By default, it is set to ``false``.

default
^^^^^^^

A JSON array containing default tags as strings, e.g. ``[]`` or ``["demo", "documentation"]``. There must be no duplicates in the array and as noted above, tags are limited to lowercase characters, digits and underscores.


.. seealso::

    :ref:`Tags <tags>`


.. _metadata_hazards:

Hazards
```````

Hazards allow users to declare whether or not the substance represented by the object poses any hazards by selecting the relevant GHS pictograms. Hazards may only be used as a property of the root object with the name ``hazards``. If such a property exists, it must be required to avoid any ambiguity, so that users have to explicitly declare that a substance poses no hazards instead of just not entering any.

.. code-block:: json
    :caption: A hazards property

    {
      "title": "GHS hazards",
      "type": "hazards"
    }

type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``hazards``.

title
^^^^^

The title for the hazards as a JSON string or object, e.g. ``"GHS hazards"`` or ``{"en": "Hazards (GHS)"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

dataverse_export
^^^^^^^^^^^^^^^^

This attribute is a boolean that controls whether this property should be exported as part of a :ref:`dataverse_export` or not, although the exporting user will still have the choice to enable or disable this property during the export. By default, it is set to ``false``.

note
^^^^

A note to display below the hazards selection when creating or editing an object using this schema, as a JSON string or object, e.g. ``"See lab guidelines"`` or ``{"en": "Please provide additional information in the description."}``.

tooltip
^^^^^^^

A tooltip to display when hovering the mouse cursor over the property title, as a JSON string or object, e.g. ``"Hazards, as per supplier"`` or ``{"en": "Hazards, as per supplier"}``.

.. seealso::

    :ref:`Hazards <hazards>`


.. _metadata_plotly_charts:

plotly Charts
`````````````

Properties of this type allow users to store JSON data that can be rendered by `plotly <https://plotly.com/>`_. This is most useful in combination with automated data entry as opposed to manually creating and entering the JSON data.

.. code-block:: json
    :caption: A plotly chart from the plotly documentation

    {
      "data": [
        {
          "x": [
            "giraffes",
            "orangutans",
            "monkeys"
          ],
          "y": [
            20,
            14,
            23
          ],
          "type": "bar"
        }
      ]
    }

For more information on the plotly JSON format, see the `JSON chart schema <https://plotly.com/chart-studio-help/json-chart-schema/>`_.

.. code-block:: json
    :caption: A plotly chart property

    {
      "title": "Temperature",
      "type": "plotly_chart"
    }


type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``plotly_chart``.

title
^^^^^

The title for the plotly chart as a JSON string or object, e.g. ``"Temperature"`` or ``{"en": "Z Distance Movement"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

dataverse_export
^^^^^^^^^^^^^^^^

This attribute is a boolean that controls whether this property should be exported as part of a :ref:`dataverse_export` or not, although the exporting user will still have the choice to enable or disable this property during the export. By default, it is set to ``false``.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.

note
^^^^

A note to display below the JSON field when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Will be filled by bot"`` or ``{"en": "Upload raw log file as well"}``.

tooltip
^^^^^^^

A tooltip to display when hovering the mouse cursor over the property title, as a JSON string or object, e.g. ``"Temperature curve, extracted from log file"`` or ``{"en": "Temperature curve, extracted from log file"}``.


.. _metadata_user_references:

User References
```````````````

Properties of this type allow you to reference SampleDB users.

.. code-block:: json
    :caption: A user reference property

    {
      "title": "Client",
      "type": "user"
    }


type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``user``.

title
^^^^^

The title for the property as a JSON string or object, e.g. ``"Client"`` or ``{"en": "Principal Investigator"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

dataverse_export
^^^^^^^^^^^^^^^^

This attribute is a boolean that controls whether this property should be exported as part of a :ref:`dataverse_export` or not, although the exporting user will still have the choice to enable or disable this property during the export. By default, it is set to ``false``.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.

note
^^^^

A note to display below the field when creating or editing an object using this schema, as a JSON string or object, e.g. ``"For external users, leave blank and fill in information below"`` or ``{"en": "Remember to set as responsible user as well"}``.

tooltip
^^^^^^^

A tooltip to display when hovering the mouse cursor over the property title, as a JSON string or object, e.g. ``"The user who operated the instrument"`` or ``{"en": "The user who operated the instrument"}``.

default
^^^^^^^

A JSON number containing the user ID to be used as default selection, or a JSON string ``"self"`` to denote that the user who is currently creating or editing the object should be the default.


.. _metadata_object_references:

Object References
`````````````````

Properties of this type allow you to reference other objects, e.g. to denote a precursor material or a dataset used for a simulation. Using ``action_type_id`` or ``action_id`` you can limit which objects may be referenced using this property.

.. code-block:: json
    :caption: An object reference property

    {
      "title": "Measured Object",
      "type": "object_reference"
    }


type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``object_reference``.

title
^^^^^

The title for the property as a JSON string or object, e.g. ``"Precursor"`` or ``{"en": "Calibration Measurement"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

dataverse_export
^^^^^^^^^^^^^^^^

This attribute is a boolean that controls whether this property should be exported as part of a :ref:`dataverse_export` or not, although the exporting user will still have the choice to enable or disable this property during the export. By default, it is set to ``false``.

style
^^^^^

This attribute is a string or dict mapping ``"form"``, ``"view"`` and ``"inline_edit"`` to strings or null, indicating how the object reference should be displayed. A string will be used for both editing and viewing object data, while a dict can specify the style depending on whether the user is editing the data or viewing the data, with or without inline editing enabled. If the style is set to ``"include"`` and the reference is not part of a list or table, the information for the referenced object is included in the object page.

.. note:: Using a style other than the default may lead to issues when entering or viewing object data. Please test the action and how its objects are displayed. If you encounter issues with a style, you can `report it on GitHub <https://github.com/sciapp/sampledb/issues/new>`_.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.

note
^^^^

A note to display below the field when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Leave blank if no precursor was used."`` or ``{"en": "Select the associated calibration measurement"}``.

tooltip
^^^^^^^

A tooltip to display when hovering the mouse cursor over the property title, as a JSON string or object, e.g. ``"Precursor, if any"`` or ``{"en": "Precursor, if any"}``.

action_type_id
^^^^^^^^^^^^^^

This attribute is a number or list of numbers that sets the IDs of action types to limit which actions an object referenced by this property may have been created with, e.g. ``-99`` to limit the property to samples or ``[-99, -98]`` to allow samples and measurements.

action_id
^^^^^^^^^

This attribute is a number or list of numbers that sets the IDs of actions to limit that only objects created with these actions may be referenced by this property, e.g. ``1`` or ``[1, 3]``.

filter_operator
^^^^^^^^^^^^^^^

This attribute is either ``"and"`` or ``"or"`` and when both ``action_type_id`` and ``action_id`` are set, this controls whether both these filters need to be fulfilled or only one. By default (``"and"``), objects referenced by an ``object_reference`` property need to match both the ``action_id`` and  ``action_type_id`` filters, however when ``filter_operator`` is set to ``"or"`` it is enough for an object to match one of these filters.

Sample References
^^^^^^^^^^^^^^^^^

Properties of this type are a special case of object reference, limited to referencing samples. The same can be achieved using an object reference with ``action_type_id`` set to -99. These properties support the same attributes as those of type ``object_reference``, aside from ``action_id``, ``action_type_id`` and ``filter_operator``. Their type must be ``sample``.

.. code-block:: json
    :caption: A sample reference property

    {
      "title": "Previous Sample",
      "type": "sample"
    }

Measurement References
^^^^^^^^^^^^^^^^^^^^^^

Properties of this type are a special case of object reference, limited to referencing measurements. The same can be achieved using an object reference with ``action_type_id`` set to -98. These properties support the same attributes as those of type ``object_reference``, aside from ``action_id``, ``action_type_id`` and ``filter_operator``. Their type must be ``measurement``.

.. code-block:: json
    :caption: A measurement reference property

    {
      "title": "Preparatory Measurement",
      "type": "measurement"
    }


.. _metadata_timeseries:

Time Series
```````````

Properties of the ``timeseries`` type represent time series, i.e. a sequence of physical quantities or unitless numbers at specific points in time or relative times. The ``units`` attribute is mandatory, so for unitless numbers it must be set to ``1``.

.. code-block:: json
    :caption: A temperature time series property

    {
      "title": "Temperature Series",
      "type": "timeseries",
      "units": "degC"
    }

type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``timeseries``.

title
^^^^^

The title for the time series as a JSON string or object, e.g. ``"Temperature Series"`` or ``{"en": "Temperature Series"}``.

may_copy
^^^^^^^^

This attribute is a boolean that sets whether or not the data for the given property may be copied when using the **Use as template** functionality in SampleDB. By default, it is set to ``true``.

dataverse_export
^^^^^^^^^^^^^^^^

This attribute is a boolean that controls whether this property should be exported as part of a :ref:`dataverse_export` or not, although the exporting user will still have the choice to enable or disable this property during the export. By default, it is set to ``false``.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.

note
^^^^

A note to display below the field when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Pressure"`` or ``{"en": "Sample Temperature"}``.

tooltip
^^^^^^^

A tooltip to display when hovering the mouse cursor over the property title, as a JSON string or object, e.g. ``"Pressure, as extracted from log file"`` or ``{"en": "Temperature, as set in instrument settings"}``.

units
^^^^^

A JSON array of strings or a single string containing the units for this property, e.g. ``"nm"``,  ``"degC"`` or ``["cm", "mm"]``.

.. note:: These units will be parsed using the `pint Python Package <https://pint.readthedocs.io/en/latest/index.html>`_ with additional `units defined by SampleDB <https://github.com/sciapp/sampledb/blob/develop/sampledb/logic/unit_definitions.txt>`_.

display_digits
^^^^^^^^^^^^^^

This attribute is the number of decimal places to be shown when displaying the magnitudes, e.g. ``2`` to show ``1.2345`` as ``1.23``. The magnitudes will be rounded for this, though due to the `limitations of floating point representation <https://docs.python.org/3/tutorial/floatingpoint.html>`_, small rounding errors may occur. Also due to limitations, at most 27 decimal places can be displayed.

statistics
^^^^^^^^^^

This attribute allows to determine which statistics about the timeseries should be displayed in a list of strings. Defaults to ``["average", "stddev"]`` if not defined. Valid statistics:

- ``"average"``: Weighted average
- ``"stddev"``: Standard deviation
- ``"min"``: Minimum
- ``"max"``: Maximum
- ``"count"``: Count of values
- ``"first"``: First value
- ``"last"``: Last value


.. _metadata_files:

Files
`````

Properties of the ``file`` type represent files uploaded for the object that are given additional meaning by being referenced in the metadata.

.. code-block:: json
    :caption: A file property

    {
      "title": "Configuration File",
      "type": "file",
      "extensions": [".ini", ".cfg"]
    }

type
^^^^

This sets the type for this subschema as a JSON string and must be set to ``file``.

title
^^^^^

The title for the file as a JSON string or object, e.g. ``"Configuration File"`` or ``{"en": "Configuration File"}``.

conditions
^^^^^^^^^^

This attribute is a JSON array containing a list of conditions which need to be fulfilled for this property to be available to the user. By default, no conditions need to be met. For examples and more information, see :ref:`conditions`.

note
^^^^

A note to display below the field when creating or editing an object using this schema, as a JSON string or object, e.g. ``"Please upload a picture of the experiment setup."`` or ``{"en": "Please upload a picture of the experiment setup."}``.

tooltip
^^^^^^^

A tooltip to display when hovering the mouse cursor over the property title, as a JSON string or object, e.g. ``"Setup (top-down view)"`` or ``{"en": "Log file of first run (see logs/0001.log)"}``.

extensions
^^^^^^^^^^

An optional list of file extensions to limit which files can be selected, e.g. ``[".png", ".jpg", ".jpeg"]``. If no list of extensions is provided, all files can be selected.

preview
^^^^^^^

This attribute is a boolean that sets whether or not an image file should have a preview image displayed for this property. By default, it is set to ``false``.


.. _metadata_schema_templates:

Schema Templates
````````````````

Schema Templates offer a way to easily reuse action schemas.

If an *action_type* is marked as includable into other actions it's possible to reuse the schema.

The schema for a template action could look like the following:

.. code-block:: json
   :caption: Minimal schema template

    {
      "title": "test",
      "type": "object",
      "properties": {
        "name": {
          "title": "Name",
          "type": "text"
        },
        "value": {
          "title": "Value",
          "type": "text"
        }
      },
      "required": [
        "name"
      ],
      "propertyOrder": [
        "name",
        "value"
      ]
    }

There is generally no difference to the schemas of other actions.

Schema templates can be included into other actions by providing a ``template`` for a property of type ``object``

.. code-block:: json
   :caption: Action with included schema template

    {
      "title": "Action with included Schema Template",
      "type": "object",
      "properties": {
        "name": {
          "title": "Name",
          "type": "text"
        },
        "included": {
          "title": "Included Schema Template",
          "type": "object",
          "template": 15
        }
      },
      "required": [
        "name"
      ],
      "propertyOrder": [
        "name",
        "included"
      ]
    }

Internally, this will then be treated as if the schema template were used for the property ``included`` there, except that the ``name`` property will be removed to avoid redundancies. The resulting action will be equivalent to:

.. code-block:: json
   :caption: Action with schema template

    {
      "title": "Action with included Schema Template",
      "type": "object",
      "properties": {
        "name": {
          "title": "Name",
          "type": "text"
        },
        "included": {
          "title": "Included Schema Template",
          "type": "object",
          "properties": {
            "value": {
              "title": "Value",
              "type": "text"
            }
          },
          "required": [],
          "propertyOrder": ["value"]
        }
      },
      "required": [
        "name"
      ],
      "propertyOrder": [
        "name",
        "included"
      ]
    }

When the schema template action is updated, all actions using it will be updated as well, as long as the resulting schema is still valid.

.. _conditions:

Conditional Properties
----------------------

Some properties might only sometimes be needed, based on some conditions, such as a particular setting of an instrument. Properties can contain conditions like this, consisting of a JSON object with a ``type`` and additional information depending on the type of condition.

.. code-block:: javascript
    :caption: A schema with a conditional property

    {
      "title": "Example Object",
      "type": "object",
      "properties": {
        "name": {
          "title": "Object Name",
          "type": "text",
          "languages": ["en", "de"]
        },
        "dropdown": {
          "title": "Dropdown",
          "type": "text",
          "choices": [
            {"en": "A"},
            {"en": "B"}
          ],
          "default": {"en": "A"}
        },
        "conditional_text": {
          "title": "Conditional Text",
          "type": "text",
          "markdown": true,
          "conditions": [
            {
              "type": "choice_equals",
              "property_name": "dropdown",
              "choice": {"en": "B"}
            }
          ]
        }
      },
      "required": ["name"]
    }

In the example schema above the property ``conditional_text`` will only be enabled if its ``choice_equals`` condition is fulfilled, that is if the ``dropdown`` property has the value ``{"en": "B"}`` selected.

The following types of conditions are supported by SampleDB:

choice_equals
`````````````

For this type of condition, the ``property_name`` attribute must be the name of another property, in the same object as the property the condition is for. The property of that name must be a property of type ``text`` with the ``choices`` attribute set. The condition must have a ``choice`` attribute that must be one of those choices, and for the condition to be fulfilled that choice must be selected.

.. code-block:: javascript
    :caption: A choice_equals condition

    {
      "type": "choice_equals",
      "property_name": "dropdown",
      "choice": {"en": "B"}
    }

user_equals
```````````

For this type of condition, the ``property_name`` attribute must be the name of another property, in the same object as the property the condition is for. The property of that name must be a property of type ``user``. The condition must have a ``user_id`` attribute that must be the ID of a user, and for the condition to be fulfilled that user must be selected.

.. code-block:: javascript
    :caption: A user_equals condition

    {
      "type": "user_equals",
      "property_name": "client",
      "user_id": 1
    }

If the ``user_id`` is set to ``null`` instead, the condition will be fulfilled if no user has been selected.

.. code-block:: javascript
    :caption: A user_equals condition for not having selected a user

    {
      "type": "user_equals",
      "property_name": "client",
      "user_id": null
    }

bool_equals
```````````

For this type of condition, the ``property_name`` attribute must be the name of another property, in the same object as the property the condition is for. The property of that name must be a property of type ``bool``. The condition must have a ``value`` attribute that must be either ``true`` or ``false``, and for the condition to be fulfilled the property must also be true or false, correspondingly.

.. code-block:: javascript
    :caption: A bool_equals condition

    {
      "type": "bool_equals",
      "property_name": "heating_on",
      "value": true
    }

object_equals
`````````````

For this type of condition, the ``property_name`` attribute must be the name of another property, in the same object as the property the condition is for. The property of that name must be a property of type ``object_reference``, ``sample`` or ``measurement``. The condition must have a ``object_id`` attribute that must be the ID of an object, and for the condition to be fulfilled that object must be selected.

.. code-block:: javascript
    :caption: An object_equals condition

    {
      "type": "object_equals",
      "property_name": "precursor",
      "object_id": 1
    }

If the ``object_id`` is set to ``null`` instead, the condition will be fulfilled if no object has been selected.

.. code-block:: javascript
    :caption: An object_equals condition for not having selected an object

    {
      "type": "object_equals",
      "property_name": "precursor",
      "object_id": null
    }

any / all
`````````

To denote that either only one or all of a list of conditions need to be fulfilled, the ``any`` or ``all`` condition type can be used, containing other conditions. An ``any`` condition is fulfilled, if any one of the conditions in it is fulfilled. If it does not contain any conditions, it will be considered as not being fulfilled. An ``all`` condition is fulfilled, if all of the conditions in it are fulfilled. If it does not contain any conditions, it will be considered as being fulfilled.

.. code-block:: javascript
    :caption: An any condition

    {
      "type": "any",
      "conditions": [
        {
          "type": "bool_equals",
          "property_name": "example_bool_1",
          "value": true
        },
        {
          "type": "bool_equals",
          "property_name": "example_bool_2",
          "value": true
        }
      ]
    }

.. code-block:: javascript
    :caption: An all condition

    {
      "type": "all",
      "conditions": [
        {
          "type": "bool_equals",
          "property_name": "example_bool_1",
          "value": true
        },
        {
          "type": "bool_equals",
          "property_name": "example_bool_2",
          "value": true
        }
      ]
    }

not
```

To denote that a certain condition must not be met, the ``not`` condition type can be used together with that other condition.

.. code-block:: javascript
    :caption: A not condition

    {
      "type": "not",
      "condition": {
        "type": "object_equals",
        "property_name": "example_object",
        "object_id": null
      }
    }

.. note:: If you need a new type of conditions, please `open an issue on GitHub <https://github.com/sciapp/sampledb/issues/new>`_ to let us know.

.. _recipes:

Recipes
-------

Recipes allow setting default value sets that can be applied while editing or creating an object.
They can be added to an object, including subobjects and objects in arrays, as a list of recipe objects.
Each recipe has to be given a name by setting the ``name``. Default values are described in the ``property_values`` section (see code box below).

Currently, only recipe values for parameters of the types ``text``, ``quantity``, ``bool``, and ``datetime`` are supported.
By setting a value to ``null`` the associated input is cleared.
As ``bool`` inputs do not support a ``null`` value you might use ``false`` to uncheck the checkbox instead.

.. code-block:: javascript
    :caption: An action schema containing a recipe

    {
      "title": "Recipe",
      "type": "object",
      "recipes": [
        {
          "name": {
            "en": "Recipe 1",
            "de": "Rezept 1"
          },
          "property_values": {
            "text": {
              "text": {
                "en": "English Text",
                "de": "Deutscher Text"
              },
              "_type": "text"
            }
          }
        }
      ],
      "properties": {
        "name": {
          "title": "Name",
          "type": "text"
        },
        "text": {
          "title": "Text",
          "type": "text",
          "languages": ["de", "en"]
        }
      },
      "required": ["name"]
    }

Query Placeholder
-----------------

When creating new objects through the user interface, query placeholders can
automatically populate predefined values. This allows another application,
script, or bookmark to specify known values, while the user manually enters
the remaining ones.

For example:

::

  /objects/new?action_id=1&properties.name=via_query_placeholder

  # or:

  /objects/new?action_id=1
  &properties.name=test
  &properties.count=100
  &properties.size=10nm
  &properties.created=2025-01-01 10:20:30
  &properties.boolfield=false
  &properties.sample=1
  &properties.tags=a,b
  &properties.multilayer.0.repetitions=1

Limitations:

- Quantities must use one of the units specified in the schema of the field.
  E.g., if a schema expects either ``µm`` or ``nm``, then it's not possible to
  use ``um``.
- The unit of unitless quantities must be set as ``1`` within the schema.
- Values in Arrays, Objects and Conditional Properties can only be populated
  if the specified field would have been rendered by default. E.g., it's not
  possible to populate a field in an array if the array defaults to zero
  items.
- Only the following types are supported:

  - quantity
  - text
  - bool
  - datetime
  - tags
  - user
  - object_reference
  - sample
  - measurement
