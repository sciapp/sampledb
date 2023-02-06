.. _locations:

Locations
---------

Locations represent physical locations, such as buildings, rooms, shelves and containers. As such, these locations can form a hierarchy:

.. figure:: ../static/img/generated/locations.png
    :alt: Locations

    Locations

Location Types
^^^^^^^^^^^^^^

Some features may be useful for some locations while not useful for others, e.g. it might be reasonable to store an object in a room but not in a building. Administrators can configure this using different location types. By default, only one generic location type exists and administrators can create and configure additional location types to fit their use case.

Location Permissions
^^^^^^^^^^^^^^^^^^^^

All users can create locations, unless all location types have been restricted to administrators or the ``ONLY_ADMINS_CAN_MANAGE_LOCATIONS`` :ref:`configuration variable <configuration>` has been set. When a location is created, the user can decide if it should be public or not. Public locations allow all users to view and edit the location. In contrast, non-public locations have permissions set for different users, similar to object and action permissions.

Location Log
^^^^^^^^^^^^

If enabled for the location type, the location log can show a list of events relevant to the individual location, such as when it was created or updated and when objects were assigned to it.

Storage Capacities
^^^^^^^^^^^^^^^^^^

If enabled for the location type, locations can have a maximum capacity for the amount of objects that can be stored there. Users can set this number or set it to be unlimited to allow an arbitrary amount of objects of that action type to be stored at the location.
