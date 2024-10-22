Changelog
=========

Version 0.30
------------

Currently in development.

- Added starting number in batch object creation
- Improved .eln export and import
- Only show action types with usable actions in the navbar Actions dropdown
- Fixed search by array index
- Introduce recursive workflow view
- Added an option to disable user invitations (configurable with SAMPLEDB_DISABLE_USER_INVITATIONS)


Version 0.29.1
--------------

Released on August 20th, 2024.

- Fixed Bad Request error in the object form after more than 15 minutes without submitting the form
- Fixed sorting of instrument log entries


Version 0.29
------------

Released on August 19th, 2024.

- Fixed simple search query escaping to support searching for special characters
- Fixed handling of property named tags that contains an array or an object instead of tags
- Fixed indentation level styling
- Added support for flexible metadata in .eln imports

Version 0.28.2
--------------

Released on July 9th, 2024.

- Fixed collapse/expand button symbol for ``expandable`` or ``collapsible`` style objects in arrays
- Fixed instrument log performance issues
- Fixed sending of notifications when creating instrument log entries via HTTP API
- Fixed editing of choice style array dropdowns
- Fixed including image files with uppercase file extensions in PDF export

Version 0.28.1
--------------

Released on June 18th, 2024.

- Fixed use of timezones for ``date`` style ``datetime`` properties
- Fixed validation of ORCID iDs

Version 0.28
------------

Released on June 13th, 2024.

- Fixed search via API in combination with name_only parameter
- Fixed search for datetime attributes not being timezone-aware
- Added ``timeline`` array style for arrays of objects with a ``datetime`` property
- Added search to text fields with more than 10 choices (configurable with ``SAMPLEDB_MIN_NUM_TEXT_CHOICES_FOR_SEARCH``)
- Added support for ``"first"`` and ``"last"`` statistic for timeseries
- Added basic and project groups to the HTTP API
- Allow using dicts for the ``style`` attribute
- Added support for ``"include"`` style for object reference properties
- Allow referenced objects in search queries
- Improved .eln export
- Added support for file references as display properties
- Allow configuring multiple workflow views
- Add support for ``sorting_properties`` for workflow views
- Allow revoking group invitations
- Added ``date`` and ``time`` styles for datetime values
- Added support for additional preview images for files uploaded via HTTP API
- Added ``expandable``, ``collapsible`` and ``horizontal`` object styles

Version 0.27
------------

Released on March 18th, 2024.

- Added ``choice`` array style for multi selection dropdowns
- Introduce action topics and allow filtering action lists by topics
- Added new array index diff syntax for updating data via the HTTP API
- Added creation of activity log entries during import of objects from other databases
- Added initial support for custom templates

Version 0.26
------------

Released on February 13th, 2024.

