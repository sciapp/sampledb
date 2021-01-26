.. _groups:

Basic Groups
============

Basic Groups are one of the two ways for organizing :ref:`users` in |service_name|. For :ref:`Object Permissions <permissions>`, a basic group acts as a single entity with all members of the group sharing any permissions granted to it.

Users can be members of any number of basic groups, leave the basic groups they are in or invite other users. Any member of a basic group can remove other members or delete the basic group as a whole.

As all users in a basic group are equal, basic groups may be best suited for those who want to freely share objects with their colleagues without fine-grained permissions. For a more detailed or hierarchical approach, see :ref:`projects`.

.. note::
    Administrators can disable creation of basic groups by regular users.

.. note::
    Basic Groups were formerly known only as groups. The name was changed along with the renaming of :ref:`projects`.

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
