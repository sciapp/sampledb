.. _users:

Users
=====

.. _authentication:

Authentication
--------------

SampleDB offers three authentication methods:

1. LDAP Authentication
^^^^^^^^^^^^^^^^^^^^^^
Users at facilities which use LDAP for user management can use their **LDAP username** with the corresponding password to sign in. An account will be created automatically.

2. OpenID Connect (OIDC) Authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Users at facilities which offer OIDC authentication can sign in using this provider. Depending on the facility's configuration, this process may either create a new account or automatically link to an existing one.

Depending on the configuration, this method may permit guests to sign in as well.

3. Federated Login using a federated SampleDB instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the SampleDB is part of a federation and Federated Login is configured, users may use their login at another SampleDB instance to sign in.

4. Invitation-based Authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* For guests or users at facilities where the previous three authentication methods are not available:
   - Request an **invitation** from an existing |service_name| user (typically the scientist responsible for your instrument).
   - Click the confirmation link in the invitation email to verify your email address.
   - Set a password for your new |service_name| account.

.. note::
   If you're unsure which method to use, contact your facility's IT support or the |service_name| administrator.

.. figure:: ../static/img/generated/guest_invitation.png
    :alt: User Invitation Form

    User Invitation Form

Users can find the invitation form at |service_invitation_url|.

.. _preferences:

Preferences
-----------

Users can edit their preferences by clicking on their name in the top right corner and selecting preferences.

The preferences are split into the following sections:

User Information
^^^^^^^^^^^^^^^^

Users can update their user name displayed on |service_name|, e.g. in the event of a marriage. They can also change their email address, which will be updated once the new address has been confirmed, and set a publicly visible ORCID iD, affiliation and role.

Authentication Methods
^^^^^^^^^^^^^^^^^^^^^^

Users can have multiple ways of signing in to |service_name|, for example using their LDAP account or using an email address. This section of the user preferences can be used to add, modify or remove such authentication methods, e.g. for users leaving their institute but still requiring access to their sample data.

API Tokens
^^^^^^^^^^

API tokens are meant as an alternative method for authentication when using the :ref:`HTTP API <http_api>` for individual scripts and allow you to monitor the requests made with the token. When you create a new API token, it will be shown to you once and you will be asked to save it. If you lose access to a token, simply delete it and create a new one as replacement.

While API tokens pose less of a risk than using your own user credentials in a script, please keep your API tokens private. Do not commit them with a version control system like git and do not share them with others!

Default Permissions
^^^^^^^^^^^^^^^^^^^

To automatically set permissions for future objects, users can set **default permissions** in their preferences. These will be applied whenever an object like a sample or measurement is created afterwards.

For more information, see :ref:`default_permissions`.

.. _notifications:

Notifications
-------------

Users will receive notifications whenever they need to be informed about an activity on |service_name|. Whenever a user has unread notifications, a bell with the number of unread notifications is shown in the navigation bar.

.. figure:: ../static/img/generated/unread_notification_icon.png
    :alt: Unread Notification Icon

    Unread Notification Icon

Bot Users
---------

Tasks like object creation can be automated by using the :ref:`HTTP API <http_api>`. When this is done in connection to an instrument or a facility instead of an individual user, it may be better to create a dedicated user account solely for this purpose.

Readonly Users
--------------

Users can be limited to READ permissions, e.g. for former employees who should still have access to their data but should not be able to create new SampleDB entries.

Hidden Users
------------

Users can also be hidden from users lists, which may be useful in similar use cases as when marking a user as readonly. These users can still be seen as part of an object's history or as members of basic and project groups, but they will not be shown in the central users list, when granting permissions, inviting a user to a group, etc.

Deactivated Users
------------------

Users can also be deactivated. These users will be unable to sign in to their account or use the API until they have been reactivated by an administrator. As they will be unable to access their own data, this should only be used if marking a user as readonly will not suffice.


User Aliases
------------

If |service_name| is set up to be used in a federation to share data with other databases, users can decide which personal data should be shared by configuring user aliases.
A user alias allows to set name, affiliation, and role for each database individually or to disable or enable the transfer of these values from the user profile.
Also, it can be allowed or forbidden to share the email address and ORCID iD.

If a user does not create an alias for a database, no personal information will be shared with that database.

.. note::
    Administrators can enable that the information from user profiles will be shared by default.


Federated Identities
--------------------

If a user has access to two or more different SampleDB instances in a federation, they can be locally linked by a federated identity.
A federated identity allows the federation users to be recognized (e.g., object creation, comments, etc.) by the name of the local corresponding user in the federated identity.

To create federated identities, there are two different ways:
- The first way is that users can create federated identities by themselves. For that, the users have to verify their identity by authenticating with the federation partner through the "Sign in to …" button in the federation overview.
- As an alternative, if the local and federated users share the same email address, a federated identity will be created automatically when updates are imported.

When users have federated identities that were created automatically, these federated identities are not verified, so they cannot be used directly for the federated login. To verify, the users have to use the "Sign in to…" button in the federation overview or use the federated login and authenticate locally.

.. figure:: ../static/img/generated/federated_identity.png
    :alt: Federated Identity Overview

    Federated Identity Overview


In addition to the federated identities used with federation partners, users can also create federated identities during the process of :ref:`importing an .eln file <eln_import>`.

.. note::
    When setting up a federated identity for users from ELN files, the importing users can only create a federated identity for themselves.


Federated Login
---------------

If an administrator enabled this feature, it is possible that users can authenticate using the login of a federation partner.
To sign in to |service_name| using the federated login, the user can use the "Sign in with …" button on the sign in page.

When using this method, the users will first be redirected to the federation partner, where they have to authenticate.
After the authentication is successful, the user is redirected back to |service_name|.
If the federation user, which is used for authentication, already has a federated identity that is verified, the user will be directly signed in to that user.
Otherwise, if no federated identity exists or has not been verified, the users have to login to a local user additionally.
After this, it is ensured that a verified federated identity exists, and the last step does not have to be done again.

If an administrator enabled the creation of new users, then users who do not have an account with a verified federated identity will be able to create
a new user who has a federated identity with the federation user.
