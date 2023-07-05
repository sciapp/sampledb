.. _permissions_tutorial:

Managing Object Permissions
===========================

Three permission levels control what users can do with objects in SampleDB:

- **READ** allows viewing objects and their metadata, files, comments, etc.
- **WRITE** allows editing object metadata, adding files, posting comments, etc.
- **GRANT** allows granting permissions to other users or groups.

Each of these includes the previous one, with **WRITE** permissions including **READ** permissions and **GRANT** permissions including **WRITE** (and therefore also **READ**) permissions.

If you have **GRANT** permissions for an object, you can click the *Edit permissions* button on that object's page to edit the object's permissions. You can then control the permissions for **users** and **groups**.

.. figure:: ../static/img/generated/object_permissions2.png
    :alt: Object Permissions

    Object Permissions

**Special groups** such as administrators and instrument scientists (for objects created with an instrument) automatically have **GRANT** permissions. You can also grant **READ** permissions to all signed-in users and, if enabled by the administrator, to anonymous users.

When creating an object, **default permissions** configured in your preferences will be applied, unless you choose to grant permissions to a specific group or to copy permissions from another object.

.. figure:: ../static/img/generated/default_permissions.png
    :alt: Default Permissions in the User Preferences

    Default Permissions in the User Preferences

.. admonition:: Summary

  - Users can have **READ**, **WRITE**, or **GRANT** permissions for an object.
  - Each level of permissions includes the one before.
  - Permissions can be granted directly to users or groups.
  - Special groups such as instrument scientists and administrators automatically have permissions.
  - Default permissions are applied when creating a new object.

..  seealso::

  - :ref:`permissions`
  - :ref:`federation_user_tutorial`
