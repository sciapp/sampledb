# coding: utf-8
"""

"""

import base64
import functools
import json
import os
import typing
import secrets

import flask
import flask_login
import sqlalchemy
import werkzeug

from . import logic, db
from .models import Permissions, migrations

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


FlaskResponseValueT = typing.Union[flask.Response, werkzeug.Response, str]
FlaskResponseT = typing.Union[FlaskResponseValueT, typing.Tuple[FlaskResponseValueT, int], typing.Tuple[FlaskResponseValueT, int, typing.Dict[str, str]]]


def ansi_color(text: str, color: int) -> str:
    """
    Add ANSI color codes to text.

    :param text: the text without ANSI colors
    :param color: the desired color
    :return: the text with the color added
    """
    return f'\033[{color}m{text}\033[0m'


def object_permissions_required(
        required_object_permissions: Permissions,
        auth_extension: typing.Any = flask_login,
        user_id_callable: typing.Callable[[], typing.Optional[int]] = lambda: flask_login.current_user.get_id() if flask_login.current_user else None,
        on_unauthorized: typing.Callable[[int], FlaskResponseT] = lambda object_id: flask.abort(403),
        may_enable_anonymous_users: bool = True
) -> typing.Callable[[typing.Any], typing.Any]:
    def decorator(
            func: typing.Callable[[typing.Any], typing.Any],
            user_id_callable: typing.Callable[[], typing.Optional[int]] = user_id_callable,
            on_unauthorized: typing.Callable[[int], FlaskResponseT] = on_unauthorized
    ) -> typing.Callable[[typing.Any], typing.Any]:
        @functools.wraps(func)
        def wrapper(
                *args: typing.Any,
                user_id_callable: typing.Callable[[], typing.Optional[int]] = user_id_callable,
                on_unauthorized: typing.Callable[[int], FlaskResponseT] = on_unauthorized,
                **kwargs: typing.Any
        ) -> typing.Any:
            assert 'object_id' in kwargs
            object_id = kwargs['object_id']
            version_id = kwargs.get('version_id')
            try:
                if version_id is None:
                    logic.objects.check_object_exists(object_id)
                else:
                    logic.objects.check_object_version_exists(object_id, version_id)
            except logic.errors.ObjectDoesNotExistError:
                return flask.abort(404)
            except logic.errors.ObjectVersionDoesNotExistError:
                return flask.abort(404)
            user_id = user_id_callable()
            if user_id is None:
                if may_enable_anonymous_users and flask.current_app.config['ENABLE_ANONYMOUS_USERS']:
                    anonymous_permissions = logic.object_permissions.get_object_permissions_for_anonymous_users(object_id)
                else:
                    anonymous_permissions = Permissions.NONE
                if required_object_permissions not in anonymous_permissions:
                    return auth_extension.login_required(lambda: on_unauthorized(object_id))()
            elif required_object_permissions not in logic.object_permissions.get_object_permissions_for_all_users(object_id):
                user = logic.users.get_user(user_id)
                if user.is_readonly and required_object_permissions not in Permissions.READ:
                    return on_unauthorized(object_id)
                user_object_permissions = logic.object_permissions.get_user_object_permissions(object_id=object_id, user_id=user_id)
                if required_object_permissions not in user_object_permissions:
                    return on_unauthorized(object_id)
            return func(*args, **kwargs)
        if not may_enable_anonymous_users:
            wrapper = auth_extension.login_required(wrapper)
        return wrapper
    return decorator


def load_environment_configuration(env_prefix: str) -> typing.Dict[str, typing.Any]:
    """
    Loads configuration data from environment variables with a given prefix.
    If the prefixed environment variable B64_JSON_ENV exists, its content
    will be treated as an Base64 encoded JSON object and it's attributes
    starting with the prefix will be added to the environment.

    :return: a dict containing the configuration values
    """
    b64_json_env = os.environ.get(env_prefix + 'B64_JSON_ENV', None)
    if b64_json_env:
        for key, value in json.loads(base64.b64decode(b64_json_env.encode('utf-8')).decode('utf-8')).items():
            if key.startswith(env_prefix):
                os.environ[key] = value
    config = {
        key[len(env_prefix):]: value
        for key, value in os.environ.items()
        if key.startswith(env_prefix) and key != env_prefix + 'B64_JSON_ENV'
    }
    return config


def generate_secret_key(num_bits: int) -> str:
    """
    Generates a secure, random key for the application.

    :param num_bits: number of bits of random data in the secret key
    :return: the base64 encoded secret key
    """
    num_bytes = num_bits // 8
    binary_key = os.urandom(num_bytes)
    base64_key = base64.b64encode(binary_key).decode('ascii')
    return base64_key


def empty_database(
        engine: sqlalchemy.engine.Engine,
        recreate: bool = False,
        only_delete: bool = True
) -> None:
    metadata = sqlalchemy.MetaData()
    with engine.begin() as connection:
        # delete views, as SQLAlchemy cannot reflect them
        connection.execute(db.text("DROP VIEW IF EXISTS user_object_permissions_by_all"))
        # delete instruments -> objects_current foreign key, as it prevents sorting the tables
        connection.execute(db.text("ALTER TABLE IF EXISTS instruments DROP CONSTRAINT IF EXISTS instruments_object_id_fkey"))
        # delete users -> eln_imports foreign key, as it prevents sorting the tables
        connection.execute(db.text("ALTER TABLE IF EXISTS users DROP CONSTRAINT IF EXISTS fk_users_eln_import_id"))
    # delete tables, etc
    metadata.reflect(bind=engine)
    if only_delete:
        with engine.begin() as connection:
            for table in reversed(metadata.sorted_tables):
                connection.execute(table.delete())
            # migration_index needs to be dropped so migration #0 will run
            connection.execute(db.text("DROP TABLE IF EXISTS migration_index"))
    else:
        metadata.drop_all(bind=engine)
    if recreate:
        # recreate the tables
        db.metadata.create_all(bind=engine)
        # run migrations
        migrations.run(db)


def generate_content_security_policy_nonce() -> str:
    nonce = getattr(flask.g, 'content_security_policy_nonce', None)
    if nonce is None:
        nonce = secrets.token_hex(32)
        flask.g.content_security_policy_nonce = nonce
    return nonce


def text_to_bool(text: str) -> bool:
    return text.lower() not in {'', 'false', 'no', 'off', '0'}
