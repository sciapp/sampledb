.. _dataverse_export:

Dataverse Export
================

Dataverse is web application for managing research data, including its publication. In contrast to |service_name|, which focuses on managing flexible, process-specific metadata within an organization, Dataverse has an administrator-managed schema system and aims at the sharing and visibility of research data.

If the :ref:`Dataverse Export configuration variables <dataverse_configuration>` have been set, users with **GRANT** permissions can export object information and files to a Dataverse server. A draft dataset is then created there, which the user can edit, review and publish according to the Dataverse permissions.

To be able to represent the process-specific metadata in a format compatible with Dataverse, |service_name| relies both on the Dataverse *Citation Metadata* block for generic metadata and the *Process Metadata* block developed by the University of Stuttgart as part of `EngMeta <https://www.izus.uni-stuttgart.de/fokus/engmeta/>`_.

By default, none of the files or process-specific metadata will be exported. Users can enable individual files and properties, and the schema of a property may include a ``dataverse_export`` boolean to set whether a property should be exported by default. This way, e.g. instrument scientists can provide a suggestion for what should be exported for a particular action.
