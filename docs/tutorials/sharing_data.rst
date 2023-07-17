.. _federation_user_tutorial:

Sharing Data with Other Databases
=================================

.. note::

  This tutorial assumes that an administrator has already :ref:`configured another database <federation>` for your SampleDB instance.

SampleDB instances are versatile and can be configured to represent most internal workflows. However, you may need to share data with others, who do not use the same SampleDB instance. In these cases, these instances can be connected to form a **Federation**. A federation consists of several SampleDB instances and does not require each instance to be connected to each other instance. If this feature is enabled for a SampleDB instance, you can navigate to *More* ➜ *Other Databases* to view a list of connected instances and a graph of the federation.

.. figure:: ../static/img/generated/federation_graph.png
    :alt: A federation graph

    A federation graph

If the SampleDB instance in question is connected, you can share **Objects** with other users and/or groups as part of the permissions system. When you edit the permissions of an object, then there is a section labeled *other databases* below the regular permissions table and forms, with a form to add permissions for a different SampleDB instance. If user information from that instance is known, you may be able to select a user you wish to grant permissions to. You can enter a user ID, a basic group ID, or a project group ID otherwise.

.. figure:: ../static/img/generated/federation_permissions.png
    :alt: Granting permissions to users or groups from another SampleDB instance

    Granting permissions to users or groups from another SampleDB instance

After clicking on *Add* next to the user or group field, you are able to select the desired permissions level. At this time, shared objects are **read-only** in the instance they are shared with, but in addition to granting *READ* permissions it is still possible to grant *WRITE* or *GRANT* permissions. *READ* permission will allow the user to view and reference the object, *WRITE* permissions include *READ* permissions but do not yet allow anything beyond that and *GRANT* permissions, which include both *READ* and *WRITE* permissions, allow the user to also grant permissions to other users in their SampleDB instance.

After saving these permissions by clicking on *Add* below the form, the object will be shared initially. As no constant connection is required, this may fail at this time and you may be informed about the failure. If it fails initially, the object will be shared the next time the two SampleDB instances exchange information, so no further action is required. After this initial sharing, any updates to the object will also be shared **automatically** without having to edit the permissions again.

As part of object information, references to users will be shared, e.g. for the creator of an object or the author of a comment. By default, no information beyond the ID will be shared. You can define a user alias by clicking on your name at the top right and then on *User Alias Settings* or by visiting the page for a specific other database (via *More* ➜ *Other Databases*). There you can either configure an alias to copy information from your user profile or fill out the information to be shared manually.

.. figure:: ../static/img/generated/federation_user_alias.png
    :alt: Creating a user alias for another SampleDB instance

    Creating a user alias for another SampleDB instance

.. admonition:: Summary

  - Several instances of SampleDB can be connected to form a Federation.
  - You can share objects with users or groups in other SampleDB instances.
  - Objects shared by other instances are read-only.
  - Updates to objects already shared to other instances will be shared automatically.
  - User information will only be shared if enabled by the user.

..  seealso::

  - :ref:`federation`
  - :ref:`permissions_tutorial`
