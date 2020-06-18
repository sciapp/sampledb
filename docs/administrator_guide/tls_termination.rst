.. _tls_termination:

TLS Termination
===============

The SampleDB container comes with a built-in, production ready CherryPy web server which serves SampleDB via HTTP on port 8000. This is great for local testing, but if you run SampleDB in production, you should use HTTPS instead.

The recommended way of doing this is to set up an nginx container as a so-called *reverse proxy* that will handle TLS termination. Clients will send requests to nginx using HTTPS and nginx will internally communicate to the SampleDB container using HTTP.

You may have existing infrastructure which you can integrate SampleDB into, this guide is merely an example in case you are starting on a completely fresh system.

Please follow general system administration best practices.

Requirements
------------

To follow this guide and set up TLS termination, you will need:

- a domain name that is mapped to your host
- a TLS certificate, saved as ``certificate.crt``
- the corresponding private key, saved as ``certificate.key``

Your facility is likely to already have a domain name, and you may be able to use one of its subdomains, e.g. ``sampledb.yourdomain.tld``. If so, there likely is an established certficate authority your facility uses. If not, consider using a certificate authority like https://letsencrypt.org/.

Docker network
--------------

The first step is to make sure the three containers run in their own Docker network, so that they can communicate with each other while port 8000 of the SampleDB container will only be reachable internally:

.. code-block:: bash

    docker network create --driver=bridge --subnet=172.24.0.0/16 sampledb-network

Next, assign IP addresses to the individual containers. The rest of this guide assumes that you use:

=================  ==========
container          IP address
=================  ==========
sampledb           172.24.0.1
sampledb-postgres  172.24.0.2
sampledb-nginx     172.24.0.3
=================  ==========

When creating the containers with ``docker run``, pass the network and IP address to docker, by using the option:

.. code-block:: bash

    --network=sampledb-network --ip=<ip_address>

Also make sure to remove the ``-p 8000:8000`` option from the SampleDB container.

nginx Configuration
-------------------

You can then create a ``sampledb.conf`` file for nginx:

.. code-block::

    upstream sampledb {
       server 172.24.0.1:8000;
    }

    ssl_session_cache shared:ssl_session_cache:10m;

    server {
        listen              80;
        server_name         <domain_name>;
        return              301 https://$server_name$request_uri;
    }
    server {
        listen              443 ssl;
        server_name         <domain_name>;
        ssl_certificate     certificate.crt;
        ssl_certificate_key certificate.key;
        ssl_protocols       TLSv1.2;
        ssl_ciphers         "EECDH+AESGCM:EDH+AESGCM:!aNULL";
        ssl_prefer_server_ciphers on;
        ssl_dhparam         dhparam.pem;

        add_header Strict-Transport-Security max-age=63072000;
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;

        client_max_body_size 64M;

        location / {
            proxy_redirect     off;
            proxy_set_header   Host $host;
            proxy_set_header   X-Real-IP $remote_addr;
            proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
            proxy_pass         http://sampledb;
        }
    }

Note the usage of ``<domain_name>`` and fill in your domain name there.

dhparam.pem
-----------

This configuration file requires the existance of a file ``dhparam.pem`` containing the parameters for the Diffie-Helmann key exchange. To generate this file, run:

.. code-block:: bash

    openssl dhparam -out dhparam.pem 4096

This may take a very long time to run.

nginx Container
---------------

With these files in place, you can start the nginx container:

.. code-block::

    docker run \
        -d \
        -v `pwd`/certificate.crt:/etc/nginx/certificate.crt:ro \
        -v `pwd`/certificate.key:/etc/nginx/certificate.key:ro \
        -v `pwd`/dhparam.pem:/etc/nginx/dhparam.pem:ro \
        -v `pwd`/sampledb.conf:/etc/nginx/conf/default.conf:ro \
        --network=sampledb-network \
        --ip=172.24.0.3 \
        --restart=always \
        --name sampledb-nginx \
        -p 80:80 \
        -p 443:443 \
        nginx

You should now be able to access SampleDB using your domain name and HTTPS.
