.. _backup_and_restore:

Backup and Restore
==================

SampleDB stores all its information in:

- the PostgreSQL database, and
- the file directory

So to create a backup of SampleDB, you will need to create backups of these.

It is recommended that you stop the SampleDB container before creating backups and start it again afterwards.

While you yourself will need to decide when and how exactly you want to create backups, the following sections show examples of how backups of these two sources of information can be created.

Please follow general system administration best practices.

The PostgreSQL database
-----------------------

One way of creating a backup of a PostgreSQL database is to create an SQL dump using the `pg_dump` tool:

.. code-block:: bash

    docker exec sampledb-postgres pg_dump -U postgres postgres > backup.sql

The resulting ``backup.sql`` file can then be copied to another system.

To restore the PostgreSQL database from such an SQL dump, you should first remove the existing database:

.. code-block:: bash

    docker stop sampledb-postgres
    docker rm sampledb-postgres
    rm -rf pgdata

You can then recreate the database container and restore the backup using the ``psql`` tool:

.. code-block:: bash

    docker run \
        -d \
        -e POSTGRES_PASSWORD=password \
        -e PGDATA=/var/lib/postgresql/data/pgdata \
        -v `pwd`/pgdata:/var/lib/postgresql/data/pgdata:rw \
        --restart=always \
        --name sampledb-postgres \
        postgres:12
    docker exec -i sampledb-postgres psql -U postgres postgres < backup.sql

If you have set different options for the database container before, e.g. setting it in a specific network and giving it a fixed IP, you should also set these options here.

For more information on backing up a PostgreSQL database and restoring a backup, see the `PostgreSQL documentation on Backup and Restore <https://www.postgresql.org/docs/current/backup.html>`_

The file directory
------------------

If you have followed the Getting Started guide, you will have set the ``SAMPLEDB_FILE_STORAGE_PATH`` variable and mounted a local directory ``files`` into the SampleDB container so that SampleDB can store uploaded files in this directory.

Files are uploaded there over time and should not change, so this directory is especially suited for incremental backups.

One way to copy it to another system is to use the ``rsync`` tool:

.. code-block:: bash

    rsync -a files <hostname>:<backup_directory>

Or, if you wish to create a backup locally, you can simply use ``cp``:

.. code-block:: bash

    cp -an files <backup_directory>

Here the ``-n`` option prevents copying files which already exist in the backup directory.

To restore the backup, simply copy the backup to your local file directory.