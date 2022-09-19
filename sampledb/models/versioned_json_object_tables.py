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

    class VersionedJSONSerializableObject(collections.namedtuple(
            'VersionedJSONSerializableObject',
            [
                'object_id',
                'version_id',
                'action_id',
                'data',
                'schema',
                'user_id',
                'utc_datetime',
                'fed_object_id',
                'fed_version_id',
                'component_id'
            ]
    )):

        _component = None

        @property
        def id(self) -> int:
            return self.object_id

        @property
        def name(self):
            if self.data and self.data.get('name') and self.data.get('name').get('text'):
                return self.data['name']['text']
            else:
                return ''

        @property
        def component(self):
            if self.component_id is not None and self._component is None:
                from ..logic.components import get_component
                self._component = get_component(self.component_id)
            return self._component

    def __init__(self, table_name_prefix, bind=None, object_type=VersionedJSONSerializableObject, user_id_column=None, action_id_column=None, component_id_column=None, action_schema_column=None, metadata=None, create_object_callbacks=None, data_validator=None, schema_validator=None):
        """
        Creates new instance for storing versioned, JSON-serializable objects using three tables.

        :param table_name_prefix: the prefix used for naming the two used tables
        :param bind: the SQLAlchemy engine used for creating the tables and for future connections
        :param object_type: the type used for returning objects
        :param user_id_column: a SQLAlchemy column object for use as foreign key for the user ID (optional)
        :param action_id_column: a SQLAlchemy column object for use as foreign key for the action ID (optional)
        :param metadata: an SQLAlchemy MetaData object used for creating the two tables (optional)
        :param create_object_callbacks: a list of callables which will be called when an object is created (optional)
        :param data_validator: a data validator function (given the data and the schema) (optional)
        :param schema_validator: a schema validator function (given the schema) (optional)
        """
        if metadata is None:
            metadata = db.MetaData()
        self.metadata = metadata
        self._current_table = db.Table(
            table_name_prefix + '_current',
            self.metadata,
            db.Column('object_id', db.Integer, nullable=False, primary_key=True, autoincrement=True),
            db.Column('version_id', db.Integer, nullable=False, default=0),
            db.Column('action_id', db.Integer),
            db.Column('data', postgresql.JSONB),
            db.Column('schema', postgresql.JSONB),
            db.Column('user_id', db.Integer),
            db.Column('utc_datetime', db.DateTime),
            db.Column('fed_object_id', db.Integer),
            db.Column('fed_version_id', db.Integer),
            db.Column('component_id', db.Integer),
            db.Column('name_cache', db.JSON),
            db.Column('tags_cache', db.JSON),
            db.CheckConstraint(
                '(fed_object_id IS NOT NULL AND fed_version_id IS NOT NULL AND component_id IS NOT NULL) OR (action_id IS NOT NULL AND data IS NOT NULL AND schema IS NOT NULL AND user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
                name=table_name_prefix + '_current_not_null_check'
            ),
            db.UniqueConstraint('fed_object_id', 'fed_version_id', 'component_id', name=table_name_prefix + '_current_fed_object_id_component_id_key')
        )
        self._previous_table = db.Table(
            table_name_prefix + '_previous',
            self.metadata,
            db.Column('object_id', db.Integer, nullable=False),
            db.Column('version_id', db.Integer, nullable=False),
            db.Column('action_id', db.Integer, nullable=True),
            db.Column('data', postgresql.JSONB, nullable=True),
            db.Column('schema', postgresql.JSONB, nullable=True),
            db.Column('user_id', db.Integer, nullable=True),
            db.Column('utc_datetime', db.DateTime, nullable=True),
            db.Column('fed_object_id', db.Integer, nullable=True),
            db.Column('fed_version_id', db.Integer, nullable=True),
            db.Column('component_id', db.Integer, nullable=True),
            db.PrimaryKeyConstraint('object_id', 'version_id'),
            db.CheckConstraint(
                '(fed_object_id IS NOT NULL AND fed_version_id IS NOT NULL AND component_id IS NOT NULL) OR (action_id IS NOT NULL AND data IS NOT NULL AND schema IS NOT NULL AND user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
                name=table_name_prefix + '_previous_not_null_check'
            )
        )
        self._subversions_table = db.Table(
            table_name_prefix + '_subversions',
            self.metadata,
            db.Column('object_id', db.Integer, nullable=False),
            db.Column('version_id', db.Integer, nullable=False),
            db.Column('subversion_id', db.Integer, nullable=False),
            db.Column('action_id', db.Integer, nullable=True),
            db.Column('data', postgresql.JSONB, nullable=True),
            db.Column('schema', postgresql.JSONB, nullable=True),
            db.Column('user_id', db.Integer, nullable=True),
            db.Column('utc_datetime', db.DateTime, nullable=True),
            db.Column('utc_datetime_subversion', db.DateTime, nullable=False),
            db.PrimaryKeyConstraint('object_id', 'version_id', 'subversion_id')
        )
        if user_id_column is not None:
            self._current_table.append_constraint(db.ForeignKeyConstraint(['user_id'], [user_id_column]))
            self._previous_table.append_constraint(db.ForeignKeyConstraint(['user_id'], [user_id_column]))
            self._subversions_table.append_constraint(db.ForeignKeyConstraint(['user_id'], [user_id_column]))
        if action_id_column is not None:
            self._current_table.append_constraint(db.ForeignKeyConstraint(['action_id'], [action_id_column]))
            self._previous_table.append_constraint(db.ForeignKeyConstraint(['action_id'], [action_id_column]))
            self._subversions_table.append_constraint(db.ForeignKeyConstraint(['action_id'], [action_id_column]))
        elif action_schema_column is not None:
            raise ValueError("Using action_schema_column requires using the action_id_column as well!")
        if component_id_column is not None:
            self._current_table.append_constraint(db.ForeignKeyConstraint(['component_id'], [component_id_column]))
            self._previous_table.append_constraint(db.ForeignKeyConstraint(['component_id'], [component_id_column]))
        self._action_id_column = action_id_column
        self._action_schema_column = action_schema_column
        self._component_id_column = component_id_column
        self.object_type = object_type
        self.object_id_column = self._current_table.c.object_id
        self.bind = bind
        if self.bind is not None:
            self.metadata.create_all(self.bind)
        self._data_validator = data_validator
        self._schema_validator = schema_validator

    def create_object(self, data, schema, user_id, action_id, utc_datetime=None, fed_object_id=None, fed_version_id=None, component_id=None, connection=None, validate_data=True):
        """
        Creates an object in the table for current objects. This object will always have version_id 0.

        :param data: a JSON serializable object containing the object data
        :param schema: a JSON schema describing data (may be None if action's schema is to be used)
        :param user_id: the ID of the user who created the object
        :param action_id: the ID of the action which was used to create the object
        :param utc_datetime: the datetime (in UTC) when the object was created (optional, defaults to utcnow())
        :param fed_object_id: the ID of this object on a federated component
        :param fed_version_id: the version ID of this object on a federated component
        :param component_id: the ID of the component that created this object
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :param validate_data: whether the data must be validated
        :return: the newly created object as object_type
        """
        if connection is None:
            connection = self.bind.connect()
        if utc_datetime is None and fed_object_id is None:
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
                if fed_object_id is None or fed_version_id is None or component_id is None:
                    raise ValueError('Action with id {} not found'.format(action_id))
                else:
                    schema = None
            else:
                schema = action[0]
        if not (schema is None and fed_object_id is not None and fed_version_id is not None):
            if self._schema_validator:
                self._schema_validator(schema)
            if not (data is None and fed_object_id is not None and fed_version_id is not None):
                if self._data_validator and validate_data:
                    self._data_validator(data, schema)
        version_id = 0
        object_id = connection.execute(
            self._current_table
            .insert()
            .values(
                version_id=version_id,
                action_id=action_id,
                data=data,
                name_cache=data.get('name', {}).get('text') if data else None,
                tags_cache=data.get('tags') if data else None,
                schema=schema,
                user_id=user_id,
                utc_datetime=utc_datetime,
                fed_object_id=fed_object_id,
                fed_version_id=fed_version_id,
                component_id=component_id
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
            utc_datetime=utc_datetime,
            fed_object_id=fed_object_id,
            fed_version_id=fed_version_id,
            component_id=component_id
        )
        return obj

    def update_object(self, object_id, data, schema, user_id, utc_datetime=None, connection=None, validate_schema=True, validate_data=True):
        """
        Updates an existing object using the given data, user id and datetime.

        This step first copies the existing object in the table of previous object versions and then modifies the
        object's version id, incrementing it by one, and data, replacing it by the given data.

        :param object_id: the ID of the existing object
        :param data: a JSON serializable object containing the updated object data
        :param schema: a JSON schema describing data (optional, defaults to the current object schema)
        :param user_id: the ID of the user who updated the object
        :param utc_datetime: the datetime (in UTC) when the object was updated (optional, defaults to utcnow())
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :param validate_schema: whether the schema should be validated
        :param validate_data: whether the data should be validated
        :return: the updated object as object_type or None, if the object does not exist
        """
        if connection is None:
            connection = self.bind.connect()
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        if schema is None:
            schema = connection.execute(
                db.select([self._current_table.c.schema]).where(self._current_table.c.object_id == object_id)
            ).fetchone()
            if schema is None:
                return None
            schema = schema[0]
        if validate_schema and self._schema_validator:
            self._schema_validator(schema)
        if validate_data and self._data_validator:
            self._data_validator(data, schema)

        # Copy current version to previous versions
        if connection.execute(
            self._previous_table
            .insert()
            .from_select(
                ['object_id', 'version_id', 'action_id', 'data', 'schema', 'user_id', 'utc_datetime', 'fed_object_id', 'fed_version_id', 'component_id'],
                self._current_table
                .select()
                .with_only_columns([
                    self._current_table.c.object_id,
                    self._current_table.c.version_id,
                    self._current_table.c.action_id,
                    self._current_table.c.data,
                    self._current_table.c.schema,
                    self._current_table.c.user_id,
                    self._current_table.c.utc_datetime,
                    self._current_table.c.fed_object_id,
                    self._current_table.c.fed_version_id,
                    self._current_table.c.component_id
                ])
                .where(self._current_table.c.object_id == db.bindparam('oid'))
            ),
            [{'oid': object_id}]
        ).rowcount != 1:
            return None
        # Update current version to new version
        connection.execute(
            self._current_table
            .update()
            .where(self._current_table.c.object_id == db.bindparam('oid'))
            .values(
                version_id=self._current_table.c.version_id + 1,
                data=data,
                name_cache=data.get('name', {}).get('text') if data else None,
                tags_cache=data.get('tags') if data else None,
                schema=schema,
                user_id=user_id,
                utc_datetime=utc_datetime
            ),
            [{'oid': object_id}]
        )
        return self.get_current_object(object_id, connection=connection)

    def restore_object_version(self, object_id, version_id, user_id, utc_datetime=None, connection=None):
        object_version = self.get_object_version(object_id=object_id, version_id=version_id, connection=connection)
        if object_version is None:
            return
        if self._schema_validator:
            self._schema_validator(object_version.schema)
        if self._data_validator:
            # allow disabled languages, as they were enabled when the version was created
            self._data_validator(object_version.data, object_version.schema, allow_disabled_languages=True)
        return self.update_object(
            object_id=object_id,
            data=object_version.data,
            schema=object_version.schema,
            user_id=user_id,
            utc_datetime=utc_datetime,
            connection=connection,
            validate_schema=False,
            validate_data=False
        )

    def insert_fed_object_version(self, fed_object_id, fed_version_id, component_id, action_id, data, schema, user_id, utc_datetime, connection=None, allow_disabled_languages: bool = False):
        if connection is None:
            connection = self.bind.connect()

        if schema is None and self._action_schema_column is not None:
            action = connection.execute(
                db
                .select([
                    self._action_schema_column
                ])
                .where(self._action_id_column == action_id)
            ).fetchone()
            if action is None:
                if fed_object_id is None or fed_version_id is None or component_id is None:
                    raise ValueError('Action with id {} not found'.format(action_id))
                else:
                    schema = None
            else:
                schema = action[0]
        validate_data = True
        if not (schema is None and fed_object_id is not None and fed_version_id is not None):
            if self._schema_validator:
                self._schema_validator(schema)
            if not (data is None and fed_object_id is not None and fed_version_id is not None):
                if self._data_validator:
                    self._data_validator(data, schema, allow_disabled_languages=allow_disabled_languages)
                    validate_data = False

        current = self.get_current_fed_object(component_id, fed_object_id)
        if current is None:
            object = self.create_object(data, schema, user_id, action_id, utc_datetime, fed_object_id, fed_version_id, component_id, connection=connection, validate_data=validate_data)
            return object
        elif current.fed_version_id < fed_version_id:
            # Copy current version to previous versions
            if connection.execute(
                self._previous_table
                .insert()
                .from_select(
                    ['object_id', 'version_id', 'action_id', 'data', 'schema', 'user_id', 'utc_datetime', 'fed_object_id', 'fed_version_id', 'component_id'],
                    self._current_table
                    .select()
                    .with_only_columns([
                        self._current_table.c.object_id,
                        self._current_table.c.version_id,
                        self._current_table.c.action_id,
                        self._current_table.c.data,
                        self._current_table.c.schema,
                        self._current_table.c.user_id,
                        self._current_table.c.utc_datetime,
                        self._current_table.c.fed_object_id,
                        self._current_table.c.fed_version_id,
                        self._current_table.c.component_id
                    ])
                    .where(self._current_table.c.object_id == db.bindparam('oid'))
                ),
                [{'oid': current.object_id}]
            ).rowcount != 1:
                return None
            # Update current version to new version
            connection.execute(
                self._current_table
                .update()
                .where(self._current_table.c.object_id == db.bindparam('oid'))
                .values(
                    object_id=current.object_id,
                    version_id=self._current_table.c.version_id + 1,
                    data=data,
                    name_cache=data.get('name', {}).get('text') if data else None,
                    tags_cache=data.get('tags') if data else None,
                    schema=schema,
                    action_id=action_id,
                    user_id=user_id,
                    utc_datetime=utc_datetime,
                    fed_object_id=fed_object_id,
                    fed_version_id=fed_version_id,
                    component_id=component_id
                ),
                [{'oid': current.object_id}]
            )
        else:
            max_version_id = connection.execute(db.select(db.func.max(self._previous_table.c.version_id)).where(db.and_(self._previous_table.c.object_id == current.object_id))).scalar()
            if max_version_id is None:
                max_version_id = -1
            if connection.execute(
                self._previous_table
                .insert()
                .values(
                    object_id=current.object_id,
                    version_id=max(max_version_id, current.version_id) + 1,
                    action_id=action_id,
                    data=data,
                    schema=schema,
                    user_id=user_id,
                    utc_datetime=utc_datetime,
                    fed_object_id=fed_object_id,
                    fed_version_id=fed_version_id,
                    component_id=component_id
                ),
                [{'oid': current.object_id}]
            ).rowcount != 1:
                return None
        return self.get_fed_object_version(component_id, fed_object_id, fed_version_id, connection=connection)

    def update_object_version(self, object_id, version_id, action_id, schema, data, user_id, utc_datetime, utc_datetime_subversion=None, connection=None, allow_disabled_languages: bool = False):
        """
        Updates an existing object version using the given data, user id and datetime.

        This step first copies the existing object version in the table of object subversions and then modifies the
        data, replacing it by the given data.

        :param object_id: the ID of the existing object
        :param version_id: the version ID of the existing object
        :param data: a JSON serializable object containing the updated object data
        :param schema: a JSON schema describing data (optional, defaults to the current object schema)
        :param user_id: the ID of the user who updated the object
        :param utc_datetime: the datetime (in UTC) when the object was updated
        :param utc_datetime_subversion: the datetime (in UTC) when the object update has been applied (optional, defaults to utcnow())
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: the updated object as object_type or None, if the object does not exist
        """
        if connection is None:
            connection = self.bind.connect()
        if utc_datetime_subversion is None:
            utc_datetime_subversion = datetime.datetime.utcnow()
        if schema is None and self._action_schema_column is not None:
            action = connection.execute(
                db
                .select([
                    self._action_schema_column
                ])
                .where(self._action_id_column == action_id)
            ).fetchone()
            if action is None:
                schema = None
            else:
                schema = action[0]
        if schema is not None:
            if self._schema_validator:
                self._schema_validator(schema)
            if data is not None:
                if self._data_validator:
                    self._data_validator(data, schema, allow_disabled_languages=allow_disabled_languages)

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
                self._previous_table.c.utc_datetime,
                self._previous_table.c.fed_object_id,
                self._previous_table.c.fed_version_id,
                self._previous_table.c.component_id
            ])
            .where(db.and_(
                self._previous_table.c.object_id == object_id,
                self._previous_table.c.version_id == version_id
            ))
        ).fetchall()
        if previous_objects:
            selected_table = self._previous_table
            object_data = self.object_type(*previous_objects[0])
        else:
            current_object = self.get_current_object(object_id, connection=connection)
            if current_object is not None and current_object.version_id == version_id:
                selected_table = self._current_table
                object_data = current_object
            else:
                return None
        if object_data.fed_object_id is None or object_data.fed_version_id is None or object_data.component_id is None:
            return None

        previous_subversion_id = connection.execute(db.select(db.func.max(self._subversions_table.c.subversion_id)).where(db.and_(self._subversions_table.c.object_id == object_id, self._subversions_table.c.version_id == version_id))).scalar()
        if previous_subversion_id is None:
            subversion_id = 0
        else:
            subversion_id = previous_subversion_id + 1
        if connection.execute(
            # move deprecated version to subversions table
            self._subversions_table
                .insert()
                .values(
                    object_id=object_data.object_id,
                    version_id=object_data.version_id,
                    subversion_id=subversion_id,
                    action_id=object_data.action_id,
                    data=object_data.data,
                    schema=object_data.schema,
                    user_id=object_data.user_id,
                    utc_datetime=object_data.utc_datetime,
                    utc_datetime_subversion=utc_datetime_subversion
                )
        ).rowcount != 1:
            return None

        # Update current version to new version
        if selected_table == self._current_table:
            cache_values = {
                'name_cache': data.get('name', {}).get('text') if data else None,
                'tags_cache': data.get('tags') if data else None,
            }
        else:
            cache_values = {}
        connection.execute(
            selected_table
            .update()
            .where(selected_table.c.object_id == db.bindparam('oid'), selected_table.c.version_id == db.bindparam('vid'))
            .values(
                action_id=action_id,
                data=data,
                schema=schema,
                user_id=user_id,
                utc_datetime=utc_datetime,
                **cache_values
            ),
            [{'oid': object_id, 'vid': version_id}]
        )
        return self.get_object_version(object_id, version_id, connection=connection)

    def is_existing_object(self, object_id: int, connection=None) -> bool:
        """
        Return whether an object with the given ID exists.

        :param object_id: the ID of a possibly existing object
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: whether the object exists
        """
        if connection is None:
            connection = self.bind.connect()
        return connection.execute(
            db.select([self._current_table.c.object_id]).where(self._current_table.c.object_id == object_id)
        ).fetchone() is not None

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
                self._current_table.c.utc_datetime,
                self._current_table.c.fed_object_id,
                self._current_table.c.fed_version_id,
                self._current_table.c.component_id
            ])
            .where(self._current_table.c.object_id == object_id)
        ).fetchone()
        if current_object is None:
            return None
        return self.object_type(*current_object)

    def get_previous_subversion(self, object_id, version_id, connection=None):
        if connection is None:
            connection = self.bind.connect()
        previous_object_subversion = connection.execute(
            db.select([
                self._subversions_table.c.object_id,
                self._subversions_table.c.version_id,
                self._subversions_table.c.action_id,
                self._subversions_table.c.data,
                self._subversions_table.c.schema,
                self._subversions_table.c.user_id,
                self._subversions_table.c.utc_datetime,
                None,
                None,
                None
            ])
            .where(
                db.and_(
                    self._subversions_table.c.object_id == object_id,
                    self._subversions_table.c.version_id == version_id
                )
            )
            .order_by(db.desc(self._subversions_table.c.subversion_id))
        ).first()
        return self.object_type(*previous_object_subversion)

    def get_current_fed_object(self, component_id, fed_object_id, connection=None):
        """
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
                self._current_table.c.utc_datetime,
                self._current_table.c.fed_object_id,
                self._current_table.c.fed_version_id,
                self._current_table.c.component_id
            ])
            .where(db.and_(
                self._current_table.c.component_id == component_id,
                self._current_table.c.fed_object_id == fed_object_id
            ))
        ).fetchone()
        if current_object is None:
            return None
        return self.object_type(*current_object)

    def get_fed_object_version(self, component_id, fed_object_id, fed_version_id, connection=None):
        """
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
                self._previous_table.c.utc_datetime,
                self._previous_table.c.fed_object_id,
                self._previous_table.c.fed_version_id,
                self._previous_table.c.component_id
            ])
            .where(db.and_(db.and_(
                self._previous_table.c.component_id == component_id,
                self._previous_table.c.fed_object_id == fed_object_id),
                self._previous_table.c.fed_version_id == fed_version_id
            ))
        ).fetchall()
        if previous_objects:
            return self.object_type(*previous_objects[0])
        current_object = self.get_current_fed_object(component_id, fed_object_id, connection=connection)
        if current_object is not None and current_object.fed_version_id == fed_version_id:
            return current_object
        return None

    def get_current_objects(self, filter_func=lambda data: True, action_table=None, action_filter=None, connection=None, table=None, parameters=None, sorting_func=None, limit=None, offset=None, num_objects_found=None):
        """
        Queries and returns all objects matching a given filter.

        :param filter_func: a lambda that may return an SQLAlchemy filter when given a table
        :param action_filter: a SQLAlchemy comparator, used to query only objects created by specific actions
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :param table: a custom SQLAlchemy table-like object to use as base for the query (optional)
        :param parameters: query parameters for the custom select statement (optional)
        :return: a list of objects as object_type
        """
        if connection is None:
            connection = self.bind.connect()

        if parameters is None:
            parameters = {}

        if table is None:
            table = self._current_table

        select_statement = db.select([
            table.c.object_id,
            table.c.version_id,
            table.c.action_id,
            table.c.data,
            table.c.schema,
            table.c.user_id,
            table.c.utc_datetime,
            table.c.fed_object_id,
            table.c.fed_version_id,
            table.c.component_id,
            db.sql.expression.text('COUNT(*) OVER()')
        ])

        selectable = table

        if sorting_func is not None and getattr(sorting_func, 'require_original_columns', False):
            selectable = selectable.outerjoin(
                self._previous_table,
                db.and_(table.c.object_id == self._previous_table.c.object_id, self._previous_table.c.version_id == 0),
                full=False
            )

        if action_table is not None and action_filter is not None:
            assert self._action_id_column is not None
            assert action_table is not None
            assert action_filter is not None
            selectable = selectable.join(
                action_table,
                db.and_(table.c.action_id == self._action_id_column, action_filter)
            )

        select_statement = select_statement.select_from(selectable)

        if sorting_func is None:
            def sorting_func(current_columns, original_columns):
                return db.sql.desc(current_columns.object_id)

        select_statement = select_statement.where(filter_func(table.c.data))
        select_statement = select_statement.order_by(sorting_func(table.c, self._previous_table.c))

        if limit is not None:
            select_statement = select_statement.limit(limit)

        if offset is not None:
            select_statement = select_statement.offset(offset)

        objects = connection.execute(
            select_statement,
            **parameters
        ).fetchall()
        if num_objects_found is not None:
            num_objects_found.clear()
            if objects:
                num_objects_found.append(objects[0][-1])
            else:
                num_objects_found.append(0)
        return [self.object_type(*obj[:-1]) for obj in objects]

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
                self._previous_table.c.utc_datetime,
                self._previous_table.c.fed_object_id,
                self._previous_table.c.fed_version_id,
                self._previous_table.c.component_id
            ])
            .where(self._previous_table.c.object_id == object_id)
            # .order_by(db.asc(self._previous_table.c.version_id))
            .order_by(db.asc(self._previous_table.c.utc_datetime))
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
                self._previous_table.c.utc_datetime,
                self._previous_table.c.fed_object_id,
                self._previous_table.c.fed_version_id,
                self._previous_table.c.component_id
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
