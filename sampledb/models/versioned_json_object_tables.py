# coding: utf-8
"""

"""

import dataclasses
import datetime
import functools
import typing

import sqlalchemy as db
from sqlalchemy.dialects import postgresql

if typing.TYPE_CHECKING:
    from ..logic.components import Component
    from ..logic.eln_import import ELNImport


F = typing.TypeVar('F', bound=typing.Callable[..., typing.Any])


def _use_transaction(func: F) -> F:
    @functools.wraps(func)
    def wrapped_func(
            self: 'VersionedJSONSerializableObjectTables',
            *args: typing.Any,
            connection: typing.Optional[db.engine.Connection] = None,
            **kwargs: typing.Any
    ) -> typing.Any:
        if connection is not None:
            return func(self, *args, connection=connection, **kwargs)
        assert self.bind is not None
        with self.bind.begin() as connection:
            return func(self, *args, connection=connection, **kwargs)
    return typing.cast(F, wrapped_func)


class DataValidator(typing.Protocol):
    def __call__(
        self,
        instance: typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]],
        schema: typing.Dict[str, typing.Any],
        path: typing.Optional[typing.List[str]] = None,
        allow_disabled_languages: bool = False,
        strict: bool = False
    ) -> None:
        ...


class SchemaValidator(typing.Protocol):
    def __call__(
        self,
        schema: typing.Dict[str, typing.Any],
        path: typing.Optional[typing.List[str]] = None,
        *,
        parent_conditions: typing.Optional[typing.List[typing.Tuple[typing.List[str], typing.Dict[str, typing.Any]]]] = None,
        invalid_template_action_ids: typing.Sequence[int] = (),
        strict: bool = False
    ) -> None:
        ...


@dataclasses.dataclass
class Object:
    object_id: int
    version_id: int
    action_id: typing.Optional[int]
    data: typing.Optional[typing.Dict[str, typing.Any]]
    schema: typing.Optional[typing.Dict[str, typing.Any]]
    user_id: typing.Optional[int]
    utc_datetime: typing.Optional[datetime.datetime]
    fed_object_id: typing.Optional[int]
    fed_version_id: typing.Optional[int]
    component_id: typing.Optional[int]
    eln_import_id: typing.Optional[int]
    eln_object_id: typing.Optional[str]
    _component_cache: typing.List[typing.Optional['Component']] = dataclasses.field(default_factory=lambda: [None], repr=False, kw_only=True)
    _eln_import_cache: typing.List[typing.Optional['ELNImport']] = dataclasses.field(default_factory=lambda: [None], repr=False, kw_only=True)

    @property
    def id(self) -> int:
        return self.object_id

    @property
    def fed_id(self) -> typing.Optional[int]:
        return self.fed_object_id

    @property
    def name(self) -> typing.Union[str, typing.Dict[str, str]]:
        if self.data is not None and self.data.get('name') and isinstance(self.data['name'], dict) and self.data['name'].get('text'):
            return typing.cast(typing.Union[str, typing.Dict[str, str]], self.data['name']['text'])
        else:
            return ''

    @property
    def component(self) -> typing.Optional['Component']:
        if self.component_id is not None and self._component_cache[0] is None:
            from ..logic.components import get_component
            self._component_cache[0] = get_component(self.component_id)
        return self._component_cache[0]

    @property
    def eln_import(self) -> typing.Optional['ELNImport']:
        if self.eln_import_id is not None and self._eln_import_cache[0] is None:
            from ..logic.eln_import import get_eln_import
            self._eln_import_cache[0] = get_eln_import(self.eln_import_id)
        return self._eln_import_cache[0]


