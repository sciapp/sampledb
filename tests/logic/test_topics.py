import pytest

import sampledb
from sampledb.logic import errors, topics, instruments, actions


def test_check_topic_exists():
    topic = topics.create_topic(
        show_on_frontpage=True,
        show_in_navbar=True,
        name={'en': 'Testing'},
        description={'en': 'Testing Topic'},
        short_description={'en': ''},
        description_is_markdown=True,
        short_description_is_markdown=True
    )
    topics.check_topic_exists(topic.id)
    with pytest.raises(errors.TopicDoesNotExistError):
        topics.check_topic_exists(topic.id + 1)


def test_get_topics():
    t1 = topics.create_topic(
        show_on_frontpage=True,
        show_in_navbar=True,
        name={'en': 'Topic A'},
        description={'en': 'Testing Topic'},
        short_description={'en': ''},
        description_is_markdown=True,
        short_description_is_markdown=True
    )
    t2 = topics.create_topic(
        show_on_frontpage=True,
        show_in_navbar=False,
        name={'en': 'Topic B'},
        description={'en': 'Testing Topic'},
        short_description={'en': ''},
        description_is_markdown=True,
        short_description_is_markdown=True
    )
    t3 = topics.create_topic(
        show_on_frontpage=False,
        show_in_navbar=True,
        name={'en': 'Topic C'},
        description={'en': 'Testing Topic'},
        short_description={'en': ''},
        description_is_markdown=True,
        short_description_is_markdown=True
    )
    t4 = topics.create_topic(
        show_on_frontpage=False,
        show_in_navbar=False,
        name={'en': 'Topic D'},
        description={'en': 'Testing Topic'},
        short_description={'en': ''},
        description_is_markdown=True,
        short_description_is_markdown=True
    )
    topics.set_topics_order([topic.id for topic in [t1, t2, t3, t4]])
    t1 = topics.get_topic(t1.id)
    t2 = topics.get_topic(t2.id)
    t3 = topics.get_topic(t3.id)
    t4 = topics.get_topic(t4.id)
    assert topics.get_topics() == [t1, t2, t3, t4]
    assert topics.get_topics(filter_navbar=True) == [t1, t3]
    assert topics.get_topics(filter_frontpage=True) == [t1, t2]
    assert topics.get_topics(filter_navbar=True, filter_frontpage=True) == [t1]


def test_add_topic_to_order():
    all_topics = [
        topics.create_topic(
            show_on_frontpage=True,
            show_in_navbar=True,
            name={'en': 'Local Topic ' + chr(ord('A') + i)},
            description={'en': ''},
            short_description={'en': ''},
            description_is_markdown=False,
            short_description_is_markdown=False
        )
        for i in range(10)
    ]
    topics.set_topics_order(
        [
            topic.id
            for topic in all_topics
        ]
    )
    ordered_topics = topics.get_topics()
    ordered_topic_ids = [
        topic.id
        for topic in ordered_topics
    ]
    assert ordered_topic_ids == [
        topic.id
        for topic in all_topics
    ]

    new_local_topic = topics.create_topic(
        show_on_frontpage=True,
        show_in_navbar=True,
        name={'en': 'Local Topic A2'},
        description={'en': ''},
        short_description={'en': ''},
        description_is_markdown=False,
        short_description_is_markdown=False
    )
    new_local_topic = topics.get_topic(new_local_topic.id)
    topics.add_topic_to_order(new_local_topic)

    ordered_topics = topics.get_topics()
    ordered_topic_ids = [
        topic.id
        for topic in ordered_topics
    ]
    assert ordered_topic_ids == [all_topics[0].id, new_local_topic.id] + [
        topic.id
        for topic in all_topics[1:]
    ]

