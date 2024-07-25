# coding: utf-8
"""
Tags or keywords are a method of organizing object. Internally, tags are part
of an objects data as text entries. In addition, however, the list of tags and
the number of objects each tag has been used for is stored in the database, so
that users can get tag suggestions and see which tags are used more to foster
a more unified vocabulary without strictly enforcing a whitelist of tags.
"""


import dataclasses
import typing
from .. import db
from ..models import tags, objects


@dataclasses.dataclass(frozen=True)
class Tag:
    """
    This class provides an immutable wrapper around models.tags.Tag.
    """
    id: int
    name: str
    uses: int

    @classmethod
    def from_database(cls, tag: tags.Tag) -> 'Tag':
        return Tag(id=tag.id, name=tag.name, uses=tag.uses)


def get_object_tags(object: objects.Object) -> typing.Sequence[str]:
    if object.data is not None and 'tags' in object.data:
        tags_entry = object.data['tags']
        if isinstance(tags_entry, dict) and '_type' in tags_entry and tags_entry['_type'] == 'tags' and 'tags' in tags_entry:
            return [tag.strip() for tag in tags_entry["tags"]]
    return ()


def update_object_tag_usage(object: objects.Object, new_subversion: bool = False) -> None:
    previous_tags: typing.Sequence[str] = ()
    new_tags = get_object_tags(object)
    if object.component_id is None or object.fed_object_id is None or object.fed_version_id is None:
        if object.version_id > 0:
            previous_object = objects.Objects.get_object_version(object.object_id, object.version_id - 1)
            if previous_object is not None:
                previous_tags = get_object_tags(previous_object)
    else:
        current = objects.Objects.get_current_fed_object(object.component_id, object.fed_object_id)
        if current is None:
            return
        if current.version_id != object.version_id:
            return
        if new_subversion:
            previous_object = objects.Objects.get_previous_subversion(object.object_id, object.version_id)
            if previous_object is not None:
                previous_tags = get_object_tags(previous_object)
        elif object.fed_version_id > 0:
            previous_object = None
            prev_version = object.fed_version_id - 1
            while previous_object is None and prev_version >= 0:
                previous_object = objects.Objects.get_fed_object_version(object.component_id, object.fed_object_id, prev_version)
                prev_version -= 1
            if previous_object is not None:
                previous_tags = get_object_tags(previous_object)
    removed_tags = set(previous_tags) - set(new_tags)
    added_tags = set(new_tags) - set(previous_tags)
    for tag_name in added_tags:
        tag = tags.Tag.query.filter_by(name=tag_name).first()
        if tag is not None:
            tag.uses += 1
        else:
            tag = tags.Tag(name=tag_name, uses=1)
        db.session.add(tag)
    for tag_name in removed_tags:
        tag = tags.Tag.query.filter_by(name=tag_name).first()
        if tag is not None:
            tag.uses = max(0, tag.uses - 1)
            if tag.uses > 0:
                db.session.add(tag)
            else:
                db.session.delete(tag)
    db.session.commit()


def get_tags() -> typing.Sequence[Tag]:
    return [Tag.from_database(tag) for tag in tags.Tag.query.order_by(tags.Tag.uses).all()]
