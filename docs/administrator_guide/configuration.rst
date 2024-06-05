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
     - The ldaps-URL of the LDAP server, or a comma separated list of ldaps-URLs to use more than one LDAP server
   * - SAMPLEDB_LDAP_CONNECT_TIMEOUT
     - The timeout to use for connecting to the LDAP server(s)
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

.. _customization_configuration:

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
   * - SAMPLEDB_SERVICE_LEGAL_NOTICE or SAMPLEDB_SERVICE_IMPRINT
     - The URL to use for the legal notice link
   * - SAMPLEDB_SERVICE_PRIVACY_POLICY
     - The URL to use for the privacy policy link
   * - SAMPLEDB_SERVICE_ACCESSIBILITY
     - The URL to use for the accessibility link
   * - SAMPLEDB_PDFEXPORT_LOGO_URL
     - A file, http or https URL for a PNG or JPEG logo to be included in object export PDF documents
   * - SAMPLEDB_PDFEXPORT_LOGO_ALIGNMENT
     - The alignment (left, center or right) of the logo, if SAMPLEDB_PDFEXPORT_LOGO_URL is set (default: right)
   * - SAMPLEDB_PDFEXPORT_LOGO_WIDTH
     - The width of the logo in millimeters (default: 30). Large logos will overlap with the content of the object export, so make sure the size and alignment do not cause any issues.
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

.. _scicat_configuration:

SciCat Export
-------------

.. list-table:: SciCat Export Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_SCICAT_NAME
     - The name of the SciCat instance (default: ``SciCat``)
   * - SAMPLEDB_SCICAT_API_URL
     - The base URL of the SciCat API server
   * - SAMPLEDB_SCICAT_FRONTEND_URL
     - The base URL of the SciCat frontend server
   * - SCICAT_EXTRA_PID_PREFIX
     - An additional prefix to use for generating persistent identifiers in combination with a UUID

For more information on the SciCat export, see :ref:`scicat_export`.

.. _download_service_configuration:

Download Service
----------------

.. list-table:: Download Service Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - DOWNLOAD_SERVICE_URL
     - The base URL of the Download Service
   * - DOWNLOAD_SERVICE_SECRET
     - The shared secret
   * - DOWNLOAD_SERVICE_WHITELIST
     - Whitelist in form of a json dict. Example: {"/normally/restricted/path/": [userID, userID2]}
   * - DOWNLOAD_SERVICE_TIME_LIMIT
     - Time the created download link is valid. In seconds. Default are 24h.

For more information on the Download Service, see :ref:`download_service`.

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
   * - SAMPLEDB_ENABLE_DEFAULT_USER_ALIASES
     - If set, users will have aliases using their profile information by default (default: False). This will not apply to bot users or imported users.
   * - SAMPLEDB_ENABLE_FEDERATION_DISCOVERABILITY
     - If set, this instance will be discoverable by other databases in the same federation. (default: True).

.. _monitoring_dashboard_configuration:

Monitoring Dashboard
--------------------

