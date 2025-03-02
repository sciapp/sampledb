.. _oidc:

OpenID Connect (OIDC)
=====================

If you use OIDC for user management, you can configure SampleDB to connect to
a single OIDC provider using the
:ref:`OIDC Configuration Environment Variables <oidc_configuration>`.
The client must be statically registered, while the configuration and keys must
be dynamically discoverable.

Only the Authorization Code Flow with ``client_secret_basic`` authentication
is supported. Proof Key for Code Exchange (PKCE) is used if the OIDC provider
signals support for the ``S256`` method. The provider should support the
``nonce`` parameter to allow for the detection of replay attacks. To increase
compatibility with some providers, the use of the parameter can be disabled
using a configuration variable. If a provider supports neither PKCE with
method ``S256``, nor ``nonce``, using it is not recommended.

RP-Initiated Logout will be used if the provider indicates support.
Back-Channel and Front-Channel Logout are not currently implemented.

The redirect URL for the authentication callback is set to the external URL of
the path ``/users/me/oidc/callback``, e.g.
``https://example.net/users/me/oidc/callback``, while the redirect URL for the
logout redirect is set to the external URL of the path ``/``, e.g.
``https://example.net/``. This can be configured using the `SERVER_NAME`
variable, see :ref:`Miscellaneous Configuration Environment Variables
<miscellaneous_config>`.

OIDC roles
^^^^^^^^^^

If ``SAMPLEDB_OIDC_ROLES`` is set, SampleDB will query this path on every
login and assign the configured roles to the user.

Available roles:

- ``is_active`` / ``is_not_active``
- ``is_hidden`` / ``is_not_hidden``
- ``is_readonly`` / ``is_not_readonly``
- ``is_admin`` / ``is_not_admin``

.. code-block:: json
    :caption: Roles in an ID Token

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

Note: Setting the ``is_not_active`` role will prevent the user from logging
in.
