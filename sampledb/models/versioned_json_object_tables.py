# coding: utf-8
"""

"""

import collections
import datetime
import sqlalchemy as db
import sqlalchemy.dialects.postgresql as postgresql

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class VersionedJSONSerializableObjectTables(object):
    """
    A class for storing JSON-serializable objects without deletes and with versioned updates.

    The class uses two tables, one for the current objects and one for previous versions of these objects. Each
    object consists of an object ID, a version ID, the actual data, a JSON schema for the data and information about
    this current version (the ID of this version's author and a datetime of when the object was created or updated).

    These two tables will be created when the instance of this class is created, if bind is provided. Otherwise you
    can use the metadata attribute to access the SQLAlchemy MetaData object associated with these tables. You can then
    call metadata.create_all(bind) to create the tables.

    You should **not** interact with the tables yourself. Instead, use the functions provided by this class.

    For information on JSON schemas, see http://json-schema.org/.
    """

    VersionedJSONSerializableObject = collections.namedtuple(
        'VersionedJSONSerializableObject',
        [
            'object_id',
            'version_id',
            'action_id',
            'data',
            'schema',
            'user_id',
            'utc_datetime'
        ]
    )

    def __init__(self, table_name_prefix, bind=None, object_type=VersionedJSONSerializableObject, user_id_column=None, action_id_column=None, action_schema_column=None, metadata=None, create_object_callbacks=None, data_validator=None, schema_validator=None):
        """
        Creates new instance for storing versioned, JSON-serializable objects using two tables.

        :param table_name_prefix: the prefix used for naming the two used tables
        :param bind: the SQLAlchemy engine used for creating the tables and for future connections
        :param object_type: the type used for returning objects
        :param user_id_column: a SQLAlchemy column object for use as foreign key for the user ID (optional)
        :param action_id_column: a SQLAlchemy column object for use as foreign key for the action ID (optional)
        :param metdata: an SQLAlchemy MetaData object used for creating the two tables (optional)
        :param create_object_callbacks: a list of callables which will be called when an object is created (optional)
        :param data_validator: a data validator function (given the data and the schema) (optional)
        :param schema_validator: a schema validator function (given the schema) (optional)
        """
        if metadata is None:
            metadata = db.MetaData()
        self.metadata = metadata
        self._current_table = db.Table(
            table_name_prefix+'_current',
            self.metadata,
            db.Column('object_id', db.Integer, nullable=False, primary_key=True, autoincrement=True),
            db.Column('version_id', db.Integer, nullable=False, default=0),
            db.Column('action_id', db.Integer, nullable=False),
            db.Column('data', postgresql.JSONB, nullable=False),
            db.Column('schema', postgresql.JSONB, nullable=False),
            db.Column('user_id', db.Integer, nullable=False),
            db.Column('utc_datetime', db.DateTime, nullable=False)
        )
        self._previous_table = db.Table(
            table_name_prefix+'_previous',
            self.metadata,
            db.Column('object_id', db.Integer, nullable=False),
            db.Column('version_id', db.Integer, nullable=False),
            db.Column('action_id', db.Integer, nullable=False),
            db.Column('data', postgresql.JSONB, nullable=False),
            db.Column('schema', postgresql.JSONB, nullable=False),
            db.Column('user_id', db.Integer, nullable=False),
            db.Column('utc_datetime', db.DateTime, nullable=False),
            db.PrimaryKeyConstraint('object_id', 'version_id')
        )
        if user_id_column is not None:
            self._current_table.append_constraint(db.ForeignKeyConstraint(['user_id'], [user_id_column]))
            self._previous_table.append_constraint(db.ForeignKeyConstraint(['user_id'], [user_id_column]))
        if action_id_column is not None:
            self._current_table.append_constraint(db.ForeignKeyConstraint(['action_id'], [action_id_column]))
            self._previous_table.append_constraint(db.ForeignKeyConstraint(['action_id'], [action_id_column]))
        elif action_schema_column is not None:
            raise ValueError("Using action_schema_column requires using the action_id_column as well!")
        self._action_id_column = action_id_column
        self._action_schema_column = action_schema_column
        self.object_type = object_type
        self.object_id_column = self._current_table.c.object_id
        if create_object_callbacks is None:
            create_object_callbacks = []
        self.create_object_callbacks = create_object_callbacks
        self.bind = bind
        if self.bind is not None:
            self.metadata.create_all(self.bind)
        self._data_validator = data_validator
        self._schema_validator = schema_validator

    def create_object(self, data, schema, user_id, action_id, utc_datetime=None, connection=None):
        """
        Creates an object in the table for current objects. This object will always have version_id 0.

        :param data: a JSON serializable object containing the object data
        :param schema: a JSON schema describing data (may be None if action's schema is to be used)
        :param user_id: the ID of the user who created the object
        :param action_id: the ID of the action which was used to create the object
        :param utc_datetime: the datetime (in UTC) when the object was created (optional, defaults to utcnow())
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: the newly created object as object_type
        """
        if connection is None:
            connection = self.bind.connect()
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        if schema is None and self._action_schema_column is not None:
            action = connection.execute(
                db
                .select([
                    self._action_schema_column
                ])
                .where(self._action_id_column == action_id)
            ).fetchone()
            if action is None:
                raise ValueError('Action with id {} not found'.format(action_id))
            schema = action[0]
        if self._schema_validator:
            self._schema_validator(schema)
        if self._data_validator:
            self._data_validator(data, schema)
        version_id = 0
        object_id = connection.execute(
            self._current_table
            .insert()
            .values(
                version_id=version_id,
                action_id=action_id,
                data=data,
                schema=schema,
                user_id=user_id,
                utc_datetime=utc_datetime
            )
            .returning(
                self._current_table.c.object_id
            )
        ).scalar()
        obj = self.object_type(
            object_id=object_id,
            version_id=version_id,
            action_id=action_id,
            data=data,
            schema=schema,
            user_id=user_id,
            utc_datetime=utc_datetime
        )
        for create_object_callback in  self.create_object_callbacks:
            create_object_callback(obj)
        return obj

    def update_object(self, object_id, data, schema, user_id, utc_datetime=None, connection=None):
        """
        Updates an existing object using the given data, user id and datetime.

        This step first copies the existing object in the table of previous object versions and then modifies the
        object's version id, incrementing it by one, and data, replacing it by the given data.

        :param object_id: the ID of the existing object
        :param data: a JSON serializable object containing the updated object data
        :param schema: a JSON schema describing data
        :param user_id: the ID of the user who updated the object
        :param utc_datetime: the datetime (in UTC) when the object was updated (optional, defaults to utcnow())
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: the updated object as object_type
        """
        if connection is None:
            connection = self.bind.connect()
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        if self._schema_validator:
            self._schema_validator(schema)
        if self._data_validator:
            self._data_validator(data, schema)
        with connection.begin() as transaction:
            # Copy current version to previous versions
            assert connection.execute(
                self._previous_table
                .insert()
                .from_select(
                    ['object_id', 'version_id', 'action_id', 'data', 'schema', 'user_id', 'utc_datetime'],
                    self._current_table
                    .select()
                    .where(self._current_table.c.object_id == db.bindparam('oid'))
                ),
                [{'oid': object_id}]
            ).rowcount == 1
            # Update current version to new version
            version_id = connection.execute(
                self._current_table
                .update()
                .where(self._current_table.c.object_id == db.bindparam('oid'))
                .values(
                    version_id=self._current_table.c.version_id + 1,
                    data=data,
                    schema=schema,
                    user_id=user_id,
                    utc_datetime=utc_datetime
                )
                .returning(
                    self._current_table.c.version_id
                ),
                [{'oid': object_id}]
            ).scalar()
            transaction.commit()
        return self.get_current_object(object_id, connection=connection)

    def get_current_object(self, object_id, connection=None):
        """
        Queries and returns an object by its ID.

        :param object_id: the ID of the existing object
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: the object as object_type or None if the object does not exist
        """
        if connection is None:
            connection = self.bind.connect()
        current_object = connection.execute(
            db
            .select([
                self._current_table.c.object_id,
                self._current_table.c.version_id,
                self._current_table.c.action_id,
                self._current_table.c.data,
                self._current_table.c.schema,
                self._current_table.c.user_id,
                self._current_table.c.utc_datetime
            ])
            .where(self._current_table.c.object_id == object_id)
        ).fetchone()
        if current_object is None:
            return None
        return self.object_type(*current_object)

    def get_current_objects(self, filter_func=lambda data: True, connection=None):
        """
        Queries and returns all objects matching a given filter.

        :param filter_func: a lambda that may return an SQLAlchemy filter when given a table
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: a list of objects as object_type
        """
        if connection is None:
            connection = self.bind.connect()
        objects = connection.execute(
            db
            .select([
                self._current_table.c.object_id,
                self._current_table.c.version_id,
                self._current_table.c.action_id,
                self._current_table.c.data,
                self._current_table.c.schema,
                self._current_table.c.user_id,
                self._current_table.c.utc_datetime
            ])
            .where(filter_func(self._current_table.c.data))
        ).fetchall()
        return [self.object_type(*obj) for obj in objects]

    def get_object_versions(self, object_id, connection=None):
        """
        Queries and returns all versions of an object with a given ID, sorted ascendingly by the version ID, from first
        version to current version.

        :param object_id: the ID of the existing object
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: a list of objects as object_type
        """
        if connection is None:
            connection = self.bind.connect()
        current_object = self.get_current_object(object_id, connection=connection)
        if current_object is None:
            return []
        previous_objects = connection.execute(
            db
            .select([
                self._previous_table.c.object_id,
                self._previous_table.c.version_id,
                self._previous_table.c.action_id,
                self._previous_table.c.data,
                self._previous_table.c.schema,
                self._previous_table.c.user_id,
                self._previous_table.c.utc_datetime
            ])
            .where(self._previous_table.c.object_id == object_id)
            .order_by(db.asc(self._previous_table.c.version_id))
        ).fetchall()
        objects = []
        for obj in previous_objects:
            objects.append(self.object_type(*obj))
        objects.append(current_object)
        return objects

    def get_object_version(self, object_id, version_id, connection=None):
        """
        Queries and returns an individual version of an object with a given object and version ID.

        :param object_id: the ID of the existing object
        :param version_id: the ID of the object's existing version
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: the object as object_type or None if the object or this version of it does not exist
        """
        if connection is None:
            connection = self.bind.connect()
        previous_objects = connection.execute(
            db
            .select([
                self._previous_table.c.object_id,
                self._previous_table.c.version_id,
                self._previous_table.c.action_id,
                self._previous_table.c.data,
                self._previous_table.c.schema,
                self._previous_table.c.user_id,
                self._previous_table.c.utc_datetime
            ])
            .where(db.and_(
                self._previous_table.c.object_id == object_id,
                self._previous_table.c.version_id == version_id
            ))
        ).fetchall()
        if previous_objects:
            return self.object_type(*previous_objects[0])
        current_object = self.get_current_object(object_id, connection=connection)
        if current_object is not None and current_object.version_id == version_id:
            return current_object
        return None

    def restore_object_version(self, object_id, version_id, user_id, utc_datetime=None, connection=None):
        """
        Reverts the changes made to an object and restores a specific version of it, while keeping the version history.
        This function merely adds a new version which sets the data and schema to those of the given version.

        :param object_id: the ID of the existing object
        :param version_id: the ID of the object's existing version
        :param user_id: the ID of the user who restored the object version
        :param utc_datetime: the datetime (in UTC) when the version was restored (optional, defaults to utcnow())
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: the object as object_type or None if the object or this version of it does not exist
        """
        if connection is None:
            connection = self.bind.connect()
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        object_version = self.get_object_version(object_id=object_id, version_id=version_id)
        if object_version is None:
            return None
        return self.update_object(
            object_id=object_id,
            data=object_version.data,
            schema=object_version.schema,
            user_id=user_id,
            utc_datetime=utc_datetime,
            connection=connection
        )