.. list-table:: Monitoring Dashboard Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_ENABLE_MONITORINGDASHBOARD
     - If set, the monitoring dashboard will be enabled.
   * - SAMPLEDB_MONITORINGDASHBOARD_DATABASE
     - The database URL for the monitoring dashboard (default: ``sqlite:///flask_monitoringdashboard.db``)

.. _miscellaneous_config:

Miscellaneous
-------------

.. list-table:: Miscellaneous Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
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
   * - SAMPLEDB_FULL_WIDTH_OBJECTS_TABLE
     - If set, the table of objects will be the full width of the browser. Users may override this setting in their preferences. (default: True)
   * - SAMPLEDB_HIDE_OBJECT_TYPE_AND_ID_ON_OBJECT_PAGE
     - If set, the object type and id, e.g. "Sample #4" will not be shown on the object page.
   * - SAMPLEDB_MAX_BATCH_SIZE
     - Maximum number of objects that can be created in one batch (default: 100)
   * - SAMPLEDB_ENABLE_BACKGROUND_TASKS
     - If set, some potentially time consuming tasks such as sending emails will be performed in the background to reduce frontend latency or timeouts.
   * - SAMPLEDB_TIMEZONE
     - If set, the given timezone will be used for all users instead of using their browser timezone or the one set in their preferences.
   * - SAMPLEDB_USE_TYPEAHEAD_FOR_OBJECTS
     - **Experimental**: If set, a text field with typeahead.js based suggestions will be used for object references instead of a dropdown/select field.
   * - SAMPLEDB_TYPEAHEAD_OBJECT_LIMIT
     - If SAMPLEDB_USE_TYPEAHEAD_FOR_OBJECTS is set, this value can set an upper limit for the number of object suggestions shown. Not set by default.
   * - SAMPLEDB_ENABLE_ANONYMOUS_USERS
     - If set, objects may be set to be readable by anonymous users, without requiring them to sign in.
   * - SAMPLEDB_SHOW_UNHANDLED_OBJECT_RESPONSIBILITY_ASSIGNMENTS
     - If set, any unhandled object responsibility assignment will be shown as an urgent notification on non-object pages (default: True).
   * - SAMPLEDB_SHOW_LAST_PROFILE_UPDATE
     - If set, show the date and time of the last user information update in each user profile (default: True). Updates by an administrator will be shown regardless of this configuration value.
   * - SAMPLEDB_ONLY_ADMINS_CAN_MANAGE_GROUP_CATEGORIES
     - If set, only administrators will be able to manage group categories (default: True).
   * - SAMPLEDB_DISABLE_INSTRUMENTS
     - If set, features related to instruments will be disabled (default: False).
   * - SAMPLEDB_ENABLE_FUNCTION_CACHES
     - If set, some functions with results that cannot change will use caches (default: True).
   * - SAMPLEDB_TEMPORARY_FILE_TIME_LIMIT
     - Time that temporary files uploaded when editing an object are stored, in seconds (default: 604800 seconds / 7 days).
   * - SAMPLEDB_ENABLE_ELN_FILE_IMPORT
     - If set, .eln files can be imported by users (default: False). :ref:`Importing .eln files <eln_import>` is currently experimental and not recommended for production systems, as the file format is still a work in progress.
   * - SAMPLEDB_ENABLE_WEBHOOKS_FOR_USERS
     - If set, "normal" users can register webhooks (default: False). If this option is not set or set to ``false`` only administrators are allowed to register webhooks. See :ref:`Webhooks <webhooks>`.
   * - SAMPLEDB_WEBHOOKS_ALLOW_HTTP
     - If set, using webhook targets that do not support https is allowed (default: False).
   * - SAMPLEDB_ENABLE_FIDO2_PASSKEY_AUTHENTICATION
     - If set, FIDO2 passkeys can be used as an authentication method instead of just as a second factor.
   * - SAMPLEDB_SHARED_DEVICE_SIGN_OUT_MINUTES
     - The time of inactivity after which users on shared devices will be signed out in minutes (default: 30 minutes).
   * - SAMPLEDB_DISABLE_OUTDATED_USE_AS_TEMPLATE
     - If set, users cannot use objects with outdated schemas as a template (default: False).
   * - SAMPLEDB_DISABLE_TOPICS
     - You can set this option to disable the :ref:`Topics <topics>` feature. (default: False, Topics enabled)
   * - SAMPLEDB_LABEL_PAPER_FORMATS
     - Specifies label paper formats that can be used for qr code labels. For more information, see :ref:`Label Paper Formats <labels>`. (default: ``[]``)
   * - SAMPLEDB_MIN_NUM_TEXT_CHOICES_FOR_SEARCH
     - The minimum number of choices a text field needs to have for search to be enabled (default: 10). Set to 0 to enable search for all choice text fields or to -1 to disable search for them.

There are other configuration values related to packages used by SampleDB. For more information on those, see the documentation of the corresponding packages.
