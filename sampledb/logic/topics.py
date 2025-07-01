import dataclasses
import enum
import typing

from . import errors
from .utils import cache
from .. import db, models, logic
from ..models import actions, topics, instruments, locations, objects


@dataclasses.dataclass(frozen=True)
class Topic:
    """
    This class provides an immutable wrapper around models.topics.Topic.
    """
    id: int
    name: typing.Dict[str, str]
    description: typing.Dict[str, str]
    short_description: typing.Dict[str, str]
    show_on_frontpage: bool
    show_in_navbar: bool
    description_is_markdown: bool
    short_description_is_markdown: bool
    order_index: typing.Optional[int]

    @classmethod
    def from_database(
            cls,
            topic: models.Topic
    ) -> 'Topic':
        wrapped_topic = Topic(
            id=topic.id,
            name=topic.name,
            description=topic.description,
            short_description=topic.short_description,
            show_on_frontpage=topic.show_on_frontpage,
            show_in_navbar=topic.show_in_navbar,
            description_is_markdown=topic.description_is_markdown,
            short_description_is_markdown=topic.short_description_is_markdown,
            order_index=topic.order_index
        )
        return wrapped_topic

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(id={self.id!r})>"


@cache
def check_topic_exists(
        topic_id: int
) -> None:
    """
    Check whether a topic with the given topic ID exists.

    :param topic_id: the ID of an existing topic
    :raise errors.TopicDoesNotExistError: when no topic with the given topic ID exists
    """
    if not db.session.query(db.exists().where(models.Topic.id == topic_id)).scalar():
        raise errors.TopicDoesNotExistError()


def get_topic(topic_id: int) -> Topic:
    """
    Returns the topic with the given topic ID.

    :param topic_id: the ID of an existing topic
    :return: the topic
    :raise errors.TopicDoesNotExistError: when no topic with the
        given topic ID exists
    """
    topic = models.Topic.query.filter_by(id=topic_id).first()
    if topic is None:
        raise errors.TopicDoesNotExistError()
    return Topic.from_database(topic)


def get_topics(filter_frontpage: bool = False, filter_navbar: bool = False) -> typing.List[Topic]:
    """
    Return the list of all existing topics.

    :return: the topics
    """
    query = models.Topic.query
    query = query.order_by(db.nulls_last(models.Topic.order_index), models.Topic.id)

    return [
        Topic.from_database(topic)
        for topic in query.all()
        if (topic.show_in_navbar or not filter_navbar) and (topic.show_on_frontpage or not filter_frontpage)
    ]


def create_topic(
        *,
        name: typing.Dict[str, str],
        description: typing.Dict[str, str],
        short_description: typing.Dict[str, str],
        show_on_frontpage: bool,
        show_in_navbar: bool,
        description_is_markdown: bool,
        short_description_is_markdown: bool
) -> Topic:
    """
    Create a new topic.

    :param name: the unique names of the topic in a dict. Keys are lang codes and values names.
    :param description: (possibly empty) descriptions for the topic in a dict.
        Keys are lang codes and values are descriptions
    :param short_description: (possibly empty) short descriptions for the topic in a dict.
        Keys are lang codes and values are short descriptions
    :param show_on_frontpage: whether this topic should be shown on the frontpage
    :param show_in_navbar: whether this topic should be shown in the navbar
    :param description_is_markdown: whether the description is markdown
    :param short_description_is_markdown: whether the short description is markdown
    :return: the created topic
    """
    topic = models.Topic(
        name=name,
        description=description,
        short_description=short_description,
        show_on_frontpage=show_on_frontpage,
        show_in_navbar=show_in_navbar,
        description_is_markdown=description_is_markdown,
        short_description_is_markdown=short_description_is_markdown,
        order_index=None
    )
    db.session.add(topic)
    db.session.commit()
    return Topic.from_database(topic)


def update_topic(
        *,
        topic_id: int,
        name: typing.Dict[str, str],
        description: typing.Dict[str, str],
        short_description: typing.Dict[str, str],
        show_on_frontpage: bool,
        show_in_navbar: bool,
        description_is_markdown: bool,
        short_description_is_markdown: bool
) -> Topic:
    """
    Update an existing topic.

    :param topic_id: the ID of an existing topic
    :param name: the unique names of the topic in a dict. Keys are lang codes and values names.
    :param description: (possibly empty) descriptions for the topic in a dict.
        Keys are lang codes and values are descriptions
    :param short_description: (possibly empty) short descriptions for the topic in a dict.
        Keys are lang codes and values are short descriptions
    :param show_on_frontpage: whether this topic should be shown on the frontpage
    :param show_in_navbar: whether this topic should be shown in the navbar
    :param description_is_markdown: whether the description is markdown
    :param short_description_is_markdown: whether the short description is markdown
    :return: the created topic
    :raise errors.TopicDoesNotExistError: when no topic with the given topic ID exists
    """
    topic = models.Topic.query.filter_by(id=topic_id).first()
    if topic is None:
        raise errors.TopicDoesNotExistError()
    topic.name = name
    topic.description = description
    topic.short_description = short_description
    topic.show_on_frontpage = show_on_frontpage
    topic.show_in_navbar = show_in_navbar
    topic.description_is_markdown = description_is_markdown
    topic.short_description_is_markdown = short_description_is_markdown
    db.session.add(topic)
    db.session.commit()
    return Topic.from_database(topic)


def set_topics_order(topic_id_list: typing.List[int]) -> None:
    """
    Sets the `order_index` for all topics in the index_list, therefore the order in the list is used.

    :param topic_id_list: list of topic ids
    """
    for i, topic_id in enumerate(topic_id_list):
        topic = models.Topic.query.filter_by(id=topic_id).first()
        if topic is not None:
            topic.order_index = i
    db.session.commit()


