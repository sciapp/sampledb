.. _http_api:

HTTP API
========

Authentication
--------------

The |service_name| HTTP API either uses `Basic Authentication <https://tools.ietf.org/html/rfc7617>`_ using normal user credentials (e.g. using the header :code:`Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=`) or `Bearer Authentication <https://tools.ietf.org/html/rfc6750>`_ using the API token (e.g. using the header :code:`Authorization: Bearer bf4e16afa966f19b92f5e63062bd599e5f931faeeb604bdc3e6189539258b155`). API tokens are meant as an alternative method for authentication for individual scripts and allow you to monitor the requests made with the token. You can create an API token when editing your :ref:`preferences`.

Please make sure to use HTTPS when accessing the API.

Objects
-------

Reading a list of all objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/

    Get a list of all objects visible to the current user.

    The list only contains the current version of each object. By passing the parameter :code:`q` to the query, the :ref:`advanced_search` can be used. By passing the parameters :code:`action_id` or :code:`action_type` objects can be filtered by the action they were created with or by their type (e.g. :code:`sample` or :code:`measurement`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "object_id": 1,
                "version_id": 0,
                "action_id": 0,
                "schema": {
                    "title": "Object Information",
                    "type": "object",
                    "properties": {
                        "name": {
                            "title": "Object Name",
                            "type": "text"
                        }
                    }
                },
                "data": {
                    "name": {
                        "_type": "text",
                        "text": "Example Object"
                    }
                }
            },
            {
                "object_id": 2,
                "version_id": 3,
                "action_id": 0,
                "schema": {
                    "title": "Object Information",
                    "type": "object",
                    "properties": {
                        "name": {
                            "title": "Object Name",
                            "type": "text"
                        }
                    }
                },
                "data": {
                    "name": {
                        "_type": "text",
                        "text": "Other Object"
                    }
                }
            }
        ]

    :statuscode 200: no error


Getting the current object version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)

    Redirect to the current version of an object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 302 Found
        Location: /api/v1/objects/1/versions/0

    :statuscode 302: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Reading an object version
^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/versions/(int:version_id)

    Get the specific version (`version_id`) of an object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/versions/0 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "object_id": 1,
            "version_id": 0,
            "action_id": 0,
            "schema": {
                "title": "Object Information",
                "type": "object",
                "properties": {
                    "name": {
                        "title": "Object Name",
                        "type": "text"
                    }
                }
            },
            "data": {
                "name": {
                    "_type": "text",
                    "text": "Example Object"
                }
            }
        }

    :>json number object_id: the object's ID
    :>json number version_id: the object version's ID
    :>json number action_id: the action's ID
    :>json object schema: the object's schema
    :>json object data: the object's data
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object/version combination does not exist


Creating a new object
^^^^^^^^^^^^^^^^^^^^^

.. http:post:: /api/v1/objects/

    Create a new object.

    **Example request**:

    .. sourcecode:: http

        POST /api/v1/objects/1/versions/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Content-Type: application/json
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        {
            "action_id": 0,
            "schema": {
                "title": "Object Information",
                "type": "object",
                "properties": {
                    "name": {
                        "title": "Object Name",
                        "type": "text"
                    }
                }
            },
            "data": {
                "name": {
                    "_type": "text",
                    "text": "Example Object"
                }
            }
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json
        Location: /api/v1/objects/1/versions/0

    :<json number version_id: the object version's ID (optional, must be 0)
    :<json number action_id: the action's ID
    :<json object schema: the object's schema (optional, must equal current action's schema)
    :<json object data: the object's data
    :statuscode 201: no error
    :statuscode 400: invalid data


