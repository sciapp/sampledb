import functools
import typing
import secrets

import flask
import flask_login

from .. import db
from ..models import ObjectDataToHTMLCacheEntry, Permissions, Object
from . import errors
from .files import get_file
from .users import get_user
from .components import get_component_by_uuid
from .languages import get_user_language
from .schemas.utils import data_iter, schema_iter
from .object_permissions import get_objects_with_permissions, get_object_if_user_has_permissions
from .utils import get_hash


def _get_object_if_current_user_has_read_permissions(object_id: int, component_uuid: typing.Optional[str] = None) -> typing.Optional[Object]:
    return get_object_if_user_has_permissions(
        user_id=flask_login.current_user.id,
        permissions=Permissions.READ,
        object_id=object_id,
        component_uuid=component_uuid,
    )


def clear_object_data_to_html_cache() -> None:
    ObjectDataToHTMLCacheEntry.query.delete()
    db.session.commit()


def _get_object_data_to_html_cache_entry(
        *,
        object_id: int,
        version_id: int,
        user_language: str,
        metadata_language: str,
        timezone: str,
        workflow_display_mode: bool,
        increase_cache_hit_counter: bool = True
) -> typing.Optional[ObjectDataToHTMLCacheEntry]:
    cache_entry = ObjectDataToHTMLCacheEntry.query.filter_by(
        object_id=object_id,
        version_id=version_id,
        user_language=user_language,
        metadata_language=metadata_language,
        timezone=timezone,
        workflow_display_mode=workflow_display_mode,
    ).first()
    if cache_entry is not None and increase_cache_hit_counter:
        cache_entry.cache_hit_counter += 1
        db.session.add(cache_entry)
        db.session.commit()
    return cache_entry


def _set_object_data_to_html_cache_entry(
        *,
        object_id: int,
        version_id: int,
        user_language: str,
        metadata_language: str,
        timezone: str,
        workflow_display_mode: bool,
        html: str,
        object_dependencies: typing.List[typing.Tuple[int, typing.Optional[str], typing.Optional[int]]],
        user_dependencies: typing.List[typing.Tuple[int, typing.Optional[int], typing.Optional[str]]],
        component_dependencies: typing.List[typing.Tuple[str, typing.Optional[int], typing.Optional[str], typing.Optional[str]]],
        file_dependencies: typing.List[typing.Tuple[int, int, typing.Optional[str], typing.Optional[bool], typing.Optional[str]]],
        id_prefix_root_placeholder: str,
        hashes_to_replace: typing.Dict[str, str],
) -> None:
    cache_entry = ObjectDataToHTMLCacheEntry(
        object_id=object_id,
        version_id=version_id,
        user_language=user_language,
        metadata_language=metadata_language,
        timezone=timezone,
        workflow_display_mode=workflow_display_mode,
        html=html,
        object_dependencies=object_dependencies,
        user_dependencies=user_dependencies,
        component_dependencies=component_dependencies,
        file_dependencies=file_dependencies,
        id_prefix_root_placeholder=id_prefix_root_placeholder,
        hashes_to_replace=hashes_to_replace,
        cache_hit_counter=0,
    )
    db.session.merge(cache_entry)
    db.session.commit()


