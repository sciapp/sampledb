.. _http_api:

HTTP API
========

The SampleDB HTTP API makes it possible to use HTTP requests to perform most actions that can be done via the web frontend. This can be very useful for automated data entry, e.g. for uploading metadata from instrument control software, and retrieval, e.g. for data analysis.

There are libraries for sending HTTP requests for most programming languages, and users of Python or Matlab can use the `sampledbapi <https://ag-salinga.zivgitlabpages.uni-muenster.de/sampledb-api-wrapper/index.html>`_ package `developed at WWU Münster <https://github.com/AG-Salinga/sampledb-api-wrapper>`_ for even simpler use of the HTTP API.

Authentication
--------------

The |service_name| HTTP API either uses `Basic Authentication <https://tools.ietf.org/html/rfc7617>`_ using normal user credentials (e.g. using the header :code:`Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=`) or `Bearer Authentication <https://tools.ietf.org/html/rfc6750>`_ using the API token (e.g. using the header :code:`Authorization: Bearer bf4e16afa966f19b92f5e63062bd599e5f931faeeb604bdc3e6189539258b155`). API tokens are meant as an alternative method for authentication for individual scripts and allow you to monitor the requests made with the token. You can create an API token when editing your :ref:`preferences`. If you have a two factor authentication method enabled, you cannot use your user credentials to use the API and will have to use an API token instead.

You can use these authentication methods to create a short-lived :ref:`access token <access_tokens>`, along with a refresh token to generate new access tokens.

Please make sure to use HTTPS when accessing the API.

Objects
-------

Reading a list of all objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/

    Get a list of all objects visible to the current user.

    The list only contains the current version of each object. By passing the parameter :code:`q` to the query, the :ref:`advanced_search` can be used. By passing the parameters :code:`action_id` or :code:`action_type` objects can be filtered by the action they were created with or by their type (e.g. :code:`sample` or :code:`measurement`).

    Instead of returning all objects, the parameters :code:`limit` and :code:`offset` can be used to reduce to maximum number of objects returned and to provide an offset in the returned set, so allow simple pagination.

    If the parameter :code:`name_only` is provided, the object data and schema will be reduced to the name property, omitting all other properties and schema information.

    If the parameter :code:`get_referencing_objects` is provided, the object data include referencing object IDs.

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
            "user_id": 1,
            "utc_datetime": "2021-04-29 12:34:56",
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
    :>json object action: the action (if the parameter embed_action is set to a non-empty value)
    :>json number user_id: the ID of the user who created this version
    :>json object user: the user (if the parameter embed_user is set to a non-empty value)
    :>json string utc_datetime: the time and date when this version was created in UTC
    :>json object schema: the object's schema
    :>json object data: the object's data
    :>json object data_diff: the :ref:`data difference <data_diffs>` between the specified and the previous version (if the parameter include_diff is set to a non-empty value)
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object/version combination does not exist


Creating a new object
^^^^^^^^^^^^^^^^^^^^^

.. http:post:: /api/v1/objects/

    Create a new object.

    **Example request**:

    .. sourcecode:: http

        POST /api/v1/objects/ HTTP/1.1
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


.. _api_post_object_version:

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
    :<json object data: the object's data (either `data` or `data_diff` must be set)
    :<json object data_diff: the :ref:`difference <data_diffs>` between the previous version and the new one (either `data` or `data_diff` must be set)
    :statuscode 201: no error
    :statuscode 400: invalid data
    :statuscode 403: the user does not have WRITE permissions for this object
    :statuscode 404: the object does not exist


Getting related object IDs
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/related_objects

    Gets object IDs related to an object (`object_id`).

    If an object ID refers to an object from `another database <federation>`_
    that does not exist in this instance of SampleDB, the `component_uuid`
    property contains the UUID of the source component. Otherwise, even if the
    object is originally from another database, `component_uuid` will be null.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/related_objects HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "referenced_objects": [
                {
                    "object_id:" 2,
                    "component_uuid": null
                },
                {
                    "object_id:" 1,
                    "component_uuid": "273e5cb7-6831-46f9-a774-1fe73c11977d"
                }
            ],
            "referencing_objects": [
                {
                    "object_id:" 3,
                    "component_uuid": null
                }
            ]
        }

    :>json array referenced_objects: the IDs of objects referenced by the metadata for this object
    :>json array referencing_objects: the IDs of objects referencing this object in their metadata
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Object Permissions
------------------


Reading whether an object is readable by all authenticated users
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/public

    Get whether or not an object is readable by all authenticated users.

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


Setting whether an object is readable by all authenticated users
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/v1/objects/(int:object_id)/permissions/public

    Set whether or not an object should be readable by all authenticated users.

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


