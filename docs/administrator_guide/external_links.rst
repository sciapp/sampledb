.. _external_links:

External Links
==============

While external links can be included in the Markdown-formatted descriptions of
many entities in SampleDB, there may be some links you might want to include
in a more prominent way, e.g. to direct users to internal dashboards or other
services. The ``SAMPLEDB_EXTERNAL_LINKS`` environment variable can be used to
configure such links.

The links specified will be shown as one or more dropdown buttons with a label, an icon and a list of links, each with an URL and a name:

.. figure:: ../static/img/generated/external_links.png
    :alt: External links for an action

    External links for an action

This configuration variable must be a JSON-encoded list containing one or more dicts containing the following fields:

 * ``label`` the label for the dropdown button, as a string or a dict mapping language codes to translated labels (default: ``{"en": "Links"}``)
 * ``icon`` the `FontAwesome v4 icon class <https://fontawesome.com/v4/icons/>`_ (default: ``fa-external-link``)
 * ``links`` a list containing dicts with ``url`` set to the URL and ``name`` set to the name of the link, either as string or as dict mapping language codes to translated names
 * ``applies_to`` a dict mapping the following keys to lists containing integer IDs or the string ``"*"`` as a wildcard for all IDs: ``objects_by_action_id``, ``actions_by_action_id``, ``instruments_by_instrument_id``, ``topics_by_topic_id``, ``basic_groups_by_basic_group_id``, ``project_groups_by_project_group_id``. Each of these keys controls where the links should be shown, e.g. the ID list for ``objects_by_action_id`` set the links to be shown for objects with the given action IDs.
 * ``applies_to_placeholder`` the placeholder used for inserting the kind of entity the link is applied to in URLs, e.g. ``object`` for ``objects_by_action_id`` or ``topic`` for ``topics_by_topic_id``, (default: ``<A>``)
 * ``id_placeholder`` the placeholder used for inserting the current ID in URLs (default: ``<ID>``)

As an example, the following would be a valid value for ``SAMPLEDB_EXTERNAL_LINKS``:

.. code-block:: json
    :caption: A configuration for adding a link to the current object page to objects of every action

    [
      {
        "label": "Links",
        "icon": "fa-external-link",
        "id_placeholder": "<ID>",
        "links": [
          {
            "url": "https://example.org/objects/<ID>",
            "name": "Object Page"
          }
        ],
        "applies_to": {
          "objects_by_action_id": ["*"]
        }
      }
    ]