Updating an object / Creating a new object version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:post:: /api/v1/objects/(int:object_id)/versions/

    Create a new version of an object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        POST /api/v1/objects/1/versions/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Content-Type: application/json
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        {
            "data": {
                "name": {
                    "_type": "text",
                    "text": "Example Object"
                }
            }
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json
        Location: /api/v1/objects/1/versions/1

    :<json number object_id: the object's ID (optional, must equal `object_id` in URL)
    :<json number version_id: the object version's ID (optional, must equal new version's ID)
    :<json number action_id: the action's ID (optional, must equal previous `action_id`)
    :<json object schema: the object's schema (optional, must equal previous `schema` or current action's schema)
    :<json object data: the object's data
    :statuscode 201: no error
    :statuscode 400: invalid data
    :statuscode 403: the user does not have WRITE permissions for this object
    :statuscode 404: the object does not exist


Object Permissions
------------------


Reading whether an object is public
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/public

    Get whether or not an object is public.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/permissions/public HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        true

    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Setting whether an object is public
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/v1/objects/(int:object_id)/permissions/public

    Get whether or not an object is public.

    **Example request**:

    .. sourcecode:: http

        PUT /api/v1/objects/1/permissions/public HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        false

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        false

    :statuscode 200: no error
    :statuscode 403: the user does not have GRANT permissions for this object
    :statuscode 404: the object does not exist


Reading all users' permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/users/

    Get a mapping of user IDs to their permissions.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/permissions/users/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "1": "read",
            "2": "grant"
        }

    :queryparam include_instrument_responsible_users: If given, permissions from being an instrument responsible user will be included (optional)
    :queryparam include_groups: If given, permissions from group memberships will be included (optional)
    :queryparam include_projects: If given, permissions from project memberships will be included (optional)
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Reading a user's permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/users/(int:user_id)

    Get the permissions of a user for an object.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/permissions/users/2 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        "grant"

    :queryparam include_instrument_responsible_users: If given, permissions from being an instrument responsible user will be included (optional)
    :queryparam include_groups: If given, permissions from group memberships will be included (optional)
    :queryparam include_projects: If given, permissions from project memberships will be included (optional)
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object or user does not exist


Setting a user's permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/v1/objects/(int:object_id)/permissions/users/(int:user_id)

    Set the permissions of a user for an object.

    **Example request**:

    .. sourcecode:: http

        PUT /api/v1/objects/1/permissions/users/2 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        "write"

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        "write"

    :statuscode 200: no error
    :statuscode 400: invalid data (should be "read", "write", "grant" or "none")
    :statuscode 403: the user does not have GRANT permissions for this object
    :statuscode 404: the object or user does not exist


Reading all groups' permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/groups/

    Get a mapping of group IDs to their permissions.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/permissions/groups/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "4": "write"
        }

    :queryparam include_projects: If given, permissions from project memberships will be included (optional)
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Reading a group's permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/groups/(int:group_id)

    Get the permissions of a group for an object.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/permissions/groups/4 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        "write"

    :queryparam include_projects: If given, permissions from project memberships will be included (optional)
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object or group does not exist


Setting a group's permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/v1/objects/(int:object_id)/permissions/groups/(int:group_id)

    Set the permissions of a group for an object.

    **Example request**:

    .. sourcecode:: http

        PUT /api/v1/objects/1/permissions/groups/2 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        "read"

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        "read"

    :statuscode 200: no error
    :statuscode 400: invalid data (should be "read", "write", "grant" or "none")
    :statuscode 403: the user does not have GRANT permissions for this object
    :statuscode 404: the object or group does not exist


Reading all projects' permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/projects/

    Get a mapping of project IDs to their permissions.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/permissions/projects/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "7": "read"
        }

    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Reading a project's permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/projects/(int:project_id)

    Get the permissions of a project for an object.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/permissions/projects/7 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        "read"

    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object or project does not exist


