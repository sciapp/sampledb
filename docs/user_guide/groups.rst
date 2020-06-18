.. _groups:

Groups
======

Groups are one of the two ways for organizing :ref:`users` in |service_name|. For :ref:`Object Permissions <permissions>`, a group acts as a single entity with all members of the group sharing any permissions granted to it.

Users can be members of any number of groups, leave the groups they are in or invite other users. Any member of a group can remove other members or delete the group as a whole.

As all users in a group are equal, groups may be best suited for those who want to freely share objects with their colleagues without fine-grained permissions. For a more detailed or hierarchical approach, see :ref:`projects`.

.. list-table:: Comparing Groups and Projects
   :header-rows: 1

   * - Feature
     - Groups
     - Projects
   * - Members
     - Users
     - Users and Groups
   * - Hierarchy
     - Flat
     - Nested, Projects can contain Subprojects
   * - Object Permissions
     - All members get the Object Permissions granted to the Group
     - Each Project member has a permissions level (**Read**/**Write**/**Grant**) for the Project and will get Object Permissions granted to the Project up to that level
   * - Member Invitation
     - Any Group member can invite new members
     - Project members with **Grant** permissions can invite new members


