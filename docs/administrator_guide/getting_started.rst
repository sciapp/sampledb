.. _setup:

Getting Started
===============

Step 1: Minimal Installation
----------------------------

We recommend using our pre-built Docker images for setting up ``SampleDB``. You will need two containers, one for a PostgreSQL database and another for SampleDB itself, and a directory to store all files in.

If you would like to set up a development version of SampleDB instead, please see the `contribution guide <https://github.com/sciapp/sampledb/blob/develop/CONTRIBUTING.md>`_.

If you do not have Docker installed yet, please `install Docker <https://docs.docker.com/engine/install/>`_.

First, start your database container:

.. code-block:: bash

    docker run \
        -d \
        -e POSTGRES_PASSWORD=password \
        -e PGDATA=/var/lib/postgresql/data/pgdata \
        -v `pwd`/pgdata:/var/lib/postgresql/data/pgdata:rw \
        --restart=always \
        --name sampledb-postgres \
        postgres:12


Next, start the SampleDB container:

.. code-block:: bash

    docker run \
        -d \
        --link sampledb-postgres \
        -e SAMPLEDB_CONTACT_EMAIL=sampledb@example.com \
        -e SAMPLEDB_MAIL_SERVER=mail.example.com \
        -e SAMPLEDB_MAIL_SENDER=sampledb@example.com \
        -e SAMPLEDB_ADMIN_PASSWORD=password \
        -e SAMPLEDB_SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://postgres:password@sampledb-postgres:5432/postgres \
        -e SAMPLEDB_FILE_STORAGE_PATH=/home/sampledb/files/ \
        -v `pwd`/files:/home/sampledb/files:rw \
        --restart=always \
        --name sampledb \
        -p 8000:8000 \
        sciapp/sampledb:0.15.0

This will start a minimal SampleDB installation at ``http://localhost:8000`` and allow you to sign in with the username ``admin`` and the password ``password``.

Step 2: Basic Configuration
---------------------------

After visiting ``http://localhost:8000`` to verify that SampleDB runs, you should sign in as administrator and update your password.

Although you have a minimal SampleDB installation now, you will need to perform some further configuration. The code block starting the SampleDB Docker container contains several environment variables with placeholder values. After stopping the container, please start it with valid values for:

- SAMPLEDB_CONTACT_EMAIL
- SAMPLEDB_MAIL_SERVER
- SAMPLEDB_MAIL_SENDER

Your mail server might require additional settings and you can find descriptions of these variables in the :ref:`list of configuration environment variables<configuration>`.

You can use this moment to set other configuration variables, e.g. for the service name, service description, or imprint and privacy policy links.

You can restart the SampleDB container to change configuration variables at any time, so you can always return to this step later on.

Step 3: Creating Actions
------------------------

Your first step in actually using SampleDB should be to set up your first :ref:`actions`. Actions represent processes that create samples, perform measurements or running simulations.

1. We recommend that you start by setting up an Action for creating a generic sample in SampleDB with:
    - a name,
    - a creation date,
    - a multiline text description, and
    - an optional input sample.

   This will allow you to import samples as you move on, until all your processes for sample creation, preparation or import are modelled as individual Actions.
2. Next, we recommend that you set up two equally generic Actions for performing a measurement and for running a simulation. This is to allow your users to enter any measurements or simulations into your SampleDB installation which have not yet been modelled as individual Actions.
3. With these three generic Actions in place, you should then pick one process and model it as an Action. Try to capture all the information that would be required to reproduce a sample creation, measurement or simulation, and add it as properties to this Action's schema.

You can then improve your Actions' schemas and add new Actions as you become more experienced using SampleDB and gather feedback from your users.

Instruments
```````````

As you add more Actions, you may want to group some Actions by the instrument they are performed with and give the instrument scientists control over these Actions. To do so:

- create a new :ref:`Instrument <instruments>`,
- assign :ref:`instrument_scientists`, and
- create :ref:`actions` for this instrument.

Step 4: Preparing SampleDB for Production
-----------------------------------------

After the previous steps, you can fully evaluate SampleDB locally using the admin user. At this stage, however, you might want to make your SampleDB installation available to others and run SampleDB in production. We **strongly** recommend that you set up :ref:`TLS Termination<tls_termination>` and that you regularly create :ref:`backups <backup_and_restore>`.

Step 5: User Management
-----------------------

At this time, SampleDB users can either sign in using a username and password specific to SampleDB, or by using LDAP if it has been enabled using the :ref:`LDAP configuration variables<ldap_configuration>`.

If your facility already has an LDAP system for user management, we recommend that you configure LDAP in SampleDB so that users can use their existing credentials.

Otherwise, you can invite your users using the :ref:`User Invitation Form<authentication>`.

Next Steps
----------

- You might want to create :ref:`groups` or :ref:`projects` to model your existing team structures. While this can be useful, it is completely optional as users can set these up themselves.
- You might want to create a basic hierarchy of :ref:`locations`. Like groups and projects, users can create these themselves so this is optional.
- If you already have a JupyterHub installation or want to set up one, you might want to enable SampleDB :ref:`JupyterHub support <jupyterhub_support>`.
- SampleDB is still under active development. When a new version is released, you should consider :ref`upgrading your SampleDB installation <upgrading>`.
- If you have any questions about SampleDB or run into any issues setting up or running SampleDB, please `create an issue on GitHub <https://github.com/sciapp/sampledb/issues/new>`_.