Setting a project's permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/v1/objects/(int:object_id)/permissions/projects/(int:project_id)

    Set the permissions of a project for an object.

    **Example request**:

    .. sourcecode:: http

        PUT /api/v1/objects/1/permissions/projects/2 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        "read"

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        "read"

    :statuscode 200: no error
    :statuscode 400: invalid data (should be "read", "write", "grant" or "none")
    :statuscode 403: the user does not have GRANT permissions for this object
    :statuscode 404: the object or project does not exist


Instruments
-----------


Reading a list of all instruments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/instruments/

    Get a list of all instruments.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/instruments/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "instrument_id": 1,
                "name": "Example Instrument",
                "description": "This is an example instrument",
                "is_hidden": false,
                "instrument_scientists": [1, 42]
            }
        ]

    :statuscode 200: no error


Reading an instrument
^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/instruments/(int:instrument_id)

    Get the specific instrument (`instrument_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/instruments/1 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "instrument_id": 1,
            "name": "Example Instrument",
            "description": "This is an example instrument",
            "is_hidden": false,
            "instrument_scientists": [1, 42]
        }

    :>json number instrument_id: the instrument's ID
    :>json string name: the instruments's name
    :>json string description: the instruments's description
    :>json bool is_hidden: whether or not the instrument is hidden
    :>json list instrument_scientists: the instrument scientists' IDs
    :statuscode 200: no error
    :statuscode 404: the instrument does not exist


Instrument Log Entries
----------------------

Reading a list of all log entries for an instrument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/instruments/(int:instrument_id)/log_entries/

    Get a list of all log entries for a specific instrument (`instrument_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/instruments/1/log_entries HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "log_entry_id": 1,
                "utc_datetime": "2020-08-19T12:13:14.123456",
                "author": 1,
                "content": "Example Log Entry 1",
                "categories": []
            },
            {
                "log_entry_id": 2,
                "utc_datetime": "2020-08-19T13:14:15.123456",
                "author": 1,
                "content": "Example Log Entry 2",
                "categories": [
                    {
                        "category_id": 1
                        "title": "Error Report"
                    },
                    {
                        "category_id": 7
                        "title": "Maintenance Log"
                    }
                ]
            }
        ]

    :statuscode 200: no error
    :statuscode 403: the instrument log can only be accessed by instrument scientists
    :statuscode 404: the instrument does not exist


Reading an instrument log entry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/instruments/(int:instrument_id)/log_entries/(int:log_entry_id)

    Get the specific log entry (`log_entry_id`) for an instrument (`instrument_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/instruments/1/log_entries/2 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "log_entry_id": 2,
            "utc_datetime": "2020-08-19T13:14:15.123456",
            "author": 1,
            "content": "Example Log Entry 2",
            "categories": [
                {
                    "category_id": 1
                    "title": "Error Report"
                },
                {
                    "category_id": 7
                    "title": "Maintenance Log"
                }
            ]
        }

    :>json number log_entry_id: the log entry's ID
    :>json string utc_datetime: the date and time of the log entry in UTC in ISO format
    :>json string content: the log entry's content
    :>json number author: the user ID of the log entry's author
    :>json list categories: the log entry's categories
    :statuscode 200: no error
    :statuscode 403: the instrument log can only be accessed by instrument scientists
    :statuscode 404: the instrument or the log entry do not exist


Reading a list of all log categories for an instrument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/instruments/(int:instrument_id)/log_categories/

    Get a list of all log categories for a specific instrument (`instrument_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/instruments/1/log_categories HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "category_id": 1
                "title": "Error Report"
            },
            {
                "category_id": 7
                "title": "Maintenance Log"
            }
        ]

    :statuscode 200: no error
    :statuscode 403: the instrument log can only be accessed by instrument scientists
    :statuscode 404: the instrument does not exist


