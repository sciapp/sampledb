.. _actions:

Actions
=======

Processes like **creating a sample**, **performing a measurement** or **running a simulation** are represented as actions in |service_name| and whenever such an action is performed a new :ref:`Object <objects>` should be created in |service_name|.

Either generic or associated with an :ref:`Instrument <instruments>`, each action contains a name, a description and a :ref:`Schema <metadata>`.

You can view a list of actions at |service_actions_url|. Similar to instruments, users can select **favorites** by clicking the star next to an action's name.

.. _action_types:

Action Types
------------

The type of an Action describes the general kind of process it represents, such as **Sample Creation**. There are four built-in action types for creating samples, performing a measurement, running a simulation, and for use as schema templates. Administrators can create additional custom action types.
Schema templates have a special role, as they are usually not used like other actions. Instead, actions marked for use as a schema template can be included in the schemas of other actions.

.. _action_topics:

Topics
------

Topics allow you to filter the action list by predefined topics.
When creating or editing an action, you can optionally assign one or more topics to the action.
See the :ref:`topics section <topics>` for more details.

Custom Actions
--------------

Users can create custom actions to represent their own processes or instruments that are not yet part of |service_name|. These actions can be private, only usable by the users who created them, or public, so all everyone can see and use them, or the user can grant permissions to specific users, basic groups or project groups.

To create a custom action, users can either use an existing action as a template or write a :ref:`Schema <metadata>` from scratch.

.. note::
    Custom Actions are an advanced feature that most users of |service_name| will not need. If you would like your instrument or action to be included without writing your own schema, please `let us know`_.

    .. only:: iffSamples

        If you would like to try working with custom actions, please `use the development and testing deployment of iffSamples <https://docker.iff.kfa-juelich.de/dev-sampledb/>`_.
