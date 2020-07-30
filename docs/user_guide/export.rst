.. _export:

Export
======

|service_name| can export the data for all objects a :ref:`User <users>` has **READ** permissions for, either as a PDF file or as an archive containing a machine-readable JSON file and the files uploaded for these objects.

The PDF file consists of the :ref:`PDF files <pdf_export>` for the individual objects. As a result, only the current metadata versions and only those uploaded files that can be represented in the PDF are included.

The archive contains a file ``data.json`` with information on objects in JSON format, including all metadata versions, comments, publications, location history and basic information on uploaded files, alongside information on relevant actions, instruments, users and locations. The uploaded files themselves are in subdirectories, grouped by the individual objects, so the first file uploaded for an object with the ID #42 would be located in the directory ``objects/42/files/0`` under its original upload name. It also contains a ``.rdf`` file containing Dublin Core metadata in RDF/XML format for each object.
