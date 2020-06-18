.. _projects:

Projects
========

Projects are one of the two ways for organizing :ref:`users` in |service_name|. For :ref:`Object Permissions <permissions>`, a project acts as a single entity with members of the project sharing the permissions granted to it up to the permissions they have for the project itself.

Users can be members of any number of projects, leave the projects they are in or invite other users if they have **GRANT** permissions for the project. Members with **GRANT** permissions can also remove other members or delete the project as a whole.

A project can be a subproject of another, sharing the parent project's permissions with the members of the subproject.

Projects may be best suited for those who want to model their object permissions in |service_name| according to an organizational hierarchy. For a simpler approach, see :ref:`groups`.

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
