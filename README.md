# SampleDB

SampleDB is a web-based sample and measurement metadata database.

## Documentation

You can find the documentation for the current release at https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/.

## Getting Started

We recommend using our pre-built Docker images for setting up `SampleDB`. You will need two containers, one for a PostgreSQL database and another for SampleDB itself, and a directory to store all files in. If you would like to set up a development version of SampleDB instead, please see the [contribution guide](https://github.com/sciapp/sampledb/blob/develop/CONTRIBUTING.md).

First, start your database container:

```bash
docker run \
    -d \
    -e POSTGRES_PASSWORD= \
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
    -e SAMPLEDB_MAIL_SERVER=mail.example.com \
    -e SAMPLEDB_MAIL_SENDER=sampledb@example.com \
    -e SAMPLEDB_CONTACT_EMAIL=sampledb@example.com \
    -e SAMPLEDB_SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://postgres:@sampledb-postgres:5432/postgres \
    -e SAMPLEDB_FILE_STORAGE_PATH=/home/sampledb/files/ \
    -v `pwd`/files:/home/sampledb/files:rw \
    --restart=always \
    --name sampledb \
    -p 8000:8000 \
    sciapp/sampledb:0.8.1
```

This will start a basic SampleDB instance at `http://localhost:8000`.

To use the administration scripts, run:

```bash
docker exec sampledb env/bin/python -m sampledb help
```

and replace `help` with the script you want to run.

### Next steps:

- You can set additional [configuration environment variables](https://scientific-it-systems.iffgit.fz-juelich.de/SampleDB/developer_guide/configuration.html) to customize or enable some features, including LDAP authentication and JupyterHub integration. You should at least configure a valid mail server, sender and contact email.

- You can use the administration scripts to create instruments, actions and bot users for use with the WebAPI.

- If you wish to run SampleDB in production, please ensure that you make backups of your database and the file directory, and ensure that your server stays secure. We strongly recommend placing SampleDB behind an nginx reverse proxy for TLS termination.

- To update an existing SampleDB instance, please create a full backup and then start the SampleDB container using the new image.

## Contributing

If you want to improve SampleDB, please read the [contribution guide](https://github.com/sciapp/sampledb/blob/develop/CONTRIBUTING.md) for a few notes on how to report issues or submit changes.
