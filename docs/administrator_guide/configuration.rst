.. _configuration:

Configuration
=============

When running a SampleDB installation, you can set environment variables to configure it. The following sections will describe groups of such variables and their effects.

E-Mail
------

.. list-table:: E-Mail Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_CONTACT_EMAIL
     - An email address for users to contact
   * - SAMPLEDB_MAIL_SENDER
     - The email address used for outbound emails
   * - SAMPLEDB_MAIL_SERVER
     - The mail server used for outbound emails
   * - SAMPLEDB_MAIL_PORT
     - The port to use for connections to the mail server (default: ``25``)
   * - SAMPLEDB_MAIL_USE_TLS / SAMPLEDB_MAIL_USE_SSL
     - Whether to use TLS or SSL for connections to the mail server (default: ``False``)
   * - SAMPLEDB_MAIL_USERNAME
     - The username sent to the mail server
   * - SAMPLEDB_MAIL_PASSWORD
     - The password sent to the mail server

While the ``SAMPLEDB_CONTACT_EMAIL``, ``SAMPLEDB_MAIL_SENDER`` and ``SAMPLEDB_MAIL_SERVER`` variables are required, you may need to set one or more of the other variables to connect to your mail server, depending on its configuration.

.. _ldap_configuration:

LDAP
----

.. list-table:: LDAP Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_LDAP_NAME
     - The name of the LDAP server shown to the users
   * - SAMPLEDB_LDAP_SERVER
     - The ldaps-URL of the LDAP server
   * - SAMPLEDB_LDAP_USER_BASE_DN
     - The LDAP base DN to search users with
   * - SAMPLEDB_LDAP_UID_FILTER
     - The filter to use for identifying a user in LDAP as python template, e.g. ``(uid={})``
   * - SAMPLEDB_LDAP_NAME_ATTRIBUTE
     - The name of the attribute containing a user's name in LDAP, e.g. ``cn``
   * - SAMPLEDB_LDAP_MAIL_ATTRIBUTE
     - The name of the attribute containing a user's email address in LDAP, e.g. ``mail``
   * - SAMPLEDB_LDAP_OBJECT_DEF
     - The object def to use for looking up user attributes, e.g. inetOrgPerson
   * - SAMPLEDB_LDAP_USER_DN
     - The DN of an LDAP user to use when searching for other users
   * - SAMPLEDB_LDAP_PASSWORD
     - The password for the user identified by SAMPLEDB_LDAP_USER_DN
   * - SAMPLEDB_TESTING_LDAP_LOGIN
     - The uid of an LDAP user (only used during tests)
   * - SAMPLEDB_TESTING_LDAP_PW
     - The password for the ldap user identified by SAMPLEDB_TESTING_LDAP_LOGIN (only used during tests)

If you use LDAP for user management, you can use these variables to configure how SampleDB should connect to your LDAP server.


Customization
-------------

.. list-table:: Customization Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_SERVICE_NAME
     - The name of the service
   * - SAMPLEDB_SERVICE_DESCRIPTION
     - A short description of the service
   * - SAMPLEDB_SERVICE_IMPRINT
     - The URL to use for the imprint link
   * - SAMPLEDB_SERVICE_PRIVACY_POLICY
     - The URL to use for the privacy policy link
   * - SAMPLEDB_PDFEXPORT_LOGO_URL
     - A file, http or https URL for a PNG or JPEG logo to be included in object export PDF documents
   * - SAMPLEDB_PDFEXPORT_LOGO_ALIGNMENT
     - The alignment (left, center or right) of the logo, if SAMPLEDB_PDFEXPORT_LOGO_URL is set (default: right)
   * - SAMPLEDB_HELP_URL
     - The URL to use for the help link

You can use these variables to customize how your SampleDB instance is called, described and which links are included in the footer. The logo at the given PDFEXPORT_LOGO_URL will be fetched when SampleDB is started and cached afterwards. To refresh the logo, you will need to restart SampleDB.

.. _jupyterhub_configuration:

JupyterHub Support
------------------

.. list-table:: JupyterHub Support Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_JUPYTERHUB_NAME
     - The name of your JupyterHub server (default: ``JupyterHub``)
   * - SAMPLEDB_JUPYTERHUB_URL
     - The base URL of your JupyterHub server
   * - SAMPLEDB_JUPYTERHUB_TEMPLATES_URL
     - The URL of a Jupyter notebook templating server (default: SAMPLEDB_JUPYTERHUB_URL + ``/templates``, if SAMPLEDB_JUPYTERHUB_URL is set)

For more information on JupyterHub support and Jupyter notebook templates, see :ref:`jupyterhub_support`.

.. _dataverse_configuration:

Dataverse Export
----------------

.. list-table:: Dataverse Export Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_DATAVERSE_NAME
     - The name of the Dataverse server (default: ``Dataverse``)
   * - SAMPLEDB_DATAVERSE_URL
     - The base URL of the Dataverse server
   * - SAMPLEDB_DATAVERSE_ROOT_IDS
     - A comma seperated list of IDs of Dataverses, which objects may be exported to  (default: ``:root``)