- Show changes during schema upgrade
- Added support for FIDO2 passkeys for authentication and two-factor authentication
- Fully remove support for files with local storage (see: https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/administrator_guide/deprecated_features.html#local-file-storage)
- Allow configuring which action types are shown for object filters
- Added automatic sign out due to inactivity for users on shared devices
- Allow schema upgrade when using an object as a template
- Allow using the simple search via the HTTP API
- Fixed setting ``SAMPLEDB_HELP_URL``
- Fixed two-factor authentication for refresh logins
- Added federated identities
- Added user activity to object list filters

Version 0.25.3
--------------

Released on December 20th, 2023.

- Fixed showing plotly plots on instrument page
- Fixed datetime format in HTTP API
- Fixed user interface issues related to admin-only action types
- Fixed handling of defaults during complex schema upgrades

Version 0.25.2
--------------

Released on December 7th, 2023.

- Fixed bool fields with defaults

Version 0.25.1
--------------

Released on December 7th, 2023.

- Fixed choice_equals conditions nested in any, all or not conditions

Version 0.25
------------

Released on December 4th, 2023.

- Implement client-side array editing
- Allow automatic calculation of quantity values
- Show object form errors as expandable alert message
- Added file name search
- Added object_log API endpoint
- Added object log webhooks

Version 0.24.1
--------------

Released on July 27th, 2023.

- Fixed conditions not being applied correctly to object reference fields

Version 0.24
------------

Released on July 17th, 2023.

- Added .eln file import
- Allowed updating actions via the HTTP API
- Allow granting READ permissions to all signed-in users during object creation
- Prevent creation of files with the :ref:`deprecated <deprecated_features>` local file storage via HTTP API
- Removed setting ``SAMPLEDB_LOAD_OBJECTS_IN_BACKGROUND``
- Introduce statistics and relative times in timeseries
- Allow tooltips for property titles
- Fixed search by user name

Version 0.23.1
--------------

Released on June 6th, 2023.

- Fixed handling of selectpicker fields with conditions

Version 0.23
------------

Released on May 31st, 2023.

- Added support for short-lived API access tokens
- Added file datatype
- Implemented workflow view for related objects
- Allow administrators to set whether they want to see hidden users

Version 0.22.1
--------------

Released on April 19th, 2023.

- Fix bug preventing federation file imports containing file hash information

Version 0.22
------------

Released on April 12th, 2023.

- Implemented object storage capacities for locations
- Applied admin permissions to managing groups
- Added selection to generate labels for multiple objects
- Added selection to change the permission for multiple objects
- Added timeseries data type
- Added support for translated property titles and notes to the graphical schema editor
- Enforce that titles in schemas are not empty
- Allow using more than one LDAP server
- Added optional checksum for file contents
- Allow viewing differences between object versions
- Fixed configuration of action types linkable to project groups
- Allow linking an object to an instrument to provide additional information
- Added data differences between object versions to the version api

Version 0.21.5
--------------

Released on March 10th, 2023.

- Fixed object search filter by action or type
- Fixed usage text in scripts
- Fixed download service permission checks
- Fixed logic for displaying "Use as Template" button for objects

Version 0.21.4
--------------

Released on February 21st, 2023.

- Fixed label generation for imported objects
- Show "Create Action" button for instrument scientists

Version 0.21.3
--------------

Released on February 7th, 2023.

- Translate group names in invitation notifications
- Fixed filtering objects by group permissions

Version 0.21.2
--------------

Released on February 2nd, 2023.

- Fixed compatibility with PostgreSQL 11

Version 0.21.1
--------------

Released on January 25th, 2023.

- Fixed filtering by activity of a user

Version 0.21
------------

Released on January 23rd, 2023.

- Improved user interface
- Add basic federation feature
- Added optional support for background tasks
- Allow ftp, file, sftp and smb scheme and IPv6 addresses in URLs
- Improve display of quantities
- Improve static file caching
- Added support for a monitoring dashboard (experimental)
- Added location permission management
- Enabled asynchronous loading of object lists by default
- Deprecated setting ``SAMPLEDB_LOAD_OBJECTS_IN_BACKGROUND`` to false
- Deprecated local file storage
- Deprecated numeric tags
- Added recipes
- Allow missing datetime entries if not marked as required
- Fix negated text search
- Fix search with missing attributes
- Made the objects table width configurable
- Allow searching for missing attributes
- Allow setting minimum and maximum values for quantities
- Allow setting an instance-wide timezone using ``SAMPLEDB_TIMEZONE``
- Added array style ``full_width_table``
- Allow selecting a unit when entering a quantity
- Allow giving anonymous users READ permissions for objects
- Added SciCat export
- Added .eln file export
- Allow declining object responsibility assignments
- Implemented location types, location responsible users and a location log
- Added download service
- Allow saving object list filters
- Show last user profile update time
- Allow administrators to update user profile information
- Added ``show_more`` option for objects
- Allow hiding locations as administrator
- Allow showing objects stored at sub-locations
- Added group categories
- Allow assigning a location to an instrument
- Added API route to get related objects
- Allow disabling instrument features
- Added support for ``hh:mm:ss`` time notation for hours and minutes quantities

Version 0.20
------------

Released on March 4th, 2022.

- Added support for any, all and not conditions
- Improve Markdown field image uploads
- Add schema templates
- Support multiple action IDs or action type IDs for object reference schemas
- Improved user interface
- Fix number rounding

Version 0.19.3
--------------

Released on January 19th, 2022.

- Fix schema upgrade for multi language choices

Version 0.19.2
--------------

Released on January 7th, 2022.

- Fix editing notes in schema editor

Version 0.19.1
--------------

Released on December 20th, 2021.

- Fix missing object type and ID on object page when using inline edit mode

Version 0.19
------------

Released on December 9th, 2021.

- Allow filtering instrument log entries by author
- Allow sorting instrument log entries by author
- Added event datetime for instrument log entries
- Added internationalization features
- Added german localization
- Store file contents in database by default
- Allow setting a publicly visible user role
- Added support for configurable user fields
- Added label for administrators in user list
- Allow individual exemptions for Use as Template
- Allow setting a default number of items for arrays
- Improved user interface
- Added support for a custom CSS file
- Added support for conditional properties
- Allow filtering object references by action
- Implemented TOTP-based two factor authentication
- Added tree view for instrument log entries
- Allow editing individual fields
- Allow hiding object type and id on object page

Version 0.18
------------

Released on May 7th, 2021.

- Moved example_data functionality to set_up_data script
- Allow administrators to enforce user names to be given as surname, given names
- Added plotly_chart data type
- Improved search page
- Improved object version HTTP API
- Improved action HTTP API
- Improved user interface

Version 0.17
------------

Released on February 10th, 2021.

- Added Dataverse export using the EngMeta "Process Metadata" block
- Added short descriptions to actions and instruments
- Added array style "horizontal_table"
- Improved handling of optional text input
- Allow linking to headers in Markdown content
- Allow disabling of "Use in Measurement" button for samples
- Added markdown support to object metadata
- Added markdown support to instrument log
- Reimplemented PDF export
- Added configuration variables to allow only administrators to create groups or projects
- Added asterisks to mark required fields when editing objects
- Project permissions can be set when inviting a user
- Allow default value "self" for user fields
- Allow searching for tags in dropdown object selection fields
- Renamed projects to project groups and groups to basic groups to avoid ambiguity
- Allow disabling of subprojects / child project groups
- Allow giving basic or project groups initial permissions
- Allow configuring the Help link
- Allow linking project groups to objects
- Fixed action ID filtering when loading objects in the background
- Added action permissions to user interface
- Improved handling of quantities for the HTTP API

Version 0.16.1
--------------

Released on January 27th, 2021.

- Fixed object name escaping when loading objects in the background

Version 0.16
------------

Released on December 9th, 2020.

- Allow restricting object references to specific action id
- Improved performance of object lists
- Allow setting display properties as part of the object list URL
- Improved performance of instrument pages
- Added image upload via drag and drop to Markdown editors
- Added support for placeholder texts for text and quantity schemas
- Added additional options to the HTTP API objects endpoint
- Display projects based on parent-child relationship
- Improved "View Objects" for users, groups and projects
- Added object comments to the HTTP API

Version 0.15
------------

Released on November 6th, 2020.

- Added versioning to instrument log entries
- Added user to metadata types
- Allow setting instrument log entry order
- Allow custom action types
- Allow administrators to deactivate users
- Allow disabling group deletion by non-administrators
- Fixed pagination for viewing objects of a project
- Added Docker Compose configuration file
- Ensure that file storage path is owned by sampledb user in docker container
- Added ``SAMPLEDB_LOAD_OBJECTS_IN_BACKGROUND`` option to load object select options using ajax
- Added "list" array style
- Added Markdown editor for editing instrument and action Markdown content

Version 0.14.1
--------------

Released on October 13th, 2020.

- Upgraded dependencies

Version 0.14
------------

Released on September 23rd, 2020.

- Allow restricting location management to administrators
- Do not show hidden users as instrument scientists
- Added setting for admin permissions
- Allow hiding instruments and actions
- Added object name to properties of publications linked to an object
- Improved invitation token handling
- Made invitation time limit configurable
- Show pending group and project invitations to members
- Show all group and project invitations to administrators
- Allow copying permissions from another object
- Improved user interface

Version 0.13.1
--------------

Released on September 9th, 2020.

- Fixed a user interface issue

Version 0.13
------------

Released on September 2nd, 2020.

- Added Dublin Core metadata in RDF/XML format
- Added fullscreen image preview of object and instrument log images
- Added instrument log to HTTP API
- Allow filtering instrument log by month
- Allow setting a publicly visible user affiliation

Version 0.12
------------

Released on July 29th, 2020.

- Added data export as PDF document, .zip or .tar.gz archive
- Allow adding a logo to object export PDF documents
- Allow setting a publicly visible ORCID iD
- Added instrument log
- Added instrument scientist notes

Version 0.11
------------

Released on June 18th, 2020.

- Allow usage of Markdown in instrument and action descriptions
- Added configuration values for creating an admin user during initial setup
- Added administrator guide to documentation

Version 0.10
------------

Released on May 11th, 2020.

- Allow configuring label formats
- Added search filters to objects API

Version 0.9
-----------

Released on March 10th, 2020.

- Allow creating and editing instruments using the web frontend
- Allow referencing measurements as object properties
- Added readonly users
- Allow hiding users
- Added API tokens
- Added administration functions to the web frontend
- Fixed various minor bugs

Version 0.8.1
-------------

Released on December 10th, 2019.

- Simplified deployment

Version 0.8
-----------

Released on November 12th, 2019.

- Added search to group and project dialogs
- Fixed various minor bugs


Version 0.7
-----------

Released on September 13th, 2019.

- Allow deleting groups and projects
- Allow group and project member removal
- Allow users to accept responsibility assignments
- Fixed various minor bugs


Version 0.6
-----------

Released on August 30th, 2019.

- Added JupyterHub notebook templates
- Added list of tags
- Fixed various minor bugs


Version 0.5
-----------

Released on April 15th, 2019.

- Added publications
- Removed activity log
- Added files to HTTP API
- Improved user interface


Version 0.4
-----------

Released on February 13th, 2019.

- Added object pagination
- Added posting of external links for objects
- Added schema editor
- Added 'Use in Measurement' button to samples
- Fixed various minor bugs


Version 0.3.1
-------------

Released on January 21st, 2019.

- Improved performance of object permissions


Version 0.3
-----------

Released on January 16th, 2019.

- Added custom actions
- Added locations
- Added notifications
- Added search by user name
- Added users and object permissions to HTTP API
- Improved documentation
- Improved email design
- Improved user interface
- Fixed various minor bugs


Version 0.2
-----------

Released on November 30th, 2018.

- Added documentation
- Added HTTP API
- Added *Related Objects* to objects' pages
- Added PDF export for objects
- Added label generation for objects
- Added GHS hazards as optional metadata
- Added error messages during object creation and editing
- Changed advanced search to be automatic for some queries
- Added sorting to object tables
- Added favorites for actions and instruments
- Improved user interface
- Fixed various minor bugs

Version 0.1
-----------

First stable release.
