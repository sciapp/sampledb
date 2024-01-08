.. _deprecated_features:

Deprecated Features
===================

As SampleDB is being developed, some features may change or may become redundant. As such, to avoid needless complexity and development effort, some features become deprecated and may be disabled or removed in the future. If a SampleDB instance relies on deprecated features, administrators will be shown a warning about those features so they can configure their SampleDB instance accordingly.

.. note:: If you rely on a deprecated feature in your SampleDB instance, please `let us know`_.

Local File Storage
------------------

Originally, files uploaded to SampleDB were stored in a specific directory, structured by action and object IDs. While this is an efficient way of storing file data, this also meant that file metadata and file data were stored apart from another. As a result of this, the principles of atomicity, consistency and integrity could not be upheld as rigidly as if both were stored in the database. Additionally, this made the backup process more complex, as the file storage path would need to be backed up in addition to the database.

To improve this, database file storage was added to SampleDB and made the default for storing file data in SampleDB version 0.19. To simplify the migration, before version 0.26, local file storage is still enabled and the :ref:`script <administration_scripts>` ``move_local_files_to_database`` is provided for moving files from local to database storage.

As of version 0.21, local file storage is deprecated and administrators are urged to move all remaining locally stored files to database storage.

As of version 0.24, files with local storage cannot be created via the API.

As of version 0.26, files with local storage are not supported anymore.

Synchronous Loading of Object Lists
-----------------------------------

There are various pages in SampleDB that require loading the names, IDs and other basic information on a large number of objects, e.g. all objects readable by the current user, such as when editing object references. Originally, these were loaded synchronously and passed to the template engine on the server side. With a large number of objects, this could lead to long loading times, even in situations where the objects might not be needed to use the page otherwise.

In version 0.15 the configuration value LOAD_OBJECTS_IN_BACKGROUND was added to allow loading these objects asynchronously and inserting them in the relevant select fiels on the client side. To preserve existing behavior, this variable was set to be False by default, even though loading the objects asynchronously leads to performance improvements and does not negatively impact the user experience.

As of version 0.21, LOAD_OBJECTS_IN_BACKGROUND is set to True by default and setting it to False is deprecated.

As of version 0.24, objects will be loaded asynchronously in the background.

Numeric Tags
------------

Numeric tags, which only consist of digits, can cause confusion because the search syntax ``#tag`` will conflict with the ``#id`` search syntax for object and user references. To avoid these, numeric tags will be disabled in new instances of SampleDB and those instances which have not used numeric tags in the past, as of version 0.21. The configuration variable ENABLE_NUMERIC_TAGS can be used to explicitly enable support for numeric tags and if an existing object uses numeric tags already, this value will be ``True`` by default. Otherwise it will be ``False`` by default.
