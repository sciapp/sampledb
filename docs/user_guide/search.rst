.. _object_search:

Search
======

Users can find objects using the |service_name| search. There are two modes for the object search:

- A *simple* text-based search, and
- an *advanced* search using property comparisons

.. _simple_search:

Simple Search
-------------

To use the simple search, users can enter words or phrases into the search field and will find all objects containing these.


.. _advanced_search:

Advanced Search
---------------

The advanced search allows a more fine grained search by performing comparisons on objects' properties and supporting Boolean algebra. Users can enter a query into the search field and select 'Advanced Search' in the adjacent dropdown, though using operators like ``=`` will automatically enable the advanced search mode. Another way to perform an advanced search is by clicking on the search icon next to an object's property that will search for other objects having the same value.

.. figure:: ../static/img/generated/advanced_search_by_property.png
    :alt: Search button for finding objects with an equal property

    Search button for finding objects with an equal property

When an advanced search is used, |service_name| will show the search tree that the query has been parsed into, to clearly show which filters were used.

.. figure:: ../static/img/generated/advanced_search_visualization.png
    :alt: Advanced search tree for the query '"Sb" in substance and (temperature < 110degC or temperature > 120degC)'

    Advanced search tree for the query ``"Sb" in substance and (temperature < 110degC or temperature > 120degC)``

In addition to attribute comparisons, the advanced search also allows searching for objects with files or links with a given name by using the special attribute ``file_name``, e.g. ``".dat" in file_name`` to find all objects with a file containing ``.dat`` in its name or ``file_name == "test.dat"`` to find all objects with a file named ``test.dat``.

Search Query Builder
````````````````````

Instead of manually writing search queries, you can use the Search Query Builder via **Objects** ➜ **Search** ➜ **Build Search Query** . This allows you to define search conditions, either requiring all or one of them to be met.

To define a condition, enter the name of the property you want to filter for, select the type of the condition and optionally enter any value to compare against, depending on the condition type.

.. figure:: ../static/img/generated/search_query_builder.png
    :alt: Using the Search Query Builder

    Using the Search Query Builder


Property Names
``````````````

To search for objects which have property fulfilling some condition, the internal name of that property must be known. Property names are set in an action's schema and the easiest way to find a property is to use the search button shown above. When searching for properties inside an object or array, dots are used as separators and a question mark can be used as wildcard for an array index, e.g. ``layers.?.name == "Base Layer"``.

Search queries can also search through referenced objects by prefixing the ``object_reference``, ``sample`` or ``measurement`` property with an asterisk and otherwise treating the referenced object as if it was simply part of the object you are searching, e.g. ``*sample.name == "Test"`` will find all objects with a property called ``sample`` that references an object with the name ``"Test"``. Only a single object reference like this can be included in a search query and this cannot be combined with array index placeholders.

Boolean operators
`````````````````

Boolean properties or comparisons of other properties can be combined with the boolean operators ``and``, ``or`` and ``not``. ``not`` is first in the order of operations, followed by ``and`` and ``or``. For a different order, parentheses can be used.

Text comparisons
````````````````

Text properties can currently be used either for direct comparisons, e.g. ``name = "Sample"``, or by checking whether a property contains a text, e.g. ``"MBE" in name``.

Quantity comparisons
````````````````````

Quantity properties can be compared using the basic mathematical comparison operators ``<``, ``<=``, ``>``, ``>=``, ``=`` and ``!=``. Comparisons will be performed in the quantities' base units.

Date comparisons
````````````````

Datetime properties can be compared using the basic mathematical comparison operators or the operators ``before``, ``after`` and ``on``. Dates to compare with must be entered using the format ``YYYY-MM-DD``.

Object or User References
`````````````````````````

To search for references to an object or user ID, ``==`` and `!=` are supported with the ID starting with ``#``, e.g. ``operator == #15``.

Tag search
``````````

Objects with certain tags can be found using ``#`` and the name of the tag, e.g. ``#hbs``.
