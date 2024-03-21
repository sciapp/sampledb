.. _federation:

Federation
==========

|service_name| supports sharing information with partnering databases.

First steps
-----------

1. Create a UUID using the :code:`generate_uuid` script (see: :ref:`Administration Scripts <administration_scripts>`)
2. Set the :ref:`SAMPLEDB_FEDERATION_UUID <federation_configuration>` environment variable to the created UUID string
3. | Add a database via frontend after logging in as administrator:
   | `More -> Other Databases` (:code:`<host>/other-databases/`)
   | To exchange data giving a UUID and address is mandatory
4. Generate an export token by clicking the **+** button in the *Export* section
5. Set up the other database's export token as import token by clicking the **+** button in the *Import* section

Configured databases can be selected when editing the permissions for an object (see: :ref:`Sharing with other databases <federation_share>`).
You can repeat the steps 3 to 5 for every additional database you want to exchange data with.

UUIDs and federated keys
------------------------

To generate unique identifiers for objects in a federation and to identify individual databases, each database receives a `universally unique identifier (UUID) <https://en.wikipedia.org/wiki/Universally_unique_identifier>`_.
Based on this identifier a composite *federation key* is created, consisting of the local id of the object, action, location, or other information entry id and the component's UUID.

For example, a UUID can be created by using the :code:`generate_uuid` administration script.
Using pseudo-randomly generated UUIDs of version 4 is recommended.
Since there is a sufficiently small probability of version 4 UUIDs being assigned twice, there is no mandatory need to check for duplicates with other databases.

After setting the UUID once and starting exchanging data with another database the UUID must **not** ever be changed,
as this leads to unresolvable object references, duplicates, and confusion.

If no UUID is set using the environment variable :ref:`SAMPLEDB_FEDERATION_UUID <federation_configuration>` the federation feature is not activated.

Authentication
--------------

Databases verify themselves by tokens previously exchanged between them, similar to API tokens.
These are created by the database administrators and have to be exchanged individually.

Export tokens are used by other databases to verify themselves and are generated automatically.
A created export token is used by the partnering database as an import token to import the exported information.

.. _federation_managing_databases:

Managing other databases
------------------------

The administrator of a SampleDB instance manages the connections to other databases.
Adding a database requires specifying its UUID, exchanging data also requires one import and one export token as well as the database URL.
Additionally, a database should be given a name.

The administrator can also manually trigger the synchronization of data.

.. figure:: ../static/img/generated/other_database.png
    :alt: Managing other databases

    Managing other databases

Federation Graph
----------------

The databases that are connected to a SampleDB instance either directly or via others are shown in the federation graph. This can help give an overview over the SampleDB instances in a federation and their connections with each other. To disable being shown in the federation graph of other databases, the environment variable :ref:`SAMPLEDB_ENABLE_FEDERATION_DISCOVERABILITY <federation_configuration>` can be set to ``false``.

.. figure:: ../static/img/generated/federation_graph.png
    :alt: A federation graph

    A federation graph

Federated Login
---------------

The federated login allows users to authenticate using the login of a federation partner.

To enable this feature, the environment variable :ref:`SAMPLEDB_ENABLE_FEDERATED_LOGIN <federation_configuration>` can be set to ``true``. The federated login requires that both instances have set this environment variable.

After both instances have set up the environment variables, it is required to import updates on both instances so that metadata can be imported.

.. note::
    To enable the login with a federation partner, it is required that, when importing updates, the other database already has the metadata. This means the database that imports updates as the first one after activating this feature must import a second time as soon as the other database has also imported updates.

If set up properly, an additional button ("Sign in with …") will be added to the sign in page for each federation partner that is available for the federated login.

When using the federated login, the user must have a federated identity on the target database which links an existing local user with the used federated user from the other database. As an alternative to linking a local user, it is also possible to enable that new users can be created. To allow this, the environment variable :ref:`SAMPLEDB_ENABLE_FEDERATED_LOGIN_CREATE_NEW_USER <federation_configuration>` can be set to ``true``.
