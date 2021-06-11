.. _languages:

Languages
=========

Although SampleDB was primarily developed in English, it now supports two ways of using it with other languages:

- SampleDB itself has been translated to German and can be translated in other languages as well in the future.
- Object metadata fields, actions, instruments, groups and other user-generated content can contain translations for various languages, defined by the administrator.

If you wish to contribute to a translation of SampleDB, see the `SampleDB contribution guide <https://github.com/sciapp/sampledb/blob/develop/CONTRIBUTING.md>`_.

By default, a SampleDB instance will have English and German as built-in languages for user input, with only English enabled. This way all text fields will appear as they were before this change. If you enable German input or create a new language that is enabled for input, many fields for which a translation would be reasonable will offer users to add a translation in the newly enabled language. When a user uses a language for which some content does not provide a translation, the content will be shown in English instead.

.. figure:: ../static/img/generated/translations.png
    :alt: Fields for providing translations for an Action name

    Fields for providing translations for an Action name

To add a new language for user input, administrators can go to *More* → *Languages* and click *Add new language*. The field *Datetime format for datetime* expects a format in the syntax used by the Python `datetime module <https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes>`_ and the field *Datetime format for moment* expects a format in the syntax used by the JavaScript `moment.js package <https://momentjs.com/docs/#/parsing/string-format/>`_. These formats will be used for user input, and formats based on the language code will be use used for displaying datetimes.