Reading an instrument log category
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/instruments/(int:instrument_id)/log_categories/(int:category_id)

    Get the specific log category (`category_id`) for an instrument (`instrument_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/instruments/1/log_categories/7 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "category_id": 7
            "title": "Maintenance Log"
        }

    :>json number category_id: the log category's ID
    :>json string title: the log category's title
    :statuscode 200: no error
    :statuscode 403: the instrument log can only be accessed by instrument scientists
    :statuscode 404: the instrument or the log category do not exist


Reading a list of all file attachments for a log entry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/instruments/(int:instrument_id)/log_entries/(int:log_entry_id)/file_attachments/

    Get a list of file attachments for a specific log entry (`log_entry_id`) for an instrument (`instrument_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/instruments/1/log_entries/2/file_attachments HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "file_attachment_id": 1,
                "file_name": "example.txt",
                "content": "RXhhbXBsZSBDb250ZW50"
            }
        ]

    :statuscode 200: no error
    :statuscode 403: the instrument log can only be accessed by instrument scientists
    :statuscode 404: the instrument or the log entry do not exist


Reading a file attachment for a log entry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/instruments/(int:instrument_id)/log_entries/(int:log_entry_id)/file_attachments/(int:file_attachment_id)

    Get a specific file attachment (`file_attachment_id`) for a log entry (`log_entry_id`) for an instrument (`instrument_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/instruments/1/log_entries/2/file_attachments/1 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "file_attachment_id": 1,
            "file_name": "example.txt",
            "content": "RXhhbXBsZSBDb250ZW50"
        }

    :>json string file_attachment_id: the file attachment's ID
    :>json string file_name: the original file name
    :>json string content: the base64 encoded file content
    :statuscode 200: no error
    :statuscode 403: the instrument log can only be accessed by instrument scientists
    :statuscode 404: the instrument, the log entry or the file attachment do not exist


Reading a list of all object attachments for a log entry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/instruments/(int:instrument_id)/log_entries/(int:log_entry_id)/object_attachments/

    Get a list of object attachments for a specific log entry (`log_entry_id`) for an instrument (`instrument_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/instruments/1/log_entries/2/object_attachments HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "object_attachment_id": 1,
                "object_id": 1
            }
        ]

    :statuscode 200: no error
    :statuscode 403: the instrument log can only be accessed by instrument scientists
    :statuscode 404: the instrument or the log entry do not exist