def object_data_to_html(
        *,
        object_id: int,
        version_id: int,
        metadata_language: typing.Optional[str],
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any],
        files: typing.List[typing.Any],
        id_prefix_root: str,
        workflow_display_mode: bool = False
) -> str:
    """
    Render the object data to HTML.

    :param object_id: the ID of the object being rendered
    :param version_id: the version ID of the object being rendered
    :param metadata_language: the metadata language code
    :param data: the object data
    :param schema: the object schema
    :param files: the files for the object
    :param id_prefix_root: the ID prefix root
    :param workflow_display_mode: whether the object is in workflow display mode
    :return: the rendered HTML
    """
    timezone = flask_login.current_user.timezone
    can_cache = flask.current_app.config['ENABLE_OBJECT_DATA_HTML_CACHE'] and timezone is not None
    user_language = get_user_language(flask_login.current_user).lang_code
    if can_cache:
        cache_entry = _get_object_data_to_html_cache_entry(
            object_id=object_id,
            version_id=version_id,
            user_language=user_language,
            metadata_language=metadata_language or user_language,
            timezone=typing.cast(str, timezone),
            workflow_display_mode=workflow_display_mode
        )
    else:
        cache_entry = None

    if cache_entry is not None:
        cached_html: typing.Optional[str] = cache_entry.html
        object_dependencies = typing.cast(typing.Set[typing.Tuple[int, typing.Optional[str], typing.Optional[int]]], {tuple(object_dependency) for object_dependency in cache_entry.object_dependencies})
        user_dependencies = typing.cast(typing.Set[typing.Tuple[int, typing.Optional[int], typing.Optional[str]]], {tuple(user_dependency) for user_dependency in cache_entry.user_dependencies})
        component_dependencies = typing.cast(typing.Set[typing.Tuple[str, typing.Optional[int], typing.Optional[str], typing.Optional[str]]], {tuple(component_dependency) for component_dependency in cache_entry.component_dependencies})
        file_dependencies = typing.cast(typing.Set[typing.Tuple[int, int, typing.Optional[str], typing.Optional[bool], typing.Optional[str]]], {tuple(file_dependency) for file_dependency in cache_entry.file_dependencies})
        id_prefix_root_placeholder = cache_entry.id_prefix_root_placeholder
        if cached_html is not None and object_dependencies:
            local_object_ids = set()
            for object_dependency in object_dependencies:
                referenced_object_id, component_uuid, _ = object_dependency
                if component_uuid is None:
                    local_object_ids.add(referenced_object_id)
            local_objects = get_objects_with_permissions(user_id=flask_login.current_user.id, permissions=Permissions.READ, object_ids=list(local_object_ids), name_only=True)
            local_objects_by_id = {
                object.object_id: object
                for object in local_objects
            }
            for referenced_object_id, component_uuid, object_version_or_none in object_dependencies:
                if component_uuid is None:
                    object_or_none = local_objects_by_id.get(referenced_object_id)
                else:
                    object_or_none = _get_object_if_current_user_has_read_permissions(object_id=referenced_object_id, component_uuid=component_uuid)
                if object_version_or_none != (object_or_none.version_id if object_or_none is not None else None):
                    cached_html = None
                    break
        if cached_html is not None and user_dependencies:
            for user_id, component_id, user_name_or_none in user_dependencies:
                try:
                    user_or_none = get_user(user_id=user_id, component_id=component_id)
                except errors.UserDoesNotExistError:
                    user_or_none = None
                if user_name_or_none != (user_or_none.name if user_or_none is not None else None):
                    cached_html = None
                    break
        if cached_html is not None and component_dependencies:
            for component_uuid, component_id, component_name, component_address in component_dependencies:
                try:
                    component = get_component_by_uuid(component_uuid)
                    if component_id != component.id or component_name != component.name or component_address != component.address:
                        cached_html = None
                        break
                except errors.ComponentDoesNotExistError:
                    if component_id is not None or component_name is not None or component_address is not None:
                        cached_html = None
                        break
        if cached_html is not None and file_dependencies:
            for file_id, file_object_id, component_uuid, file_is_hidden, file_title in file_dependencies:
                try:
                    if component_uuid:
                        component_id = get_component_by_uuid(component_uuid).id
                    else:
                        component_id = None
                    file_or_none = get_file(file_id, file_object_id, component_id)
                except errors.ComponentDoesNotExistError:
                    file_or_none = None
                except errors.FileDoesNotExistError:
                    file_or_none = None
                if file_or_none is None and (file_is_hidden is not None or file_title is not None):
                    cached_html = None
                    break
                elif file_or_none is not None and (file_is_hidden != file_or_none.is_hidden or file_title != file_or_none.title):
                    cached_html = None
                    break
        if cached_html is not None:
            html = cached_html.replace(id_prefix_root_placeholder, id_prefix_root)
            for hash, text in cache_entry.hashes_to_replace.items():
                text = text.replace(id_prefix_root_placeholder, id_prefix_root)
                html = html.replace(hash, get_hash(text))
            return html

    object_dependencies = set()
    user_dependencies = set()
    component_dependencies = set()
    file_dependencies = set()
    if can_cache:
        for _, property_schema in schema_iter(schema, filter_property_types={'object_reference', 'sample', 'measurement'}):
            if 'style' not in property_schema:
                continue
            property_style = property_schema['style']
            if isinstance(property_style, dict):
                property_style = property_style.get('view')
            if property_style == 'include':
                can_cache = False
                break

    if can_cache:
        for _, property_data in data_iter(data, filter_property_types={'user', 'object_reference', 'sample', 'measurement', 'file'}):
            if not isinstance(property_data, dict):
                continue
            component_uuid = property_data.get('component_uuid')
            component_id = None
            if component_uuid is not None:
                try:
                    component = get_component_by_uuid(component_uuid)
                    component_id = component.id
                    component_dependencies.add((component_uuid, component.id, component.name, component.address))
                except errors.ComponentDoesNotExistError:
                    component_dependencies.add((component_uuid, None, None, None))
            if 'user_id' in property_data:
                user_id = property_data['user_id']
                try:
                    user = get_user(user_id=user_id, component_id=component_id)
                    user_dependencies.add((user.id, user.component_id, user.name))
                except errors.UserDoesNotExistError:
                    user_dependencies.add((user_id, component_id, None))
            if 'object_id' in property_data:
                referenced_object_id = property_data['object_id']
                object_or_none = _get_object_if_current_user_has_read_permissions(object_id=referenced_object_id, component_uuid=component_uuid)
                object_dependencies.add((referenced_object_id, component_uuid, object_or_none.version_id if object_or_none is not None else None))
            if 'file_id' in property_data:
                file_id = property_data['file_id']
                try:
                    file = get_file(file_id, object_id, component_uuid)
                    file_dependencies.add((file_id, object_id, component_uuid, file.is_hidden, file.title))
                except errors.FileDoesNotExistError:
                    file_dependencies.add((file_id, object_id, component_uuid, None, None))

    if can_cache:
        id_prefix_root_placeholder = f"id_prefix_root_placeholder_{secrets.token_hex(32)}"
    else:
        id_prefix_root_placeholder = id_prefix_root

    hashes_to_replace: typing.Dict[str, str] = {}

    def _get_hash(text: str, hashes_to_replace: typing.Dict[str, str], id_prefix_root_placeholder: str) -> str:
        hash = get_hash(text)
        if id_prefix_root_placeholder in text:
            hashes_to_replace[hash] = text
        return hash

    try:
        flask.current_app.jinja_env.filters['get_hash'] = functools.partial(_get_hash, hashes_to_replace=hashes_to_replace, id_prefix_root_placeholder=id_prefix_root_placeholder)
        html = flask.render_template(
            'objects/view/standalone_object_metadata.html',
            object_id=object_id,
            data=data,
            schema=schema,
            metadata_language=metadata_language,
            diff=None,
            previous_schema=None,
            indent_level=0,
            show_indent_border=False,
            property_path=(),
            get_object_if_current_user_has_read_permissions=_get_object_if_current_user_has_read_permissions,
            id_prefix_root=id_prefix_root_placeholder,
            id_prefix=id_prefix_root_placeholder + '_',
            workflow_display_mode=workflow_display_mode,
            files=files,
        )
    finally:
        flask.current_app.jinja_env.filters['get_hash'] = get_hash

    if can_cache:
        _set_object_data_to_html_cache_entry(
            object_id=object_id,
            version_id=version_id,
            user_language=user_language,
            metadata_language=metadata_language or user_language,
            timezone=flask_login.current_user.timezone,  # type: ignore
            workflow_display_mode=workflow_display_mode,
            html=html,
            object_dependencies=list(object_dependencies),
            user_dependencies=list(user_dependencies),
            component_dependencies=list(component_dependencies),
            file_dependencies=list(file_dependencies),
            id_prefix_root_placeholder=id_prefix_root_placeholder,
            hashes_to_replace=hashes_to_replace,
        )
        html = html.replace(id_prefix_root_placeholder, id_prefix_root)
        for hash, text in hashes_to_replace.items():
            text = text.replace(id_prefix_root_placeholder, id_prefix_root)
            html = html.replace(hash, get_hash(text))

    return html
