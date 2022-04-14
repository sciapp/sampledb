.. _administration_scripts:

Administration Scripts
======================

Most administration features are available to administrators through the user interface. Some features which are rarely used or which would be useful for scripting purposes are available as scripts, so that they can be run using the SampleDB command line interface.

If you are running SampleDB using Docker, you can execute these scripts using ``docker exec``. To make it easier, you can set an alias like so:

.. code-block:: bash

   alias sdb="docker exec -it sampledb sampledb"

Add this in your .bashrc or .zshrc depending if you use respectively bash or zsh as shell.

To get a list of all available scripts, you can run:

.. code-block:: bash

    sdb help

To then get a list of all actions, for example, you can run:

.. code-block:: bash

    sdb list_actions

To get information on how to run one of these scripts, you can run pass the `help` parameter to it:

.. code-block:: bash

    sdb list_actions help
