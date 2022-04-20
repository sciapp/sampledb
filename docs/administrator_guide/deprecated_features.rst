.. _deprecated_features:

Deprecated Features
===================

As SampleDB is being developed, some features may change or may become redundant. As such, to avoid needless complexity and development effort, some features become deprecated and may be disabled or removed in the future. If a SampleDB instance relies on deprecated features, administrators will be shown a warning about those features so they can configure their SampleDB instance accordingly.

.. note:: If you rely on a deprecated feature in your SampleDB instance, please `let us know`_.

Local File Storage
------------------

Originally, files uploaded to SampleDB were stored in a specific directory, structured by action and object IDs. While this is an efficient way of storing file data, this also meant that file metadata and file data were stored apart from another. As a result of this, the principles of atomicity, consistency and integrity could not be upheld as rigidly as if both were stored in the database. Additionally, this made the backup process more complex, as the file storage path would need to be backed up in addition to the database.

To improve this, database file storage was added to SampleDB and made the default for storing file data in SampleDB version 0.19. To simplify the migration, local file storage is still enabled and the :ref:`script <_administration_scripts>` ``move_local_files_to_database`` is provided for moving files from local to database storage.

As of version 0.21, local file storage is deprecated and administrators are urged to move all remaining locally stored files to database storage.
