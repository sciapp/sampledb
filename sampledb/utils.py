# coding: utf-8
"""

"""

import base64
import functools
import json
import os
import typing

import flask
import flask_login
import sqlalchemy

from . import logic, db
from .models import Permissions, migrations

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def ansi_color(text: str, color: int):
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
        user_id_callable: typing.Callable[[], int] = lambda: flask_login.current_user.id,
        on_unauthorized: typing.Callable[[int], None] = lambda object_id: flask.abort(403)
):
    def decorator(func, user_id_callable=user_id_callable, on_unauthorized=on_unauthorized):
        @auth_extension.login_required
        @functools.wraps(func)
        def wrapper(*args, user_id_callable=user_id_callable, on_unauthorized=on_unauthorized, **kwargs):
            assert 'object_id' in kwargs
            object_id = kwargs['object_id']
            version_id = kwargs.get('version_id')
            try:
                logic.objects.get_object(object_id, version_id)
            except logic.errors.ObjectDoesNotExistError:
                return flask.abort(404)
            except logic.errors.ObjectVersionDoesNotExistError:
                return flask.abort(404)
            if not (logic.object_permissions.object_is_public(object_id) and required_object_permissions in Permissions.READ):
                user_id = user_id_callable()
                user = logic.users.get_user(user_id)
                if user.is_readonly and required_object_permissions not in Permissions.READ:
                    return on_unauthorized(object_id)
                user_object_permissions = logic.object_permissions.get_user_object_permissions(object_id=object_id, user_id=user_id)
                if required_object_permissions not in user_object_permissions:
                    return on_unauthorized(object_id)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def load_environment_configuration(env_prefix):
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


def generate_secret_key(num_bits):
    """
    Generates a secure, random key for the application.

    :param num_bits: number of bits of random data in the secret key
    :return: the base64 encoded secret key
    """
    num_bytes = num_bits // 8
    binary_key = os.urandom(num_bytes)
    base64_key = base64.b64encode(binary_key).decode('ascii')
    return base64_key


def empty_database(engine, recreate=False, only_delete=True):
    metadata = sqlalchemy.MetaData(bind=engine)
    # delete views, as SQLAlchemy cannot reflect them
    engine.execute("DROP VIEW IF EXISTS user_object_permissions_by_all")
    # delete tables, etc
    metadata.reflect()
    if only_delete:
        for table in reversed(metadata.sorted_tables):
            engine.execute(table.delete())
        # migration_index needs to be dropped so migration #0 will run
        engine.execute("DROP TABLE IF EXISTS migration_index")
    else:
        metadata.drop_all()
    if recreate:
        # recreate the tables
        db.metadata.create_all(bind=engine)
        # run migrations
        migrations.run(db)