Reading an object attachment for a log entry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/instruments/(int:instrument_id)/log_entries/(int:log_entry_id)/object_attachments/(int:object_attachment_id)

    Get a specific object attachment (`object_attachment_id`) for a log entry (`log_entry_id`) for an instrument (`instrument_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/instruments/1/log_entries/2/object_attachments/1 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "object_attachment_id": 1,
            "object_id": 1
        }

    :>json string object_attachment_id: the object attachment's ID
    :>json string object_id: the object ID
    :statuscode 200: no error
    :statuscode 403: the instrument log can only be accessed by instrument scientists
    :statuscode 404: the instrument, the log entry or the object attachment do not exist


Creating an instrument log entry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:post:: /api/v1/instruments/(int:instrument_id)/log_entries/

    Create a log entry for an instrument (`instrument_id`) and optionally attach files and objects to it.

    **Example request**:

    .. sourcecode:: http

        POST /api/v1/instruments/1/log_entries/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        {
            "content": "Example Log Entry Text",
            "category_ids": [1, 7],
            "file_attachments": [
                {
                    "file_name": "example.txt",
                    "base64_content": "RXhhbXBsZSBDb250ZW50"
                }
            ],
            "object_attachments": [
                {
                    "object_id": 1
                },
                {
                    "object_id": 2
                }
            ]
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json
        Location: https://iffsamples.fz-juelich.de/api/v1/instruments/1/log_entries/1

    :<json string content: the log entry's content
    :<json list category_ids: an optional list of category IDs for the log entry
    :<json list file_attachments: an optional list of file attachments as json objects with file_name and base64_content attributes
    :<json list object_attachments: an optional list of object attachments as json objects with an object_id attribute
    :statuscode 201: the log entry and optional attachments have been created successfully
    :statuscode 400: there was an error in the given json data
    :statuscode 403: only instrument scientists can write to the instrument log
    :statuscode 404: the instrument does not exist


Actions
-------


Reading a list of all actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/actions/

    Get a list of all actions.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/actions/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "action_id": 1,
                "instrument_id": null,
                "type": "sample",
                "type_id": -99,
                "name": "Example Sample Creation",
                "description": "This is an example action",
                "is_hidden": false,
                "schema": {
                    "title": "Example Sample",
                    "type": "object",
                    "properties": {
                        "name": {
                            "title": "Sample Name",
                            "type": "text"
                        }
                    },
                    "required": ["name"]
                }
            },
            {
                "action_id": 2,
                "instrument_id": 1,
                "type": "measurement",
                "type_id": -98,
                "name": "Example Measurement",
                "description": "This is an example action",
                "is_hidden": false,
                "schema": {
                    "title": "Example Measurement",
                    "type": "object",
                    "properties": {
                        "name": {
                            "title": "Measurement Name",
                            "type": "text"
                        }
                    },
                    "required": ["name"]
                }
            }
        ]

    :statuscode 200: no error


Reading an action
^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/actions/(int:action_id)

    Get the specific action (`action_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/actions/1 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "action_id": 1,
            "instrument_id": null,
            "type": "sample",
            "type_id": -99,
            "name": "Example Sample Creation",
            "description": "This is an example action",
            "is_hidden": false,
            "schema": {
                "title": "Example Sample",
                "type": "object",
                "properties": {
                    "name": {
                        "title": "Sample Name",
                        "type": "text"
                    }
                },
                "required": ["name"]
            }
        }

    :>json number action_id: the action's ID
    :>json number instrument_id: the actions's instrument's ID or null
    :>json string type: the action's type ("sample", "measurement", "simulation" or "custom")
    :>json number type_id: the ID of the action's type
    :>json string name: the actions's name
    :>json string description: the actions's description
    :>json bool is_hidden: whether or not the action is hidden
    :>json object schema: the actions's schema
    :statuscode 200: no error
    :statuscode 404: the action does not exist


Action Types
------------


Reading a list of all action types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/action_types/

    Get a list of all action types.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/action_types/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "type_id": -99,
                "name": "Sample Creation",
                "object_name": "sample",
                "admin_only": false
            },
            {
                "type_id": -98,
                "name": "Measurement",
                "object_name": "measurement",
                "admin_only": false
            },
            {
                "type_id": -97,
                "name": "Simulation",
                "object_name": "simulation",
                "admin_only": false
            }
        ]

    :statuscode 200: no error


Reading an action type
^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/action_types/(int:type_id)

    Get the specific action type (`type_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/action_types/-99 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "type_id": -99,
            "name": "Sample Creation",
            "object_name": "sample",
            "admin_only": false
        }

    :>json number type_id: the action type's ID
    :>json string name: the action type's name
    :>json string object_name: the name of objects created with this action type
    :>json bool admin_only: whether or not actions with this type can only be created by administrators
    :statuscode 200: no error
    :statuscode 404: the action does not exist


Users
-----


Reading a list of all users
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/users/

    Get a list of all users.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/users/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "user_id": 1,
                "name": "Example User"
            }
        ]

    :statuscode 200: no error


Reading a user
^^^^^^^^^^^^^^

.. http:get:: /api/v1/users/(int:user_id)

    Get the specific user (`user_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/users/1 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "user_id": 1,
            "name": "Example User"
        }

    :>json number user_id: the user's ID
    :>json string name: the user's name
    :statuscode 200: no error
    :statuscode 404: the user does not exist


Reading the current user
^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/users/me

    Get the current user.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/users/me HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "user_id": 1,
            "name": "Example User"
        }

    :>json number user_id: the user's ID
    :>json string name: the user's name
    :statuscode 200: no error


Locations
---------