class VersionedJSONSerializableObjectTables:
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

    def __init__(
            self,
            table_name_prefix: str,
            bind: typing.Optional[db.engine.Engine] = None,
            user_id_column: typing.Optional[typing.Any] = None,
            action_id_column: typing.Optional[typing.Any] = None,
            component_id_column: typing.Optional[typing.Any] = None,
            eln_import_id_column: typing.Optional[typing.Any] = None,
            action_schema_column: typing.Optional[typing.Any] = None,
            metadata: typing.Optional[db.MetaData] = None,
            data_validator: typing.Optional[DataValidator] = None,
            schema_validator: typing.Optional[SchemaValidator] = None
    ) -> None:
        """
        Creates new instance for storing versioned, JSON-serializable objects using three tables.

        :param table_name_prefix: the prefix used for naming the two used tables
        :param bind: the SQLAlchemy engine used for creating the tables and for future connections
        :param user_id_column: a SQLAlchemy column object for use as foreign key for the user ID (optional)
        :param action_id_column: a SQLAlchemy column object for use as foreign key for the action ID (optional)
        :param metadata: an SQLAlchemy MetaData object used for creating the two tables (optional)
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
            db.Column('utc_datetime', db.TIMESTAMP(timezone=True)),
            db.Column('fed_object_id', db.Integer),
            db.Column('fed_version_id', db.Integer),
            db.Column('component_id', db.Integer),
            db.Column('name_cache', db.JSON),
            db.Column('tags_cache', db.JSON),
            db.Column('eln_import_id', db.Integer, nullable=True),
            db.Column('eln_object_id', db.String, nullable=True),
            db.CheckConstraint(
                '(fed_object_id IS NOT NULL AND fed_version_id IS NOT NULL AND component_id IS NOT NULL) OR (eln_import_id IS NOT NULL AND eln_object_id IS NOT NULL) OR (action_id IS NOT NULL AND data IS NOT NULL AND schema IS NOT NULL AND user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
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
            db.Column('utc_datetime', db.TIMESTAMP(timezone=True), nullable=True),
            db.Column('fed_object_id', db.Integer, nullable=True),
            db.Column('fed_version_id', db.Integer, nullable=True),
            db.Column('component_id', db.Integer, nullable=True),
            db.Column('eln_import_id', db.Integer, nullable=True),
            db.Column('eln_object_id', db.String, nullable=True),
            db.PrimaryKeyConstraint('object_id', 'version_id'),
            db.CheckConstraint(
                '(fed_object_id IS NOT NULL AND fed_version_id IS NOT NULL AND component_id IS NOT NULL) OR (eln_import_id IS NOT NULL AND eln_object_id IS NOT NULL) OR (action_id IS NOT NULL AND data IS NOT NULL AND schema IS NOT NULL AND user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
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
            db.Column('utc_datetime', db.TIMESTAMP(timezone=True), nullable=True),
            db.Column('utc_datetime_subversion', db.TIMESTAMP(timezone=True), nullable=False),
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
        if eln_import_id_column is not None:
            self._current_table.append_constraint(db.ForeignKeyConstraint(['eln_import_id'], [eln_import_id_column]))
            self._previous_table.append_constraint(db.ForeignKeyConstraint(['eln_import_id'], [eln_import_id_column]))
        self._action_id_column = action_id_column
        self._action_schema_column = action_schema_column
        self._component_id_column = component_id_column
        self._eln_import_id_column = eln_import_id_column
        self.object_id_column = self._current_table.c.object_id
        self.data_column = self._current_table.c.data
        self.bind = bind
        if self.bind is not None:
            self.metadata.create_all(self.bind)
        self._data_validator = data_validator
        self._schema_validator = schema_validator

    @_use_transaction
    def create_object(
            self,
            data: typing.Optional[typing.Dict[str, typing.Any]],
            schema: typing.Optional[typing.Dict[str, typing.Any]],
            user_id: typing.Optional[int],
            action_id: typing.Optional[int],
            utc_datetime: typing.Optional[datetime.datetime] = None,
            fed_object_id: typing.Optional[int] = None,
            fed_version_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None,
            eln_import_id: typing.Optional[int] = None,
            eln_object_id: typing.Optional[str] = None,
            connection: typing.Optional[db.engine.Connection] = None,
            validate_data: bool = True,
            data_validator_arguments: typing.Optional[typing.Dict[str, typing.Any]] = None
    ) -> Object:
        """
        Creates an object in the table for current objects. This object will always have version_id 0.

        :param data: a JSON serializable object containing the object data
        :param schema: a JSON schema describing data (may be None if action's schema is to be used)
        :param user_id: the ID of the user who created the object
        :param action_id: the ID of the action which was used to create the object
        :param utc_datetime: the datetime (in UTC) when the object was created (optional, defaults to now(timezone.utc))
        :param fed_object_id: the ID of this object on a federated component
        :param fed_version_id: the version ID of this object on a federated component
        :param eln_import_id: the ID of an .eln file import
        :param eln_object_id: the ID of this object in the .eln file
        :param component_id: the ID of the component that created this object
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :param validate_data: whether the data must be validated
        :param data_validator_arguments: additional keyword arguments to the data validator
        :return: the newly created object as object_type
        :raise ValueError: if the schema and action are None for a local object
        """
        assert connection is not None  # ensured by decorator
        if utc_datetime is None and fed_object_id is None:
            utc_datetime = datetime.datetime.now(datetime.timezone.utc)
        if schema is not None or data is not None:
            if schema is None and action_id is not None and self._action_schema_column is not None and self._action_id_column is not None:
                action = connection.execute(
                    db
                    .select(
                        self._action_schema_column
                    )
                    .where(self._action_id_column == action_id)
                ).fetchone()
                if action is None:
                    if fed_object_id is None or fed_version_id is None or component_id is None:
                        raise ValueError(f'Action with id {action_id} not found')
                    else:
                        schema = None
                else:
                    schema = action[0]
            if not (schema is None and fed_object_id is not None and fed_version_id is not None):
                if schema is not None and self._schema_validator:
                    self._schema_validator(schema)
                if not (data is None and fed_object_id is not None and fed_version_id is not None):
                    if data is not None and schema is not None and self._data_validator and validate_data:
                        if data_validator_arguments is None:
                            data_validator_arguments = {}
                        if 'allow_disabled_languages' not in data_validator_arguments:
                            data_validator_arguments['allow_disabled_languages'] = False
                        self._data_validator(data, schema, **data_validator_arguments)
        version_id = 0
        object_id = typing.cast(int, connection.execute(
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
                component_id=component_id,
                eln_import_id=eln_import_id,
                eln_object_id=eln_object_id,
            )
            .returning(
                self._current_table.c.object_id
            )
        ).scalar())
        obj = Object(
            object_id=object_id,
            version_id=version_id,
            action_id=action_id,
            data=data,
            schema=schema,
            user_id=user_id,
            utc_datetime=utc_datetime,
            fed_object_id=fed_object_id,
            fed_version_id=fed_version_id,
            component_id=component_id,
            eln_import_id=eln_import_id,
            eln_object_id=eln_object_id,
        )
        return obj

    @_use_transaction
    def update_object(
            self,
            object_id: int,
            data: typing.Optional[typing.Dict[str, typing.Any]],
            schema: typing.Optional[typing.Dict[str, typing.Any]],
            user_id: int,
            utc_datetime: typing.Optional[datetime.datetime] = None,
            connection: typing.Optional[db.engine.Connection] = None,
            validate_schema: bool = True,
            validate_data: bool = True,
            data_validator_arguments: typing.Optional[typing.Dict[str, typing.Any]] = None
    ) -> typing.Optional[Object]:
        """
        Updates an existing object using the given data, user id and datetime.

        This step first copies the existing object in the table of previous object versions and then modifies the
        object's version id, incrementing it by one, and data, replacing it by the given data.

        :param object_id: the ID of the existing object
        :param data: a JSON serializable object containing the updated object data
        :param schema: a JSON schema describing data (optional, defaults to the current object schema)
        :param user_id: the ID of the user who updated the object
        :param utc_datetime: the datetime (in UTC) when the object was updated (optional, defaults to now(timezone.utc))
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :param validate_schema: whether the schema should be validated
        :param validate_data: whether the data should be validated
        :param data_validator_arguments: additional keyword arguments to the data validator
        :return: the updated object as object_type or None, if the object does not exist
        """
        assert connection is not None  # ensured by decorator
        if utc_datetime is None:
            utc_datetime = datetime.datetime.now(datetime.timezone.utc)
        if schema is not None or data is not None:
            if schema is None:
                schema_row = connection.execute(
                    db.select(self._current_table.c.schema).where(self._current_table.c.object_id == object_id)
                ).fetchone()
                if schema_row is None:
                    return None
                schema = schema_row[0]
            if validate_schema and self._schema_validator and schema is not None:
                self._schema_validator(schema)
            if validate_data and self._data_validator and schema is not None and data is not None:
                if data_validator_arguments is None:
                    data_validator_arguments = {}
                self._data_validator(data, schema, **data_validator_arguments)

        # Copy current version to previous versions
        if connection.execute(
            self._previous_table
            .insert()
            .from_select(
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
                    'component_id',
                    'eln_import_id',
                    'eln_object_id',
                ],
                self._current_table
                .select()
                .with_only_columns(
                    self._current_table.c.object_id,
                    self._current_table.c.version_id,
                    self._current_table.c.action_id,
                    self._current_table.c.data,
                    self._current_table.c.schema,
                    self._current_table.c.user_id,
                    self._current_table.c.utc_datetime,
                    self._current_table.c.fed_object_id,
                    self._current_table.c.fed_version_id,
                    self._current_table.c.component_id,
                    self._current_table.c.eln_import_id,
                    self._current_table.c.eln_object_id,
                )
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

    @_use_transaction
    def restore_object_version(
            self,
            object_id: int,
            version_id: int,
            user_id: int,
            utc_datetime: typing.Optional[datetime.datetime] = None,
            connection: typing.Optional[db.engine.Connection] = None
    ) -> typing.Optional[Object]:
        object_version = self.get_object_version(object_id=object_id, version_id=version_id, connection=connection)
        if object_version is None:
            return None
        if object_version.schema is not None and self._schema_validator:
            self._schema_validator(object_version.schema)
        if object_version.schema is not None and object_version.data is not None and self._data_validator:
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

    @_use_transaction
    def insert_fed_object_version(
            self,
            fed_object_id: int,
            fed_version_id: int,
            component_id: int,
            action_id: typing.Optional[int],
            data: typing.Optional[typing.Dict[str, typing.Any]],
            schema: typing.Optional[typing.Dict[str, typing.Any]],
            user_id: typing.Optional[int],
            utc_datetime: typing.Optional[datetime.datetime],
            connection: typing.Optional[db.engine.Connection] = None,
            allow_disabled_languages: bool = False,
            get_missing_schema_from_action: bool = True
    ) -> typing.Optional[Object]:
        assert connection is not None  # ensured by decorator
        if schema is None and get_missing_schema_from_action and self._action_schema_column is not None and self._action_id_column is not None:
            action = connection.execute(
                db
                .select(
                    self._action_schema_column
                )
                .where(self._action_id_column == action_id)
            ).fetchone()
            if action is None:
                if fed_object_id is None or fed_version_id is None or component_id is None:
                    raise ValueError(f'Action with id {action_id} not found')
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
        elif current.fed_version_id is None or current.fed_version_id < fed_version_id:
            # Copy current version to previous versions
            if connection.execute(
                self._previous_table
                .insert()
                .from_select(
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
                        'component_id',
                        'eln_import_id',
                        'eln_object_id'
                    ],
                    self._current_table
                    .select()
                    .with_only_columns(
                        self._current_table.c.object_id,
                        self._current_table.c.version_id,
                        self._current_table.c.action_id,
                        self._current_table.c.data,
                        self._current_table.c.schema,
                        self._current_table.c.user_id,
                        self._current_table.c.utc_datetime,
                        self._current_table.c.fed_object_id,
                        self._current_table.c.fed_version_id,
                        self._current_table.c.component_id,
                        self._current_table.c.eln_import_id,
                        self._current_table.c.eln_object_id,
                    )
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
            max_version_id = connection.execute(
                db.select(
                    db.sql.func.max(self._previous_table.c.version_id)  # pylint: disable=not-callable
                ).where(
                    self._previous_table.c.object_id == current.object_id
                )
            ).scalar()
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

    @_use_transaction
    def update_object_version(
            self,
            object_id: int,
            version_id: int,
            action_id: typing.Optional[int],
            schema: typing.Optional[typing.Dict[str, typing.Any]],
            data: typing.Optional[typing.Dict[str, typing.Any]],
            user_id: typing.Optional[int],
            utc_datetime: typing.Optional[datetime.datetime],
            utc_datetime_subversion: typing.Optional[datetime.datetime] = None,
            connection: typing.Optional[db.engine.Connection] = None,
            allow_disabled_languages: bool = False,
            get_missing_schema_from_action: bool = True
    ) -> typing.Optional[Object]:
        """
        Updates an existing object version using the given data, user id and datetime.

        This step first copies the existing object version in the table of object subversions and then modifies the
        data, replacing it by the given data.

        :param object_id: the ID of the existing object
        :param version_id: the version ID of the existing object
        :param action_id: the ID of the existing action
        :param data: a JSON serializable object containing the updated object data
        :param schema: a JSON schema describing data (optional, defaults to the current object schema)
        :param user_id: the ID of the user who updated the object
        :param utc_datetime: the datetime (in UTC) when the object was updated
        :param utc_datetime_subversion: the datetime (in UTC) when the object update has been applied (optional, defaults to now(timezone.utc))
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :param allow_disabled_languages: whether using disabled languages should be allowed in this update
        :param get_missing_schema_from_action: whether to use an action schema (if available) when None is passed for schema
        :return: the updated object as object_type or None, if the object does not exist
        """
        assert connection is not None  # ensured by decorator
        if utc_datetime_subversion is None:
            utc_datetime_subversion = datetime.datetime.now(datetime.timezone.utc)
        if schema is None and get_missing_schema_from_action and self._action_schema_column is not None and self._action_id_column is not None:
            action = connection.execute(
                db
                .select(
                    self._action_schema_column
                )
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

        assert connection is not None  # ensured by decorator
        previous_objects = connection.execute(
            db
            .select(
                self._previous_table.c.object_id,
                self._previous_table.c.version_id,
                self._previous_table.c.action_id,
                self._previous_table.c.data,
                self._previous_table.c.schema,
                self._previous_table.c.user_id,
                self._previous_table.c.utc_datetime,
                self._previous_table.c.fed_object_id,
                self._previous_table.c.fed_version_id,
                self._previous_table.c.component_id,
                self._previous_table.c.eln_import_id,
                self._previous_table.c.eln_object_id,
            )
            .where(db.and_(
                self._previous_table.c.object_id == object_id,
                self._previous_table.c.version_id == version_id
            ))
        ).fetchall()
        if previous_objects:
            selected_table = self._previous_table
            object_data = Object(*previous_objects[0])
        else:
            current_object = self.get_current_object(object_id, connection=connection)
            if current_object is not None and current_object.version_id == version_id:
                selected_table = self._current_table
                object_data = current_object
            else:
                return None
        if object_data.fed_object_id is None or object_data.fed_version_id is None or object_data.component_id is None:
            return None

        previous_subversion_id = connection.execute(
            db.select(
                db.sql.func.max(self._subversions_table.c.subversion_id)  # pylint: disable=not-callable
            ).where(
                db.and_(
                    self._subversions_table.c.object_id == object_id,
                    self._subversions_table.c.version_id == version_id
                )
            )
        ).scalar()
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

    @_use_transaction
    def is_existing_object(
            self,
            object_id: int,
            connection: typing.Optional[db.engine.Connection] = None
    ) -> bool:
        """
        Return whether an object with the given ID exists.

        :param object_id: the ID of a possibly existing object
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: whether the object exists
        """
        assert connection is not None  # ensured by decorator
        return connection.execute(
            db.select(self._current_table.c.object_id).where(self._current_table.c.object_id == object_id)
        ).fetchone() is not None

    @_use_transaction
    def is_existing_object_version(
            self,
            object_id: int,
            version_id: int,
            connection: typing.Optional[db.engine.Connection] = None
    ) -> bool:
        """
        Return whether an object version with the given ID exists.

        :param object_id: the ID of a possibly existing object
        :param version_id: the version ID to check
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: whether the object version exists
        """
        assert connection is not None  # ensured by decorator
        current_version_id = connection.execute(
            db.select(self._current_table.c.version_id).where(
                self._current_table.c.object_id == object_id,
                self._current_table.c.version_id >= version_id
            )
        ).fetchone()
        if current_version_id is None:
            return False
        if current_version_id[0] == version_id:
            return True
        return connection.execute(
            db.select(self._previous_table.c.version_id).where(
                self._previous_table.c.object_id == object_id,
                self._previous_table.c.version_id == version_id
            )
        ).fetchone() is not None

    @_use_transaction
    def get_current_object(
            self,
            object_id: int,
            connection: typing.Optional[db.engine.Connection] = None
    ) -> typing.Optional[Object]:
        """
        Queries and returns an object by its ID.

        :param object_id: the ID of the existing object
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: the object as object_type or None if the object does not exist
        """
        assert connection is not None  # ensured by decorator
        current_object = connection.execute(
            db
            .select(
                self._current_table.c.object_id,
                self._current_table.c.version_id,
                self._current_table.c.action_id,
                self._current_table.c.data,
                self._current_table.c.schema,
                self._current_table.c.user_id,
                self._current_table.c.utc_datetime,
                self._current_table.c.fed_object_id,
                self._current_table.c.fed_version_id,
                self._current_table.c.component_id,
                self._current_table.c.eln_import_id,
                self._current_table.c.eln_object_id,
            )
            .where(self._current_table.c.object_id == object_id)
        ).fetchone()
        if current_object is None:
            return None
        return Object(*current_object)

    @_use_transaction
    def get_previous_subversion(
            self,
            object_id: int,
            version_id: int,
            connection: typing.Optional[db.engine.Connection] = None
    ) -> typing.Optional[Object]:
        assert connection is not None  # ensured by decorator
        previous_object_subversion = connection.execute(
            db.select(
                self._subversions_table.c.object_id,
                self._subversions_table.c.version_id,
                self._subversions_table.c.action_id,
                self._subversions_table.c.data,
                self._subversions_table.c.schema,
                self._subversions_table.c.user_id,
                self._subversions_table.c.utc_datetime,
                db.null(),  # fed_object_id
                db.null(),  # fed_version_id
                db.null(),  # component_id
                db.null(),  # eln_import_id
                db.null(),  # eln_object_id
            )
            .where(
                db.and_(
                    self._subversions_table.c.object_id == object_id,
                    self._subversions_table.c.version_id == version_id
                )
            )
            .order_by(db.desc(self._subversions_table.c.subversion_id))
        ).first()
        if previous_object_subversion is None:
            return None
        return Object(*previous_object_subversion)

    @_use_transaction
    def get_current_fed_object(
            self,
            component_id: int,
            fed_object_id: int,
            connection: typing.Optional[db.engine.Connection] = None
    ) -> typing.Optional[Object]:
        """
        """
        assert connection is not None  # ensured by decorator
        current_object = connection.execute(
            db
            .select(
                self._current_table.c.object_id,
                self._current_table.c.version_id,
                self._current_table.c.action_id,
                self._current_table.c.data,
                self._current_table.c.schema,
                self._current_table.c.user_id,
                self._current_table.c.utc_datetime,
                self._current_table.c.fed_object_id,
                self._current_table.c.fed_version_id,
                self._current_table.c.component_id,
                self._current_table.c.eln_import_id,
                self._current_table.c.eln_object_id,
            )
            .where(db.and_(
                self._current_table.c.component_id == component_id,
                self._current_table.c.fed_object_id == fed_object_id
            ))
        ).fetchone()
        if current_object is None:
            return None
        return Object(*current_object)

    @_use_transaction
    def get_fed_object_version(
            self,
            component_id: int,
            fed_object_id: int,
            fed_version_id: int,
            connection: typing.Optional[db.engine.Connection] = None
    ) -> typing.Optional[Object]:
        """
        """
        assert connection is not None  # ensured by decorator
        previous_objects = connection.execute(
            db
            .select(
                self._previous_table.c.object_id,
                self._previous_table.c.version_id,
                self._previous_table.c.action_id,
                self._previous_table.c.data,
                self._previous_table.c.schema,
                self._previous_table.c.user_id,
                self._previous_table.c.utc_datetime,
                self._previous_table.c.fed_object_id,
                self._previous_table.c.fed_version_id,
                self._previous_table.c.component_id,
                self._previous_table.c.eln_import_id,
                self._previous_table.c.eln_object_id,
            )
            .where(db.and_(db.and_(
                self._previous_table.c.component_id == component_id,
                self._previous_table.c.fed_object_id == fed_object_id),
                self._previous_table.c.fed_version_id == fed_version_id
            ))
        ).fetchall()
        if previous_objects:
            return Object(*previous_objects[0])
        current_object = self.get_current_fed_object(component_id, fed_object_id, connection=connection)
        if current_object is not None and current_object.fed_version_id == fed_version_id:
            return current_object
        return None

    @_use_transaction
    def get_current_objects(
            self,
            filter_func: typing.Callable[[typing.Any], typing.Any] = lambda data: True,
            action_table: typing.Any = None,
            action_filter: typing.Optional[db.sql.ColumnElement[bool]] = None,
            connection: typing.Optional[db.engine.Connection] = None,
            table: typing.Any = None,
            parameters: typing.Optional[typing.Dict[str, typing.Any]] = None,
            sorting_func: typing.Optional[typing.Callable[[typing.Any, typing.Any], typing.Any]] = None,
            limit: typing.Optional[int] = None,
            offset: typing.Optional[int] = None,
            num_objects_found: typing.Optional[typing.List[int]] = None
    ) -> typing.List[Object]:
        """
        Queries and returns all objects matching a given filter.

        :param filter_func: a lambda that may return an SQLAlchemy filter when given a table
        :param action_table: a SQLAlchemy table object containing the actions to filter by (see action_filter)
        :param action_filter: a SQLAlchemy comparator, used to query only objects created by specific actions
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :param table: a custom SQLAlchemy table-like object to use as base for the query (optional)
        :param parameters: query parameters for the custom select statement (optional)
        :param sorting_func: a sorting function to use (see logic.object_sorting)
        :param limit: limits the number of returned objects, if set
        :param offset: an offset to apply to the query
        :param num_objects_found: a list used to return the number of objects found in, using the 0-th element
        :return: a list of objects as object_type
        """
        assert connection is not None  # ensured by decorator

        if parameters is None:
            parameters = {}

        if table is None:
            table = self._current_table

        select_statement = db.select(
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
            table.c.eln_import_id,
            table.c.eln_object_id,
            db.sql.expression.text('COUNT(*) OVER()')
        )

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
            def default_sorting_func(current_columns: typing.Any, original_columns: typing.Any) -> typing.Any:
                return db.sql.desc(current_columns.object_id)

            sorting_func = default_sorting_func

        # use data_full column for filtering, as data might only contain the name property
        filter_data_column = table.c.data_full if hasattr(table.c, 'data_full') else table.c.data
        # set object_id_column to allow access to table.c.object_id in filter_func (e.g. for file search)
        filter_data_column.object_id_column = table.c.object_id
        select_statement = select_statement.where(filter_func(filter_data_column))
        select_statement = select_statement.order_by(sorting_func(table.c, self._previous_table.c))

        if limit is not None:
            select_statement = select_statement.limit(limit)

        if offset is not None:
            select_statement = select_statement.offset(offset)

        objects = connection.execute(
            select_statement,
            parameters
        ).fetchall()
        if num_objects_found is not None:
            num_objects_found.clear()
            if objects:
                num_objects_found.append(objects[0][-1])
            else:
                num_objects_found.append(0)
        return [Object(*obj[:-1]) for obj in objects]

    @_use_transaction
    def get_object_versions(
            self,
            object_id: int,
            connection: typing.Optional[db.engine.Connection] = None
    ) -> typing.List[Object]:
        """
        Queries and returns all versions of an object with a given ID, sorted ascendingly by the version ID, from first
        version to current version.

        :param object_id: the ID of the existing object
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: a list of objects as object_type
        """
        assert connection is not None  # ensured by decorator
        current_object = self.get_current_object(object_id, connection=connection)
        if current_object is None:
            return []
        previous_objects = connection.execute(
            db
            .select(
                self._previous_table.c.object_id,
                self._previous_table.c.version_id,
                self._previous_table.c.action_id,
                self._previous_table.c.data,
                self._previous_table.c.schema,
                self._previous_table.c.user_id,
                self._previous_table.c.utc_datetime,
                self._previous_table.c.fed_object_id,
                self._previous_table.c.fed_version_id,
                self._previous_table.c.component_id,
                self._previous_table.c.eln_import_id,
                self._previous_table.c.eln_object_id,
            )
            .where(self._previous_table.c.object_id == object_id)
            # .order_by(db.asc(self._previous_table.c.version_id))
            .order_by(db.asc(self._previous_table.c.utc_datetime))
        ).fetchall()
        objects = []
        for obj in previous_objects:
            objects.append(Object(*obj))
        objects.append(current_object)
        return objects

    @_use_transaction
    def get_object_version(
            self,
            object_id: int,
            version_id: int,
            connection: typing.Optional[db.engine.Connection] = None
    ) -> typing.Optional[Object]:
        """
        Queries and returns an individual version of an object with a given object and version ID.

        :param object_id: the ID of the existing object
        :param version_id: the ID of the object's existing version
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: the object as object_type or None if the object or this version of it does not exist
        """
        assert connection is not None  # ensured by decorator
        previous_objects = connection.execute(
            db
            .select(
                self._previous_table.c.object_id,
                self._previous_table.c.version_id,
                self._previous_table.c.action_id,
                self._previous_table.c.data,
                self._previous_table.c.schema,
                self._previous_table.c.user_id,
                self._previous_table.c.utc_datetime,
                self._previous_table.c.fed_object_id,
                self._previous_table.c.fed_version_id,
                self._previous_table.c.component_id,
                self._previous_table.c.eln_import_id,
                self._previous_table.c.eln_object_id,
            )
            .where(db.and_(
                self._previous_table.c.object_id == object_id,
                self._previous_table.c.version_id == version_id
            ))
        ).fetchall()
        if previous_objects:
            return Object(*previous_objects[0])
        current_object = self.get_current_object(object_id, connection=connection)
        if current_object is not None and current_object.version_id == version_id:
            return current_object
        return None

    @_use_transaction
    def get_current_object_version_id(
            self,
            object_id: int,
            connection: typing.Optional[db.engine.Connection] = None
    ) -> typing.Optional[int]:
        """
        Get the ID of the current version of an object.

        :param object_id: the ID of an existing object
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: the object's current version ID, or None
        """
        assert connection is not None  # ensured by decorator
        current_object_info = connection.execute(
            db
            .select(
                self._current_table.c.version_id,
            )
            .where(
                self._current_table.c.object_id == object_id
            )
        ).fetchone()
        if current_object_info is None:
            return None
        return typing.cast(int, current_object_info[0])

    @_use_transaction
    def get_action_ids_for_object_ids(
            self,
            object_ids: typing.Sequence[int],
            connection: typing.Optional[db.engine.Connection] = None
    ) -> typing.Dict[int, typing.Optional[int]]:
        """
        Get the action IDs for a list of object IDs.

        :param object_ids: the IDs of existing objects
        :param connection: the SQLAlchemy connection (optional, defaults to a new connection using self.bind)
        :return: the objects' action IDs
        """
        assert connection is not None  # ensured by decorator

        object_ids_and_action_ids = connection.execute(
            db
            .select(
                self._current_table.c.object_id, self._current_table.c.action_id
            )
            .where(
                self._current_table.c.object_id.in_(object_ids)
            )
        ).fetchall()
        result = {
            object_id: action_id
            for object_id, action_id in object_ids_and_action_ids
        }
        for object_id in object_ids:
            if object_id not in result:
                result[object_id] = None
        return result

    @property
    def current_table(self) -> db.Table:
        return self._current_table