Getting the permissions for all authenticated users
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/authenticated_users

    Get the permissions for an object for all authenticated users.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/permissions/authenticated_users HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        "none"

    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Setting the permissions for all authenticated users
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/v1/objects/(int:object_id)/permissions/authenticated_users

    Set the permissions for an object for all authenticated users.

    **Example request**:

    .. sourcecode:: http

        PUT /api/v1/objects/1/permissions/authenticated_users HTTP/1.1
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
    :statuscode 403: the user does not have GRANT permissions for this object
    :statuscode 404: the object does not exist


Getting the permissions for anonymous users
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/anonymous_users

    Get the permissions for an object for anonymous users, if anonymous users are enabled.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/permissions/anonymous_users HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        "none"

    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Setting the permissions for anonymous users
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/v1/objects/(int:object_id)/permissions/anonymous_users

    Set the permissions for an object for anonymous users, if anonymous users are enabled.

    **Example request**:

    .. sourcecode:: http

        PUT /api/v1/objects/1/permissions/anonymous_users HTTP/1.1
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
    :queryparam include_groups: If given, permissions from basic group memberships will be included (optional)
    :queryparam include_projects: If given, permissions from project group memberships will be included (optional)
    :queryparam include_admins: If given, permissions from being an administrator will be included (optional)
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
    :queryparam include_groups: If given, permissions from basic group memberships will be included (optional)
    :queryparam include_projects: If given, permissions from project group memberships will be included (optional)
    :queryparam include_admins: If given, permissions from being an administrator will be included (optional)
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


Reading all basic groups' permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/groups/

    Get a mapping of basic group IDs to their permissions.

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

    :queryparam include_projects: If given, permissions from project group memberships will be included (optional)
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Reading a basic group's permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/groups/(int:group_id)

    Get the permissions of a basic group for an object.

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

    :queryparam include_projects: If given, permissions from project group memberships will be included (optional)
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object or basic group does not exist


Setting a basic group's permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/v1/objects/(int:object_id)/permissions/groups/(int:group_id)

    Set the permissions of a basic group for an object.

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
    :statuscode 404: the object or basic group does not exist


Reading all project groups' permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/projects/

    Get a mapping of project group IDs to their permissions.

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


Reading a project group's permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/permissions/projects/(int:project_id)

    Get the permissions of a project group for an object.

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
    :statuscode 404: the object or project group does not exist


Setting a project group's permissions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/v1/objects/(int:object_id)/permissions/projects/(int:project_id)

    Set the permissions of a project group for an object.

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
    :statuscode 404: the object or project group does not exist


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
                "instrument_scientists": [1, 42],
                "location_id": null
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
            "instrument_scientists": [1, 42],
            "location_id": 1
        }

    :>json number instrument_id: the instrument's ID
    :>json string name: the instruments's name
    :>json string description: the instruments's description
    :>json bool is_hidden: whether or not the instrument is hidden
    :>json list instrument_scientists: the instrument scientists' IDs
    :>json number location_id: the instrument location's ID
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
                "event_utc_datetime": "2020-08-03T12:13:14.123456",
                "content_is_markdown": false
                "categories": []
            },
            {
                "log_entry_id": 2,
                "utc_datetime": "2020-08-19T13:14:15.123456",
                "author": 1,
                "content": "Example Log Entry 2",
                "event_utc_datetime": null,
                "content_is_markdown": false,
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
            "event_utc_datetime": "2020-08-03T12:13:14.123456",
            "content_is_markdown": false,
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
    :>json string event_utc_datetime: the date and time of the event in UTC in ISO format if set, else ``null``
    :>json string content_is_markdown: whether the log entry's content is markdown
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
                "user_id": null,
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
                "user_id": null,
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
            "user_id": null,
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
    :>json number instrument_id: the action's instrument's ID or null
    :>json number user_id: the action's user ID, if it is a user-specific action, or null
    :>json string type: the action's type ("sample", "measurement", "simulation" or "custom")
    :>json number type_id: the ID of the action's type
    :>json string name: the action's name
    :>json string description: the action's description
    :>json bool is_hidden: whether or not the action is hidden
    :>json object schema: the action's schema
    :statuscode 200: no error
    :statuscode 404: the action does not exist

Updating an action
^^^^^^^^^^^^^^^^^^

.. http:post:: /api/v1/actions/(int:action_id)

    Update the specific action (`action_id`).

    **Example request**:

    .. sourcecode:: http

        POST /api/v1/actions/1 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        {
            "action_id": 1,
            "instrument_id": null,
            "user_id": null,
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

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "action_id": 1,
            "instrument_id": null,
            "user_id": null,
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

    :<json string name: the action's name
    :<json string description: the action's description
    :<json bool is_hidden: whether or not the action is hidden
    :<json object schema: the action's schema
    :<json number action_id: the action's ID (optional, must not be changed)
    :<json number instrument_id: the action's instrument's ID or null (optional, must not be changed)
    :<json number user_id: the action's user ID, if it is a user-specific action, or null (optional, must not be changed)
    :<json string type: the action's type ("sample", "measurement", "simulation" or "custom", optional, must not be changed)
    :<json number type_id: the ID of the action's type (optional, must not be changed)
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
                "name": "Example User",
                "orcid": null,
                "affiliation": null,
                "role": null
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
            "name": "Example User",
            "orcid": null,
            "affiliation": null,
            "role": null
        }

    :>json number user_id: the user's ID
    :>json string name: the user's name
    :>json string orcid: the user's ORCid ID (optional)
    :>json string affiliation: the user's affiliation (optional)
    :>json string role: the user's role (optional)
    :>json string email: the user's email (only for API requests by administrators)
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
            "name": "Example User",
            "orcid": null,
            "affiliation": null,
            "role": null
        }

    :>json number user_id: the user's ID
    :>json string name: the user's name
    :>json string orcid: the user's ORCid ID (optional)
    :>json string affiliation: the user's affiliation (optional)
    :>json string role: the user's role (optional)
    :>json string email: the user's email (only for API requests by administrators)
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
                "parent_location_id": null,
                "type_id": -99,
                "is_hidden": false
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
            "parent_location_id": null,
            "type_id": -99,
            "is_hidden": false
        }

    :>json number location_id: the location's ID
    :>json string name: the locations's name
    :>json string description: the locations's description
    :>json number parent_location_id: the parent location's ID
    :>json number type_id: the location type's ID
    :>json bool is_hidden: whether or not the location is hidden
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this location
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


