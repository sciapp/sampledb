.. _projects:

Project Groups
==============

Project Groups are one of the two ways for organizing :ref:`users` in |service_name|. For :ref:`Object Permissions <permissions>`, a project group acts as a single entity with members of the group sharing the permissions granted to it up to the permissions they have for the project group itself.

Users can be members of any number of project groups, leave the projects they are in or invite other users if they have **GRANT** permissions for the project group. Members with **GRANT** permissions can also remove other members or delete the project group as a whole.

A project group can contain :ref:`groups` as well as users, though it cannot contain other project groups. Instead, a parent-child relationship can be established between project groups, optionally allowing users with **GRANT** permissions in a child project group to invite other users to both the child and parent project groups.

Project groups may be best suited for those who want to model their object permissions in |service_name| according to an organizational hierarchy. For a simpler approach, see :ref:`groups`.

.. note::
    Administrators can disable creation of project groups by regular users. Administrators can also disable subproject support.

.. note::
    Project groups were formerly known only as projects. The name was changed to distinguish them from objects containing information about research projects.

.. list-table:: Comparing Basic and Project Groups
   :header-rows: 1

   * - Feature
     - Basic Groups
     - Project Groups
   * - Members
     - Users
     - Users and Basic Groups
   * - Hierarchy
     - Flat
     - Nested (Project Groups can have Child Project Groups)
   * - Object Permissions
     - All members get the Object Permissions granted to the Basic Group
     - Each Project Group member has a permissions level (**Read**/**Write**/**Grant**) for the Project Group and will get Object Permissions granted to the Project Group up to that level
   * - Member Invitation
     - Any member of a Basic Group can invite new members
     - Only members of a Project Group with **Grant** permissions can invite new members
