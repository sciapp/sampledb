.. _oidc:

OpenID Connect (OIDC)
=====================

If you use OIDC for user management, you can configure SampleDB to connect to
a single OIDC provider using the
:ref:`OIDC Configuration Environment Variables <oidc_configuration>`.

The client must be statically registered, while the configuration and keys
must be dynamically discoverable. The configuration is cached until shutdown,
the keys are cached for 10 hours. Startup and key refresh require the IdP to
be reachable, otherwise startup will fail and OIDC users will be signed out.
The ``name``, ``email`` and ``email_verified`` claims are required, the latter
must be ``true``.

Only the Authorization Code Flow with ``client_secret_basic`` authentication
is supported. Proof Key for Code Exchange (PKCE) with method ``S256`` is
always offered. The provider should support the ``nonce`` parameter to allow
for the detection of replay attacks. If a provider supports neither PKCE with
method ``S256``, nor ``nonce``, using it is not recommended.

RP-Initiated Logout will be used if the provider indicates support. The
session's lifetime will be bound to the that of the ID Token if configured. In
that case, Refresh Tokens are required and used to transparently refresh the
ID Token after its expiration. Back-Channel Logouts will end the session if
configured at the provider. The ``sub`` claim is required. If a ``sid`` claim
is present, only the matching session is expired; otherwise, all active OIDC
sessions for the user are expired. Front-Channel Logout is not currently
implemented.

The following URLs can or must be configured at the OIDC provider:

.. list-table::
   :header-rows: 1

   * - Type
     - URL
     - Required

   * - Authentication callback
     - ``/users/me/oidc/callback``
     - Yes

   * - Post logout redirect
     - ``/``
     - Yes

   * - Back-Channel Logout
     - ``/users/me/oidc/backchannel_logout``
     - No

For example, if the SampleDB is hosted at ``https://samples.example.net``,
then the authentication callback would be
``https://samples.example.net/users/me/oidc/callback``.

.. _oidc_account_linking:

Account Linking
^^^^^^^^^^^^^^^

OIDC sign-ins provide a subject identifier (the ``sub`` claim) that uniquely
links the user's account at the OIDC provider to their account in SampleDB.

When a user signs in via OIDC for the first time, this link does not yet
exist. In this case, SampleDB checks whether a user with the same email
address exists and whether the configuration variable
``SAMPLEDB_OIDC_CREATE_ACCOUNT`` allows creating a new account or linking to
an existing one.

.. list-table::
   :header-rows: 1

   * - Email address exists
     - OIDC_CREATE_ACCOUNT
     - Resulting action

   * - No
     - ``deny_existing``
     - New account created

   * - No
     - ``auto_link``
     - New account created

   * - No
     - ``no``
     - Sign-in denied

   * - Yes
     - ``deny_existing``
     - Sign-in denied

   * - Yes
     - ``auto_link``
     - Linked to the account (if the account is active, otherwise denied)

   * - Yes
     - ``no``
     - Sign-in denied


If the OIDC provider reuses email addresses, the ``auto_link`` option may
allow a new user (e.g., Jane Doe) to access the SampleDB account of a previous
user (e.g., John Doe) who formerly held the address ``j.doe@example.org``.
Accordingly, use of the ``auto_link`` option should be carefully considered.

It is not yet possible to create these links through the user interface or
administration scripts.

OIDC roles
^^^^^^^^^^

If ``SAMPLEDB_OIDC_ROLES`` is set, SampleDB will query this path on every
login and assign the configured roles to the user.

Available roles:

- ``is_active`` / ``is_not_active``
- ``is_hidden`` / ``is_not_hidden``
- ``is_readonly`` / ``is_not_readonly``
- ``is_admin`` / ``is_not_admin``

.. raw:: html

   <style>
     .highlight .err {
       border: inherit;
       box-sizing: inherit;
       color: #777777;
     }
   </style>

.. code-block:: json
    :caption: Roles in an ID Token
    :force:

    {
      ...
      "resource_access": {
        "sampledb": {
          "roles": [
            "is_active",
            "is_not_hidden"
          ]
        }
      },
      "email": "user@example.org"
      ...
    }

Based on the provided ID Token and variable
``SAMPLEDB_OIDC_ROLES=resource_access.sampledb.roles``, SampleDB will set the
user as active and not hidden, and will not change whether they are readonly
or an admin.

.. note::
  Setting the ``is_not_active`` role will prevent the user from logging in.

Access Tokens as API keys
^^^^^^^^^^^^^^^^^^^^^^^^^

SampleDB can be configured to allow OIDC Access Tokens as API tokens using the
``Bearer Authentication`` of the :ref:`HTTP API<http_api>`. These tokens work
like regular user-bound API tokens and are validated for every request. The
lifetime of the Access Token is set by the provider.

OIDC Access Tokens are validated by making an HTTP request to the
Introspection Endpoint of the provider, which then returns either the relevant
user details or an error. Alternatively, if the provider encodes its Access
Tokens as JSON Web Tokens (JWT), then validation may omit the introspection
request and rely on the cryptographic signature of the token.

.. note::
  SampleDB will first try to validate other types of API tokens,
  then try to validate the token as a JWT, and only if it is not a JWT and
  introspection is enabled, will SampleDB make the introspection request.
  Meaning, if introspection is enabled, every API request with an invalid
  API token will result in a request to the OIDC provider.

.. note::
  API requests will not create user accounts or update user
  profiles, meaning the user making the API request must already have their
  account linked to the provider. However, if OIDC roles are used, they will
  be updated. Or, if they are missing or invalid, fail the login.