Location Types
--------------


Reading a list of all location types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/location_types/

    Get a list of all location types.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/location_types/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "location_type_id": 1,
                "name": "Example Location Type"
            }
        ]

    :statuscode 200: no error


Reading a location type
^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/location_types/(int:location_type_id)

    Get the specific location type (`location_type_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/location_types/1 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "location_type_id": 1,
            "name": "Example Location Type"
        }

    :>json number location_type_id: the location type's ID
    :>json string name: the location type's name
    :statuscode 200: no error
    :statuscode 404: the location type does not exist


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
    :>json string storage: how the file is stored (local, database or url)
    :>json string url: the URL of the file (for url storage)
    :>json string original_file_name: the original name of the file (for local or database storage)
    :>json string base64_content: the base64 encoded content of the file (for local or database storage)
    :>json object hash: hash algorithm and hexdigest of the content (optional, for local, database or local_reference storage)
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object or the file does not exist


Uploading a file
^^^^^^^^^^^^^^^^

.. http:post:: /api/v1/objects/(int:object_id)/files/

    Create a new file with database storage for a specific object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        POST /api/v1/objects/1/files/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        {
            "storage": "database",
            "original_file_name": "test.txt",
            "base64_content": "dGVzdA==",
            "hash": {
                "algorithm": "sha256",
                "hexdigest": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
            }
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json
        Location: https://iffsamples.fz-juelich.de/api/v1/objects/1/files/0

    :<json string storage: how the file is stored (either database or local_reference)
    :<json string original_file_name: the original name of the file
    :<json string base64_content: the base64 encoded content of the file
    :<json object hash: hash algorithm and hexdigest of the content (optional)
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

Comments
--------


Reading a list of an object's comments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/comments/

    Get a list of all comments for a specific object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/comments/ HTTP/1.1
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
                "user_id": 1,
                "comment_id": 0,
                "content": "This is an example comment"
                "utc_datetime": "2020-12-03T01:02:03.456789"
            }
        ]

    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object does not exist


Reading information for a comment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/objects/(int:object_id)/comments/(int:comment_id)

    Get a specific comment (`comment_id`) for a specific object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/objects/1/comments/0 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "object_id": 1,
            "user_id": 1,
            "comment_id": 0,
            "content": "This is an example comment"
            "utc_datetime": "2020-12-03T01:02:03.456789"
        }

    :>json number object_id: the object's ID
    :>json number user_id: the ID of the user who posted the comment
    :>json number comment_id: the comment's ID
    :>json string content: the comment's content
    :>json string utc_datetime: the time the comment was posted in UTC formatted in ISO 8601 format
    :statuscode 200: no error
    :statuscode 403: the user does not have READ permissions for this object
    :statuscode 404: the object or the comment does not exist


Posting a comment
^^^^^^^^^^^^^^^^^

.. http:post:: /api/v1/objects/(int:object_id)/comments/

    Create a new comment for a specific object (`object_id`).

    **Example request**:

    .. sourcecode:: http

        POST /api/v1/objects/1/comments/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        {
            "content": "This is an example comment"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json
        Location: https://iffsamples.fz-juelich.de/api/v1/objects/1/comments/0

    :<json string content: the (non-empty) content for the new comment
    :statuscode 201: the comment has been created successfully
    :statuscode 403: the user does not have WRITE permissions for this object
    :statuscode 404: the object does not exist

.. _data_diffs:

Object Data Diff Syntax
-----------------------

When :ref:`updating object data <api_post_object_version>`, instead of providing the full object data a diff can be provided instead. This is an alternative to downloading the current object version, performing the change locally and then uploading the data again, and can be useful in scripts, e.g. to update the status of an object.

The syntax for these diffs is specific to SampleDB data entries, but fairly simple:

- When comparing arrays, the diff is a list that contains the diff item by item, or ``null`` if the items are the same.
- When comparing objects, the diff is a dictionary mapping each key to the diff of the values, if they have changed.
- Otherwise, the diff is a dictionary mapping the key ``_before`` to the value before the change (if there was any data there before) and mapping the key ``_after`` to the value after the change (unless there is no value afterwards).

As an example, considering the following data before:

.. code-block:: json

    {
      "name": {
          "_type": "text",
          "text": {
              "en": "Example Measurement"
          }
      },
      "measurement_complete": {
          "_type": "bool",
          "value": false
      },
      "mass_list": [
        {
          "_type": "quantity",
          "magnitude": 10,
          "magnitude_in_base_units": 0.01,
          "units": "g",
          "dimensionality": "[mass]"
        }
      ]
    }

The following diff would add a value of 11g to ``mass_list`` and set ``measurement_complete`` to ``True``:

.. code-block:: json

    {
      "measurement_complete": {
        "_before": {
          "_type": "bool",
          "value": false
        },
        "_after": {
          "_type": "bool",
          "value": true
        }
      },
      "mass_list": [
        null,
        {
          "_after": {
            "_type": "quantity",
            "magnitude": 11,
            "magnitude_in_base_units": 0.011,
            "units": "g",
            "dimensionality": "[mass]"
          }
        }
      ]
    }

.. _access_tokens:

Access Tokens
-------------

In some situations, e.g. for interactive applications that use the API, users may want to authenticate with their username and password, but these should not be stored. In these situations, access tokens are a short-lived and more convenient alternative to having the users create API tokens. An access token can be used with Bearer authentication, just like an API token. After a given time this access token will expire automatically, so that there won't be any cleanup needed by the user. When creating an access token, the expiration date and time (in UTC) will be returned along with a refresh token, which can be used to create a new access token to avoid expiry, as long as the access token is needed.

.. http:post:: /api/v1/access_tokens/

    Create a new access token.

    **Example request**:

    .. sourcecode:: http

        POST /api/v1/access_tokens/ HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

        {
            "description": "Access Token for Instrument Control"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json

        {
            "access_token": "d0305fdf89d737dfa3062569022ef38be363b8fdf3d4137d26674809e34eac5a",
            "refresh_token": "b6f6d66d6ee92b4bc38857aabab793c2eb1e982941fa576b02b0535c280498c3",
            "expiration_utc_datetime": "2023-04-05 06:07:08"
            "description": "Access Token for Instrument Control"
        }

    :<json string description: a description for the access token
    :>json string access_token: the created access token
    :>json string refresh_token: the accompanying refresh token
    :>json string expiration_utc_datetime: the expiration date and time (in UTC)
    :>json string description: the given description
    :statuscode 201: the access token has been created successfully


.. _api_object_log_entries:

Object Log Entries
------------------


Reading the full accessible object log
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/object_log_entries/

    Get a list of all object log entries for objects with at least read permission.

    **Example request**:

    .. sourcecode:: http

        GET /api/v1/object_log_entries/?after_id=3514 HTTP/1.1
        Host: iffsamples.fz-juelich.de
        Accept: application/json
        Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        [
            {
                "log_entry_id": 3515,
                "type": "CREATE_OBJECT",
                "object_id": 163,
                "user_id": 12,
                "data": {},
                "utc_datetime": "2023-12-03 01:02:03"
            }
        ]

    :<json number after_id: only log entries created after the entry with the id ``after_id`` are returned (optional)
    :>json number log_entry_id: the log entry's ID
    :>json string type: the type of the log entry
    :>json number object_id: the ID of the object this log entry is related to
    :>json string user_id: the ID of the user by whose activity the log entry was created
    :>json string data: the data of the log entry, might be empty (``{}``)
    :>json string utc_datetime: the timestamp of the log entry in UTC in format %Y-%m-%d %H:%M:%S
    :statuscode 200: no error
