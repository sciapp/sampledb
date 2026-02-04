.. _backup_and_restore:

Backup and Restore
==================

SampleDB stores all its information a PostgreSQL database, so to create a backup of SampleDB, you will need to create a backup of this database.

It is recommended that you stop the SampleDB container before creating backups and start it again afterwards.

While you yourself will need to decide when and how exactly you want to create backups, the following section shows examples of how backups can be created.

Please follow general system administration best practices.

The PostgreSQL database
-----------------------

One way of creating a backup of a PostgreSQL database is to create an SQL dump using the `pg_dump` tool:

.. code-block:: bash

    docker exec sampledb-postgres pg_dump -U postgres postgres > backup.sql

The resulting ``backup.sql`` file can then be copied to another system.

To restore the PostgreSQL database from such an SQL dump, you should first remove the existing database:

.. code-block:: bash

    docker stop sampledb-postgres
    docker rm sampledb-postgres
    rm -rf pgdata

You can then recreate the database container and restore the backup using the ``psql`` tool:

.. code-block:: bash

    docker run \
        -d \
        -e POSTGRES_PASSWORD=password \
        -e PGDATA=/var/lib/postgresql/data/pgdata \
        -v `pwd`/pgdata:/var/lib/postgresql/data/pgdata:rw \
        --restart=always \
        --name sampledb-postgres \
        postgres:15
    docker exec -i sampledb-postgres psql -U postgres postgres < backup.sql

If you have set different options for the database container before, e.g. setting it in a specific network and giving it a fixed IP, you should also set these options here.

For more information on backing up a PostgreSQL database and restoring a backup, see the `PostgreSQL documentation on Backup and Restore <https://www.postgresql.org/docs/current/backup.html>`_

Differential Backup Using Borgmatic
-----------------------------------

In case of large databases, the additional space required for more than one backup can be prohibitive. Differential backups instead only save changes since the last full backup. 

`Borg <https://www.borgbackup.org/>`_ is a well-established tool for performing differential backups. `Borgmatic <https://torsion.org/borgmatic/>`_ provides it in a docker container and adds some utility. Both are free and open source software.

For this configuration we suggest the use of docker compose. Change to the directory containing your compose file and create the directories required for borgmatic:

.. code-block:: bash

	mkdir -p data/{borgmatic.d,repository,.config,.ssh,.cache}
	
Add the borgmatic container as backup service to your compose file named for example ``compose.yaml`` (minimal working example):

.. code-block:: yaml

	services:
	  backup:
	  image: ghcr.io/borgmatic-collective/borgmatic:2.0.12
	  container_name: borgmatic
	  restart: always
	  volumes:
	    - /var/run/docker.sock:/var/run/docker.sock
	    - ./data/repository:/mnt/borg-repository
	    # This binds to the config file directory. Set repo and postgres password (same as in sampledb-postgres) there.
	    - ./data/borgmatic.d:/etc/borgmatic.d/
	    - ./data/.config/borg:/root/.config/borg
	    - ./data/.ssh:/root/.ssh
	    - ./data/.cache/borg:/root/.cache/borg
	    - ./data/.state/borgmatic:/root/.local/state/borgmatic
	  environment:
	    - TZ=Europe/Berlin
	    - DOCKERCLI=true
	    - BACKUP_CRON=00 03 * * *
	  
	  sampledb:
	  image: sciapp/sampledb:0.32.0
	  container_name: sampledb
	  ports:
	    - 8000:8000
	  environment:
	    - SAMPLEDB_CONTACT_EMAIL=admin@example.com
	    - SAMPLEDB_MAIL_SERVER=mail.example.com
	    - SAMPLEDB_MAIL_SENDER=sampledb@example.com
	    - SAMPLEDB_ADMIN_PASSWORD=password
	    # This variable includes the postgres password, set it the same as in the sampledb-postgres service.
	    - SAMPLEDB_SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://postgres:password@sampledb-postgres:5432/postgres
	  restart: always
	  depends_on:
	    - sampledb-postgres
	  
	  sampledb-postgres:
	  image: postgres:15
	  container_name: sampledb-postgres
	  environment:
	    - POSTGRES_PASSWORD=password
	    - PGDATA=/var/lib/postgresql/data/pgdata
	  volumes:
	    - pgdata:/var/lib/postgresql/data/pgdata:rw
	  restart: always

In ``./data/borgmatic.d`` create ``config.yaml``. This conifguartion file should look like this:

.. code-block:: yaml

	source_directories: []
	
	repositories:
	  - path: /mnt/borg-repository/repo
	one_file_system: true
	read_special: true
	
	encryption_passphrase: "DoNotForgetToChangeYourPassphrase"
	compression: lz4
	archive_name_format: 'backup-{now}'
	
	keep_daily: 7
	keep_weekly: 4
	keep_monthly: 12
	keep_yearly: 10
	
	checks:
	  - name: repository
		frequency: 2 weeks
	  - name: archives
		frequency: always
	  - name: extract
		frequency: 2 weeks
	  - name: data
		frequency: 1 month
	
	postgresql_databases:
	  - name: all
		hostname: sampledb-postgres
		port: 5432
		username: postgres
		password: password
	
	commands:
	  - before: repository
		when:
	      - create
	      - prune
	      - compact
		run:
	      - echo "`date` - Starting backup create/prune/compact."
		  - docker stop sampledb
	
	- after: repository
		when:
		  - create
		  - prune
		  - compact
		run:
		  - echo {containernames} | xargs docker start
		  - docker start sampledb
	
	- after: error
		run:
		  - echo "Error during borgmatic action."
	  
Start all involved containers and use this command to initialize the repository:

.. code-block:: bash

	docker exec -it backup borgmatic --verbosity 1 init --encryption repokey
	
Secure the repository keys, by exporting them and backing them up at a secure location:

.. code-block:: bash

	docker exec -it backup borg key export --paper /mnt/borg-repository/repo encrypted-key-backup.txt

Do a manual backup to see if everything works as intended:

.. code-block:: bash

	docker exec -it backup borgmatic --stats --verbosity 1
	
To restore, first clear the database container and associated data, just as above:

.. code-block:: bash

	docker compose down sampledb-postgres
	docker volume rm docker_pgdata
	rm -rf /opt/docker/sampledb/volumes/pgdata
	
Then recreate the directory and database container:

.. code-block:: bash

	mkdir /opt/docker/sampledb/volumes/pgdata/
	docker compose up -d sampledb-postgres
	
And, finally, restore the latest archive of the database using borgmatic:

.. code-block:: bash

	docker exec -it backup borgmatic --verbosity 1 extract --config /etc/borgmatic.d/wiki_config.yaml --archive latest
	
Find further information on borgmatic and its database backup and restore in its `documentation <https://torsion.org/borgmatic/how-to/backup-your-databases/>`_.
