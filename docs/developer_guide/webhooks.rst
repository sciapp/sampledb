.. _webhooks:

Webhooks
========

Webhooks can be used to inform an external service about events right after they occurred.
Currently only the object/activity log can be subscribed to, which contains log entries for object creation, updates, new references, comments, files and similar activity.

If webhooks are used, background tasks (see :ref:`SAMPLEDB_ENABLE_BACKGROUND_TASKS <miscellaneous_config>`) should be enabled to handle sending the messages in background without blocking operations which create object log entries.

By default only administrators are allowed to register webhooks. To allow other users using this feature the variable :ref:`SAMPLEDB_ENABLE_WEBHOOKS_FOR_USERS <miscellaneous_config>` has to be set.

Every webhook has a target URL to send a message to if the subscribed log was updated and a secret, to validate a message's contents.

To configure webhooks visit the webhook section on your user preferences page.
Right after creation the webhook secret is displayed to be copied and safely stored by you (see secret validation below).
You can only setup one object log webhook per target.

Handling Webhook Messages
-------------------------

If a webhook has been registered by a user and a new entry in the subscribed log which the user is allowed to access, a HTTP POST request is sent to the Webhooks target URL.
This message contains the object log entries data in JSON (see :ref:`Object Log Entries in the HTTP API section <api_object_log_entries>`) as well as two custom headers:

    * ``X-Sampledb-Event-Type``: The name of the subscribed log. Currently ``Object Log`` is the only possible value.
    * ``X-Sampledb-Signature``: The signature based on the data and the webhooks secret, e.g. ``sha256=6b17ffb207aeb7145fe67a0b81ca75aa8415e70bbade2c9c5a7d3bb830add211``

If you setup a server to handle the webhook messages you should still have in mind, that the communication between |service_name| and webhook handler might not always be possible.
|service_name| does not retry if the communication was not successful.
Therefore you should check for new events in the object log using the :ref:`object_log_entries API endpoint <api_object_log_entries>` regularly.

Exemplary POST request:

.. sourcecode:: http

    POST /webhook/ HTTP/1.1
    Host: example.com
    User-Agent: python-requests/2.31.0
    Accept-Encoding: gzip, deflate, br
    Accept: */*
    Connection: keep-alive
    X-Sampledb-Event-Type: OBJECT_LOG
    X-Sampledb-Signature: sha256=6b17ffb207aeb7145fe67a0b81ca75aa8415e70bbade2c9c5a7d3bb830add211
    Content-Length: 148
    Content-Type: application/json

    {
        "log_entry_id": 124,
        "type": "EDIT_OBJECT",
        "object_id": 34,
        "user_id": 1,
        "data": {
            "version_id": 7
        },
        "utc_datetime": "2015-05-03 12:34:56"
    }

You can validate the signature as shown in the following python code snippet:

.. sourcecode:: python

    import hashlib
    import hmac

    def verify_signature(payload_body, secret, signature_header):
        """
        Verify that the payload was sent from SampleDB by validating SHA256.

        :param payload_body: original request body to verify
        :param secret: SampleDB webhook secret
        :param signature_header: header received from SampleDB (X-Sampledb-Signature)
        """
        if not signature_header:
            # signature header (X-Sampledb-Signature) is missing
            # you might want to raise an appropriate exception here and return the status code 403 Forbidden
            raise Exception()
        hash_object = hmac.new(secret.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
        expected_signature = "sha256=" + hash_object.hexdigest()
        if not hmac.compare_digest(expected_signature, signature_header):
            # signatures do not match
            # you might want to raise an appropriate exception here and return the status code 403 Forbidden
            raise Exception()
