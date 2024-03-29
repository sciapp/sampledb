import pytest

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
