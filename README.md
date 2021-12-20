# SampleDB

[![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.md)
[![DOI](https://zenodo.org/badge/221237572.svg)](https://zenodo.org/badge/latestdoi/221237572)
[![DOI](https://joss.theoj.org/papers/10.21105/joss.02107/status.svg)](https://doi.org/10.21105/joss.02107)

SampleDB is a web-based sample and measurement metadata database.

## Documentation

You can find the documentation for the current release at https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/.

## Getting Started

We recommend using our pre-built Docker images for setting up `SampleDB`. You will need two containers, one for a PostgreSQL database and another for SampleDB itself, and a directory to store all files in.

If you would like to set up a development version of SampleDB instead, please see the [contribution guide](https://github.com/sciapp/sampledb/blob/develop/CONTRIBUTING.md).

If you do not have Docker installed yet, please [install Docker](https://docs.docker.com/engine/install/).

### Using docker-compose

First, get the [docker-compose.yml](https://raw.githubusercontent.com/sciapp/sampledb/develop/docker-compose.yml) configuration file. You can git clone this repo or just get the file:

```bash
curl https://raw.githubusercontent.com/sciapp/sampledb/develop/docker-compose.yml --output docker-compose.yml
```

Then simply bring everything up with:

```bash
docker-compose up -d
```

### Using docker commands

First, start your database container:

```bash
docker run \
    -d \
    -e POSTGRES_PASSWORD=password \
    -e PGDATA=/var/lib/postgresql/data/pgdata \
    -v `pwd`/pgdata:/var/lib/postgresql/data/pgdata:rw \
    --restart=always \
    --name sampledb-postgres \
    postgres:12
```

Next, start the SampleDB container:

```bash
docker run \
    -d \
    --link sampledb-postgres \
    -e SAMPLEDB_CONTACT_EMAIL=sampledb@example.com \
    -e SAMPLEDB_MAIL_SERVER=mail.example.com \
    -e SAMPLEDB_MAIL_SENDER=sampledb@example.com \
    -e SAMPLEDB_ADMIN_PASSWORD=password \
    -e SAMPLEDB_SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://postgres:password@sampledb-postgres:5432/postgres \
    -e SAMPLEDB_FILE_STORAGE_PATH=/home/sampledb/files/ \
    -v `pwd`/files:/home/sampledb/files:rw \
    --restart=always \
    --name sampledb \
    -p 8000:8000 \
    sciapp/sampledb:0.19.1
```

### Once it's started

This will start a minimal SampleDB installation at `http://localhost:8000` and allow you to sign in with the username `admin` and the password `password` (which you should change immediately after signing in).

To learn how to further set up SampleDB, please follow the rest of the [Getting Started guide](https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/administrator_guide/getting_started.html).

## Contributing

If you want to improve SampleDB, please read the [contribution guide](https://github.com/sciapp/sampledb/blob/develop/CONTRIBUTING.md) for a few notes on how to report issues or submit changes.

## Support

If you have any questions about SampleDB or run into any issues setting up or running SampleDB, please [open an issue on GitHub](https://github.com/sciapp/sampledb/issues/new).
