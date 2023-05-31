.. _scicat_export:

SciCat Export
=============

`SciCat <https://scicatproject.github.io/>`_ is a web-based catalog for scientific metadata. Although it has a more fixed structure than |service_name|, with categories for proposals, samples, raw and derived datasets, many action types in |service_name| may be able to be mapped to one of these categories. To configure this mapping, the SciCat export type setting for action types can be used.

If the :ref:`SciCat Export configuration variables <scicat_configuration>` have been set, users with **GRANT** permissions can export object information to a SciCat instance. An entry containing both generic metadata and user-selected properties of the process-specific metadata will be created.

By default, none of the process-specific metadata will be exported. Users can enable individual properties, and the schema of a property may include a ``scicat_export`` boolean to set whether a property should be exported by default. This way, e.g. instrument scientists can provide a suggestion for what should be exported for a particular action.

During the export, users are able to select which groups in SciCat should have read and write permissions. Users can also select a SciCat instrument or a previously exported sample or input datasets, if applicable.