Reading a list of all locations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/locations/

    Get a list of all locations.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/locations/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "location_id": 1,
                "name": "Example Location",
                "description": "This is an example location",
                "parent_location_id": null
            }
        ]

    :statuscode 200: no error


Reading a location
^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/locations/(int:location_id)

    Get the specific location (`location_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/locations/1 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "location_id": 1,
            "name": "Example Location",
            "description": "This is an example location",
            "parent_location_id": null
        }

    :>json number location_id: the location's ID
    :>json string name: the locations's name
    :>json string description: the locations's description
    :>json number parent_location_id: the parent location's ID
    :statuscode 200: no error
    :statuscode 404: the location does not exist


Reading a list of an object's locations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/locations/

    Get a list of all object locations assignments for a specific object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/locations/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "object_id": 1,
                "location_id": 3,
                "responsible_user_id": 6,
                "user_id": 17,
                "description": "Shelf C",
                "utc_datetime": "2018-12-11 17:50:00"
            }
        ]

    :statuscode 200: no error


Reading an object's location
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/locations/(int:index)

    Get a specific object location assignment (`index`) for a specific object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/locations/0 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "object_id": 1,
            "location_id": 3,
            "responsible_user_id": 6,
            "user_id": 17,
            "description": "Shelf C",
            "utc_datetime": "2018-12-11 17:50:00"
        }

    :>json number object_id: the object's ID
    :>json number location_id: the location's ID
    :>json number responsible_user_id: the ID of the user who is responsible for the object
    :>json number user_id: the ID of the user who assigned this location to the object
    :>json string description: the description of the object's position
    :>json number utc_datetime: the datetime when the object was stored
    :statuscode 200: no error
    :statuscode 404: the object or the object location assignment does not exist


Files
-----


Reading a list of an object's files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/files/

    Get a list of all files for a specific object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/files/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "object_id": 1,
                "file_id": 0,
                "storage": "url",
                "url": "https://iffsamples.fz-juelich.de"
            }
        ]

    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Reading information for a file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/files/(int:file_id)

    Get a specific file (`file_id`) for a specific object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/files/0 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "object_id": 1,
            "file_id": 0,
            "storage": "url",
            "url": "https://iffsamples.fz-juelich.de"
        }

    :>json number object_id: the object's ID
    :>json number file_id: the file's ID
    :>json string storage: how the file is stored (local or url)
    :>json string url: the URL of the file (for url storage)
    :>json string original_file_name: the original name of the file (for local storage)
    :>json string base64_content: the base64 encoded content of the file (for local storage)
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object or the file does not exist


Uploading a file
^^^^^^^^^^^^^^^^

.. http:post:: /api/v1/objects/(int:object_id)/files/

    Create a new file with local storage for a specific object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        POST /api/v1/objects/1/files/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        {
            "storage": "local",
            "original_file_name": "test.txt",
            "base64_content": "dGVzdA=="
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json
        Location: https://iffsamples.fz-juelich.de/api/v1/objects/1/files/0

    :<json string storage: how the file is stored (local)
    :<json string original_file_name: the original name of the file
    :<json string base64_content: the base64 encoded content of the file
    :statuscode 201: the file has been created successfully
    :statuscode 403: the user does not have WRITE permissions for this object
    :statuscode 404: the object does not exist


Posting a link
^^^^^^^^^^^^^^

.. http:post:: /api/v1/objects/(int:object_id)/files/

    Create a new file with url storage for a specific object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        POST /api/v1/objects/1/files/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        {
            "storage": "url",
            "url": "https://iffsamples.fz-juelich.de"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json
        Location: https://iffsamples.fz-juelich.de/api/v1/objects/1/files/0

    :<json string storage: how the file is stored (url)
    :<json string url: the URL of the file
    :statuscode 201: the file has been created successfully
    :statuscode 403: the user does not have WRITE permissions for this object
    :statuscode 404: the object does not exist