def test_actions_use_instrument_topics():
    min_schema = {
        'type': 'object',
        'title': 'Action A',
        'properties': {
            'name': {
                'type': 'text',
                'title': 'name'
            }
        },
        'required': ['name']
    }
    topic_a = topics.create_topic(
        show_on_frontpage=True,
        show_in_navbar=True,
        name={'en': 'Topic A'},
        description={'en': 'Testing Topic'},
        short_description={'en': ''},
        description_is_markdown=True,
        short_description_is_markdown=True
    )
    topic_b = topics.create_topic(
        show_on_frontpage=True,
        show_in_navbar=False,
        name={'en': 'Topic B'},
        description={'en': 'Testing Topic'},
        short_description={'en': ''},
        description_is_markdown=True,
        short_description_is_markdown=True
    )
    instrument_a = instruments.create_instrument()
    topics.set_instrument_topics(instrument_a.id, [topic_a.id])
    action_a = actions.create_action(
        action_type_id=actions.ActionType.SAMPLE_CREATION,
        schema=min_schema
    )
    topics.set_action_topics(action_a.id, [topic_a.id])
    action_b = actions.create_action(
        action_type_id=actions.ActionType.SAMPLE_CREATION,
        schema=min_schema,
        instrument_id=instrument_a.id
    )
    topics.set_action_topics(action_b.id, [topic_b.id])
    assert {action.id for action in actions.get_actions_for_topic(topic_a.id)} == {action_a.id}
    assert {action.id for action in actions.get_actions_for_topic(topic_b.id)} == {action_b.id}
    assert {topic.id for topic in actions.get_action(action_a.id).topics} == {topic_a.id}
    assert {topic.id for topic in actions.get_action(action_b.id).topics} == {topic_b.id}
    actions.update_action(
        action_id=action_b.id,
        schema=min_schema,
        use_instrument_topics=True
    )
    assert {action.id for action in actions.get_actions_for_topic(topic_a.id)} == {action_a.id, action_b.id}
    assert not {action.id for action in actions.get_actions_for_topic(topic_b.id)}
    assert {topic.id for topic in actions.get_action(action_a.id).topics} == {topic_a.id}
    assert {topic.id for topic in actions.get_action(action_b.id).topics} == {topic_a.id}
    topics.set_instrument_topics(instrument_a.id, [topic_a.id, topic_b.id])
    assert {action.id for action in actions.get_actions_for_topic(topic_a.id)} == {action_a.id, action_b.id}
    assert {action.id for action in actions.get_actions_for_topic(topic_b.id)} == {action_b.id}
    assert {topic.id for topic in actions.get_action(action_a.id).topics} == {topic_a.id}
    assert {topic.id for topic in actions.get_action(action_b.id).topics} == {topic_a.id, topic_b.id}


