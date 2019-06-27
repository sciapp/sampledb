.. _configuration:

Configuration
=============

When running a SampleDB installation, you can set the the following environment variables to configure it.

.. list-table:: Configuration Environment Variables
   :header-rows: 1

   * - Variable Name
     - Description
   * - SAMPLEDB_SERVICE_NAME
     - The name of the service
   * - SAMPLEDB_SERVICE_DESCRIPTION
     - A short description of the service
   * - SAMPLEDB_SERVICE_IMPRINT
     - The URL to use for the imprint link
   * - SAMPLEDB_MAIL_SERVER
     - The mail server used for outbound emails
   * - SAMPLEDB_MAIL_SENDER
     - The email address used for outbound emails
   * - SAMPLEDB_CONTACT_EMAIL
     - An email address for users to contact
   * - SAMPLEDB_FILE_STORAGE_PATH
     - A path to the directory that uploaded files should be stored in
   * - SAMPLEDB_SERVER_NAME
     - The server name for Flask. See: http://flask.pocoo.org/docs/1.0/config/#SERVER_NAME
   * - SAMPLEDB_SQLALCHEMY_DATABASE_URI
     - The database URI for SQLAlchemy. See: http://flask-sqlalchemy.pocoo.org/2.3/config/
   * - SAMPLEDB_SECRET_KEY
     - The secret key for Flask and Flask extensions. See: http://flask.pocoo.org/docs/1.0/config/#SECRET_KEY
   * - SAMPLEDB_LDAP_NAME
     - The name of the LDAP server shown to the users
   * - SAMPLEDB_LDAP_SERVER
     - The ldaps-URL of the LDAP server
   * - SAMPLEDB_LDAP_USER_BASE_DN
     - The LDAP base DN to search users with
   * - SAMPLEDB_LDAP_UID_FILTER
     - The filter to use for identifying a user in LDAP as python template, e.g. ``(uid={})``
   * - SAMPLEDB_LDAP_NAME_ATTRIBUTE
     - The name of the attribute containing a user's name in LDAP
   * - SAMPLEDB_LDAP_MAIL_ATTRIBUTE
     - The name of the attribute containing a user's email address in LDAP
   * - SAMPLEDB_LDAP_OBJECT_DEF
     - The object def to use for looking up user attributes, e.g. inetOrgPerson
   * - SAMPLEDB_LDAP_USER_DN
     - The DN of an LDAP user to use when searching for other users (optional)
   * - SAMPLEDB_LDAP_PASSWORD
     - The password for the user identified by SAMPLEDB_LDAP_USER_DN (optional)
   * - SAMPLEDB_JUPYTERHUB_URL
     - The base URL of a JupyterHub server with support for notebook templates (optional)
