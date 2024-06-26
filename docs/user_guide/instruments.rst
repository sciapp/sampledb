.. _instruments:

Instruments
===========

Instruments in |service_name| map real instruments to :ref:`actions` performed with them.

You can view a list of instruments at |service_instruments_url|. To make navigating the growing list of instruments easier, users can select **favorites** by clicking the star next to an instrument's name.

Each instrument can optionally be assigned to a :ref:`location <locations>`, to indicate to users where the instrument can be found. Similarly, each instrument can optionally be linked to an object that may contain additional metadata for the instrument. Administrators can control whether objects created with actions of a certain :ref:`type <action_types>` can be used for this.

.. note::
    At this time, instruments can only be created by the |service_name| administrators. If you would like your instrument or action to be included, please `let us know`_.

.. _instrument_scientists:

Instrument Scientists
---------------------

Most instruments are associated with one or more **instrument scientists**, who will automatically be granted permissions for all objects created with their instruments. For more information on how permissions are handled, see :ref:`permissions`.

.. _instrument_scientist_notes:

Instrument Scientist Notes
^^^^^^^^^^^^^^^^^^^^^^^^^^

Instrument Scientists can save notes, e.g. for internal information on  instrument maintenance or configuration.
These notes will not be shown to regular users, though they should not be used to store sensitive information such as passwords.

.. _instrument_log:

Instrument Log
--------------

Instrument scientists can use the instrument log to keep track of problems, maintenance or other events. They can decide whether the log can be seen by other users, and whether other users can also create log entries, e.g. to report issues. When a new log entry is created, a notification will be sent to the instrument scientists.

.. _instrument_topics:

Topics
------

Topics allow you to filter the instrument list by predefined topics.
When creating or editing an instrument, you can optionally assign one or more topics to it.
See the :ref:`topics section <topics>` for more details.