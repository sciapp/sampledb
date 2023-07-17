.. _api_tutorial:

Using the HTTP API
==================

SampleDB provides an :ref:`http_api` which can be used to **automate processes**, both for data entry and for using data stored in SampleDB. Most actions that can be performed via the web frontend can also be performed via the API.

To authorize with the API, you can either use `Basic Authentication <https://tools.ietf.org/html/rfc7617>`_ using your normal credentials. However it is recommended to create an **API token** instead and then use `Bearer Authentication <https://tools.ietf.org/html/rfc6750>`_. API tokens can be created in your user preferences, where you can also view the log for each API token, listing how it was used.

.. figure:: ../static/img/generated/api_token_list.png
    :alt: API tokens

    API tokens

The HTTP API can be used from various programming languages, e.g. Python:

.. code-block:: python
  :caption: An example script for fetching all readable objects from a SampleDB instance

  import requests

  SERVER_URL = 'https://example.org'
  API_TOKEN = 'bf4e16afa966f19b92f5e63062bd599e5f931faeeb604bdc3e6189539258b155'

  r = requests.get(
      f"{SERVER_URL}/api/v1/objects/",
      headers={"Authorization": f"Bearer {API_TOKEN}"}
  )
  print(r.json())

The full list of HTTP API endpoints can be found in the :ref:`http_api` documentation. While many endpoints are used for reading, like in the example above, others will perform changes in the SampleDB instance by creating or updating entries. These may need to be supplied with additional information, formatted as `JSON <https://datatracker.ietf.org/doc/html/rfc8259>`_ in the request body.

.. code-block:: python
  :caption: An example script for creating a new object

  import requests

  SERVER_URL = 'https://example.org'
  API_TOKEN = 'bf4e16afa966f19b92f5e63062bd599e5f931faeeb604bdc3e6189539258b155'

  r = requests.post(
      f"{SERVER_URL}/api/v1/objects/",
      headers={"Authorization": f"Bearer {API_TOKEN}"},
      json={
          "action_id": 1,
          "data": {
              "name": {
                  "_type": "text",
                  "text": "Example Object"
              }
          }
      }
  )
  print(r.status_code)

.. admonition:: Summary

  - The HTTP API can be used to automate processes.
  - Authentication is handled via username and password or via an API token.
  - Data may need to be provided as JSON.

..  seealso::

  - :ref:`http_api`
  - :ref:`permissions_tutorial`
