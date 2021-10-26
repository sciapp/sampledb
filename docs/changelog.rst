Changelog
=========

Version 0.19
------------

Currently in development.

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