For more information on the Dataverse export, see :ref:`dataverse_export`.

Administrator Account
---------------------

.. list-table:: Administrator Account Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_ADMIN_PASSWORD
     - The password for the admin account.
   * - SAMPLEDB_ADMIN_USERNAME
     - The username for the admin account (default: ``admin``)
   * - SAMPLEDB_ADMIN_EMAIL
     - The email address for the admin account (default: SAMPLEDB_CONTACT_EMAIL)


If no users exist yet and the ``SAMPLEDB_ADMIN_PASSWORD`` variable is set, a new user will be created with this password. This user will be a SampleDB admin. The username for this user will be set to value of ``SAMPLEDB_ADMIN_USERNAME`` and the email address for this user will be set to the value of ``SAMPLEDB_ADMIN_EMAIL``.

If another user already exists, these variables will have no effect. It is meant for creating an administrator account as part of the initial setup.

.. _federation_configuration:

Federation
----------

.. list-table:: Federation Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_FEDERATION_UUID
     - This instance's federation UUID. See :ref:`federation` for details
   * - SAMPLEDB_ALLOW_HTTP
     - If set, insecure communication to other databases via HTTP will be allowed.
   * - SAMPLEDB_VALID_TIME_DELTA
     - Valid time delta between SampleDB instances in a federation in seconds (default: ``300``)

Miscellaneous
-------------

.. list-table:: Miscellaneous Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_FILE_STORAGE_PATH
     - A path to the directory that uploaded files should be stored in
   * - SAMPLEDB_SERVER_NAME
     - The server name for Flask. See: https://flask.palletsprojects.com/en/1.1.x/config/#SERVER_NAME
   * - SAMPLEDB_SQLALCHEMY_DATABASE_URI
     - The database URI for SQLAlchemy. See: https://flask-sqlalchemy.palletsprojects.com/en/2.x/config/
   * - SAMPLEDB_SECRET_KEY
     - The secret key for Flask and Flask extensions. See: https://flask.palletsprojects.com/en/1.1.x/config/#SECRET_KEY
   * - SAMPLEDB_WTF_CSRF_TIME_LIMIT
     - The time limit for WTForms CSRF tokens in seconds. See: https://flask-wtf.readthedocs.io/en/stable/config.html
   * - SAMPLEDB_INVITATION_TIME_LIMIT
     - The time limit for invitation links in seconds.
   * - SAMPLEDB_ONLY_ADMINS_CAN_MANAGE_LOCATIONS
     - If set, only administrators will be able to create and edit locations.
   * - SAMPLEDB_ONLY_ADMINS_CAN_CREATE_GROUPS
     - If set, only administrators will be able to create basic groups.
   * - SAMPLEDB_ONLY_ADMINS_CAN_DELETE_GROUPS
     - If set, only administrators will be able to delete non-empty basic groups.
   * - SAMPLEDB_ONLY_ADMINS_CAN_CREATE_PROJECTS
     - If set, only administrators will be able to create project groups.
   * - SAMPLEDB_LOAD_OBJECTS_IN_BACKGROUND
     - If set, object selections will be loaded in the background using AJAX.
   * - SAMPLEDB_DISABLE_USE_IN_MEASUREMENT
     - If set, the "Use in Measurement" button will not be shown.
   * - SAMPLEDB_DISABLE_SUBPROJECTS
     - If set, project groups cannot have child project groups assigned to them.
   * - SAMPLEDB_ENFORCE_SPLIT_NAMES
     - If set, force names to be entered as "surname, given names". **Note:** this will prevent users with a mononym from setting their name correctly!
   * - SAMPLEDB_PYBABEL_PATH
     - The path to the pybabel executable (default: ``pybabel``)
   * - SAMPLEDB_EXTRA_USER_FIELDS
     - A JSON-encoded dict containing extra user fields, e.g. ``{"phone": {"name": {"en": "Phone No."}, "placeholder": {"en": "Phone No."}}}`` (default: ``{}``)
   * - SAMPLEDB_SHOW_PREVIEW_WARNING
     - If set, a warning will be shown indicating that the instance is a preview installation and that data will be deleted.
   * - SAMPLEDB_DISABLE_INLINE_EDIT
     - If set, the inline edit mode will be disabled and users will not be able to edit individual fields.
   * - SAMPLEDB_SHOW_OBJECT_TITLE
     - If set, object schema titles will be shown when viewing metadata by default. Users may override this setting in their preferences.
   * - SAMPLEDB_HIDE_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE
     - If set, the object type and id, e.g. "Sample #4" will not be shown on the object page.
   * - SAMPLEDB_MAX_BATCH_SIZE
     - Maximum number of objects that can be created in one batch (default: 100)
   * - SAMPLEDB_ENABLE_BACKGROUND_TASKS
     - If set, some potentially time consuming tasks such as sending emails will be performed in the background to reduce frontend latency or timeouts.

There are other configuration values related to packages used by SampleDB. For more information on those, see the documentation of the corresponding packages.