@pytest.mark.parametrize(
    ['use_instrument_action'],
    [
        [True],
        [False],
    ]
)
def test_get_object_topics(use_instrument_action):
    user = sampledb.logic.users.create_user("Example User", "example@example.org", sampledb.models.UserType.PERSON)
    instrument = sampledb.logic.instruments.create_instrument()
    action = sampledb.logic.actions.create_action(
        action_type_id=actions.ActionType.SAMPLE_CREATION,
        schema={
            'type': 'object',
            'title': 'Object Information',
            'properties': {
                'name': {
                    'type': 'text',
                    'title': 'Name'
                }
            },
            'required': ['name']
        },
        instrument_id=(instrument.id if use_instrument_action else None)
    )
    location_a = sampledb.logic.locations.create_location(name={"en": "Example Location"}, description={"en": "Example Location"}, parent_location_id=None,user_id=user.id, type_id=sampledb.models.LocationType.LOCATION)
    location_b = sampledb.logic.locations.create_location(name={"en": "Example Location"}, description={"en": "Example Location"}, parent_location_id=None,user_id=user.id, type_id=sampledb.models.LocationType.LOCATION)

    topics = [
        sampledb.logic.topics.create_topic(
            name={"en": f"Topic {i+1}"},
            description={"en": f"Topic {i+1}"},
            short_description={"en": f"Topic {i+1}"},
            show_on_frontpage=True,
            show_in_navbar=True,
            description_is_markdown=False,
            short_description_is_markdown=False,
        )
        for i in range(5)
    ]
    instrument_topic, action_topic, location_a_topic, location_b_topic, unused_topic = topics
    sampledb.logic.topics.set_instrument_topics(instrument.id, [instrument_topic.id])
    sampledb.logic.topics.set_action_topics(action.id, [action_topic.id])
    sampledb.logic.topics.set_location_topics(location_a.id, [location_a_topic.id])
    sampledb.logic.topics.set_location_topics(location_b.id, [location_b_topic.id])

    object = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            }
        },
        user_id=user.id
    )
    sampledb.logic.action_permissions.set_user_action_permissions(action.id, user.id, sampledb.models.Permissions.NONE)
    assert sampledb.logic.topics.get_topic_ids_by_object_ids([object.id], user.id)[object.id] == ({
        instrument_topic.id: {sampledb.logic.topics.TopicSource.INSTRUMENT}
    } if use_instrument_action else {})
    sampledb.logic.action_permissions.set_user_action_permissions(action.id, user.id, sampledb.models.Permissions.READ)
    assert sampledb.logic.topics.get_topic_ids_by_object_ids([object.id], user.id)[object.id] == {
        action_topic.id: {sampledb.logic.topics.TopicSource.ACTION},
    } | ({
        instrument_topic.id: {sampledb.logic.topics.TopicSource.INSTRUMENT}
    } if use_instrument_action else {})

    sampledb.logic.locations.assign_location_to_object(
        object_id=object.id,
        location_id=location_a.id,
        responsible_user_id=None,
        user_id=user.id,
        description={'en': ''}
    )
    sampledb.logic.location_permissions.set_location_permissions_for_all_users(location_a.id, sampledb.models.Permissions.NONE)
    assert sampledb.logic.topics.get_topic_ids_by_object_ids([object.id], user.id)[object.id] == {
        action_topic.id: {sampledb.logic.topics.TopicSource.ACTION},
    } | ({
        instrument_topic.id: {sampledb.logic.topics.TopicSource.INSTRUMENT}
    } if use_instrument_action else {})
    sampledb.logic.location_permissions.set_user_location_permissions(location_a.id, user.id, sampledb.models.Permissions.READ)
    assert sampledb.logic.topics.get_topic_ids_by_object_ids([object.id], user.id)[object.id] == {
        action_topic.id: {sampledb.logic.topics.TopicSource.ACTION},
        location_a_topic.id: {sampledb.logic.topics.TopicSource.LOCATION},
    } | ({
        instrument_topic.id: {sampledb.logic.topics.TopicSource.INSTRUMENT}
    } if use_instrument_action else {})
    sampledb.logic.locations.assign_location_to_object(
        object_id=object.id,
        location_id=location_b.id,
        responsible_user_id=None,
        user_id=user.id,
        description={'en': ''}
    )
    sampledb.logic.location_permissions.set_location_permissions_for_all_users(location_b.id, sampledb.models.Permissions.NONE)
    assert sampledb.logic.topics.get_topic_ids_by_object_ids([object.id], user.id)[object.id] == {
        action_topic.id: {sampledb.logic.topics.TopicSource.ACTION},
        location_a_topic.id: {sampledb.logic.topics.TopicSource.LOCATION},
    } | ({
        instrument_topic.id: {sampledb.logic.topics.TopicSource.INSTRUMENT}
    } if use_instrument_action else {})
    sampledb.logic.location_permissions.set_user_location_permissions(location_b.id, user.id, sampledb.models.Permissions.READ)
    assert sampledb.logic.topics.get_topic_ids_by_object_ids([object.id], user.id)[object.id] == {
        action_topic.id: {sampledb.logic.topics.TopicSource.ACTION},
        location_a_topic.id: {sampledb.logic.topics.TopicSource.LOCATION},
        location_b_topic.id: {sampledb.logic.topics.TopicSource.LOCATION},
    } | ({
        instrument_topic.id: {sampledb.logic.topics.TopicSource.INSTRUMENT}
    } if use_instrument_action else {})

    sampledb.logic.topics.set_location_topics(location_b.id, [location_b_topic.id, action_topic.id])
    assert sampledb.logic.topics.get_topic_ids_by_object_ids([object.id], user.id)[object.id] == {
        action_topic.id: {sampledb.logic.topics.TopicSource.ACTION, sampledb.logic.topics.TopicSource.LOCATION},
        location_a_topic.id: {sampledb.logic.topics.TopicSource.LOCATION},
        location_b_topic.id: {sampledb.logic.topics.TopicSource.LOCATION},
    } | ({
        instrument_topic.id: {sampledb.logic.topics.TopicSource.INSTRUMENT}
    } if use_instrument_action else {})

    assert set(sampledb.logic.topics.get_topic_ids_by_object_ids([object.id], user.id).keys()) == {object.id}
