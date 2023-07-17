.. _finding_objects_tutorial:

Finding Objects
===============

If you wish to find data that has been entered into SampleDB in the past, there are various ways to search for objects in SampleDB. In any case, you will need to have **READ** permissions for an object to be able to find and view it.

One way to find objects is to use the search function in SampleDB. You can use the search either by entering a **Search Query** into the text field in the navigation bar or by clicking on *Objects* ➜ *Search* to get to the **Search Query Builder**. There are two search modes in SampleDB: a simple text search, which will look for a text anywhere in the internal metadata representation of an object, or the advanced search, which can filter objects using their properties and boolean algebra.

.. figure:: ../static/img/generated/search_query_builder.png
    :alt: Using the Search Query Builder

    Using the Search Query Builder

To search for a text, e.g. an object's name or a word mentioned in an object description, simply enter that word into the search field and click on the search icon. To search using the advanced search instead, you will need to either manually write a valid search query or create one using the search query builder. There you can add filter conditions step by step, e.g. that a text field with a given name should have a specific value. In both cases, you will see a list of objects that fulfill the given search criteria, if any could be found.

.. figure:: ../static/img/generated/object_list.png
    :alt: A list of objects

    A list of objects

There, you can click on **Filters** to apply additional filters to the object list, e.g. by action type, action, instrument, location, or publication.

.. figure:: ../static/img/generated/object_list_filters.png
    :alt: Object list filters dialog

    Object list filters dialog

Another way to find objects, if you know a user who worked on them, is to filter by **User Activity**. If you go to their user profile, e.g. via *More* ➜ *Users*, you can click on the button *View Objects* to view all objects with activity by that user. By clicking on the caret, you can also find objects that the user has specific permissions for. You can do the same for groups or projects by clicking on *View Objects* on a group or project page.

.. admonition:: Summary

  - You need **READ** permissions to find and view an object.
  - You can either search by text or by metadata fields.
  - You can filter the object list using various criteria.
  - You can also find objects by user activity.

..  seealso::

  - :ref:`permissions_tutorial`
  - :ref:`object_search`