def add_topic_to_order(topic: Topic) -> None:
    """
    Insert a topic into the current sort order.

    :param topic: the topic to insert
    """
    if topic.order_index is not None:
        # topic already has a place in the current sort order
        return
    topics = [
        Topic.from_database(other_topic)
        for other_topic in models.Topic.query.filter(models.Topic.order_index != db.null()).order_by(models.Topic.order_index).all()
    ]
    sorted_topics = topics + [topic]
    if topics:
        # check if topics are listed in order of their english names
        english_names = [
            other_topic.name.get('en', '').lower()
            for other_topic in topics
        ]
        english_lexicographical_order = english_names == sorted(english_names)
        if english_lexicographical_order:
            sorted_topics = sorted(sorted_topics, key=lambda t: t.name.get('en', '').lower())
    # update order indices
    index_list = [
        other_topic.id
        for other_topic in sorted_topics
    ]
    set_topics_order(index_list)


def _set_topics(
        mutable_object: typing.Union[actions.Action, instruments.Instrument, locations.Location],
        topic_ids: typing.Sequence[int]
) -> None:
    set_topics = topics.Topic.query.filter(topics.Topic.id.in_(topic_ids)).all()
    if len(set_topics) != len(set(topic_ids)):
        raise errors.TopicDoesNotExistError()
    mutable_object.topics.clear()
    for topic in set_topics:
        mutable_object.topics.append(topic)
    db.session.add(mutable_object)
    db.session.commit()


def set_action_topics(
        action_id: int,
        topic_ids: typing.Sequence[int]
) -> None:
    action = actions.Action.query.filter_by(id=action_id).first()
    if action is None:
        raise errors.ActionDoesNotExistError()
    _set_topics(action, topic_ids)


def set_instrument_topics(
        instrument_id: int,
        topic_ids: typing.Sequence[int]
) -> None:
    instrument = instruments.Instrument.query.filter_by(id=instrument_id).first()
    if instrument is None:
        raise errors.InstrumentDoesNotExistError()
    _set_topics(instrument, topic_ids)


def set_location_topics(
        location_id: int,
        topic_ids: typing.Sequence[int]
) -> None:
    location = locations.Location.query.filter_by(id=location_id).first()
    if location is None:
        raise errors.LocationDoesNotExistError()
    _set_topics(location, topic_ids)


class TopicSource(enum.IntEnum):
    ACTION = 1
    INSTRUMENT = 2
    LOCATION = 3


def get_topic_ids_by_object_ids(
        object_ids: typing.Sequence[int],
        user_id: typing.Optional[int] = None
) -> typing.Dict[int, typing.Dict[int, typing.Set[TopicSource]]]:
    action_topics_select = db.select(
        objects.Objects.current_table.c.object_id, actions.topic_action_association_table.c.topic_id, TopicSource.ACTION, actions.topic_action_association_table.c.action_id
    ).filter(
        actions.topic_action_association_table.c.action_id == objects.Objects.current_table.c.action_id
    )
    if object_ids is not None:
        action_topics_select = action_topics_select.filter(
            objects.Objects.current_table.c.object_id.in_(object_ids)
        )
    instrument_topics_select = db.select(
        objects.Objects.current_table.c.object_id, instruments.topic_instrument_association_table.c.topic_id, TopicSource.INSTRUMENT, instruments.topic_instrument_association_table.c.instrument_id
    ).filter(
        objects.Objects.current_table.c.action_id == actions.Action.id,
        actions.Action.instrument_id == instruments.topic_instrument_association_table.c.instrument_id
    )
    if object_ids is not None:
        instrument_topics_select = instrument_topics_select.filter(
            objects.Objects.current_table.c.object_id.in_(object_ids)
        )

    location_topics_select = db.select(
        locations.ObjectLocationAssignment.object_id, locations.topic_location_association_table.c.topic_id, TopicSource.LOCATION, locations.topic_location_association_table.c.location_id
    ).filter(
        locations.ObjectLocationAssignment.location_id == locations.topic_location_association_table.c.location_id
    )
    if object_ids is not None:
        location_topics_select = location_topics_select.filter(
            locations.ObjectLocationAssignment.object_id.in_(object_ids)
        )
    object_id_topic_id_tuples = db.session.execute(
        action_topics_select.union(
            instrument_topics_select,
            location_topics_select
        )
    ).fetchall()
    topic_ids_by_object_id: typing.Dict[int, typing.Dict[int, typing.Set[TopicSource]]] = {}
    for object_id in object_ids:
        topic_ids_by_object_id[object_id] = {}
    action_ids = set()
    location_ids = set()
    for _, _, topic_source, topic_source_id in object_id_topic_id_tuples:
        if topic_source == TopicSource.ACTION:
            action_ids.add(topic_source_id)
        elif topic_source == TopicSource.LOCATION:
            location_ids.add(topic_source_id)
    action_permissions = logic.action_permissions.get_user_permissions_for_multiple_actions(list(action_ids), user_id)
    location_permissions = logic.location_permissions.get_user_permissions_for_multiple_locations(list(location_ids), user_id)
    for object_id, topic_id, topic_source, topic_source_id in object_id_topic_id_tuples:
        if topic_source == TopicSource.ACTION and models.Permissions.READ not in action_permissions.get(topic_source_id, models.Permissions.NONE):
            continue
        if topic_source == TopicSource.LOCATION and models.Permissions.READ not in location_permissions.get(topic_source_id, models.Permissions.NONE):
            continue
        if topic_id not in topic_ids_by_object_id[object_id]:
            topic_ids_by_object_id[object_id][topic_id] = set()
        topic_ids_by_object_id[object_id][topic_id].add(topic_source)
    return topic_ids_by_object_id
