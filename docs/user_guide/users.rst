.. _users:

Users
=====

.. _authentication:

Authentication
--------------

Users at facilities which use LDAP for user management can use their **LDAP username** with the corresponding password to sign in. An account will be created automatically.

Guests, or users at facilities without LDAP, should ask another user of |service_name| for an **invitation**, e.g. the scientist responsible for the instrument they will be using. Once they have confirmed their email address by clicking the confirmation link in the invitation email, they can then set a password for their new |service_name| account.

.. figure:: ../static/img/generated/guest_invitation.png
    :scale: 50 %
    :alt: User Invitation Form

    User Invitation Form

Users can find the invitation form at |service_invitation_url|.

.. _preferences:

Preferences
-----------

Users can edit their preferences by clicking on their name in the top right corner and selecting preferences.

The preferences are split into the following sections:

User Information
````````````````

Users can update their user name displayed on |service_name|, e.g. in the event of a marriage. They can also change their email address, which will be updated once the new address has been confirmed, and set a publicly visible ORCID iD and affiliation.

Authentication Methods
``````````````````````

Users can have multiple ways of signing in to |service_name|, for example using their LDAP account or using an email address. This section of the user preferences can be used to add, modify or remove such authentication methods, e.g. for users leaving their institute but still requiring access to their sample data.

API Tokens
``````````

API tokens are meant as an alternative method for authentication when using the :ref:`HTTP API <http_api>` for individual scripts and allow you to monitor the requests made with the token. When you create a new API token, it will be shown to you once and you will be asked to save it. If you lose access to a token, simply delete it and create a new one as replacement.

While API tokens pose less of a risk than using your own user credentials in a script, please keep your API tokens private. Do not commit them with a version control system like git and do not share them with others!

Default Permissions
```````````````````

To automatically set permissions for future objects, users can set **default permissions** in their preferences. These will be applied whenever an object like a sample or measurement is created afterwards.

For more information, see :ref:`default_permissions`.

.. _notifications:

Notifications
-------------

Users will receive notifications whenever they need to be informed about an activity on |service_name|. Whenever a user has unread notifications, a bell with the number of unread notifications is shown in the navigation bar.

.. figure:: ../static/img/generated/unread_notification_icon.png
    :scale: 50 %
    :alt: Unread Notification Icon

    Unread Notification Icon

Bot Users
---------

Tasks like object creation can be automated by using the :ref:`HTTP API <http_api>`. When this is done in connection to an instrument or a facility instead of an individual user, it may be better to create a dedicated user account solely for this purpose.

Readonly Users
--------------

Users can be limited to READ permissions, e.g. for former employees who should still have access to their data but should not be able to create new SampleDB entries.

Hidden users
------------

Users can also be hidden from users lists, which may be useful in similar use cases as when marking a user as readonly. These users can still be seen as part of an object's history or as members of groups and projects, but they will not be shown in the central users list, when granting permissions, inviting a user to a group or project, etc.

Deactivated users
------------------

Users can also be deactivated. These users will be unable to sign in to their account or use the API until they have been reactivated by an administrator. As they will be unable to access their own data, this should only be used if marking a user as readonly will not suffice.
