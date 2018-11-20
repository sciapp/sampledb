.. _object_permissions:

Object Permissions
==================

By default, samples, measurements and simulations are visible only to the user who created them and to the instrument scientists of the instrument the objects were created with. Additionally, administrators of iffSamples have access to the database the information is stored in. Object permissions can be used to share access to these objects with other users, groups or projects.

The object permissions built into iffSamples fall into three categories:

- **Read**: The permission to **view objects** and their properties, files and comments.
- **Write**: The permission to **edit objects** and their properties and add files and comments.
- **Grant**: The permission to **grant permissions** to other users.

Each of these categories is built on top of the other, with **Write** permissions including **Read** permissions and **Grant** permissions including **Write** permissions.

.. figure:: static/img/generated/object_permissions.png
    :scale: 50 %
    :alt: Object Permissions

    Object Permissions

To modify the permissions of an object, any user with **Grant** permissions can click the **Edit permissions** button on the object's page. They can then view the existing permissions, modify them or add new permissions for users, groups or projects.

Default Permissions
-------------------

When an object is created, its creator, any associated instrument scientists and the administrators will have **Grant** permissions. They can then allow other users to access the data by granting them permissions. To make these more convenient, each user has a set of **default permissions** set in the :ref:`preferences`, which will be applied to all objects they create in the future.

.. figure:: static/img/generated/default_permissions.png
    :scale: 50 %
    :alt: Default Permissions
   
    Default Permissions in the User Preferences


