# coding: utf-8
"""

"""

import pytest
import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def user():
    user = sampledb.models.User(
        name="User",
        email="example1@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return user


@pytest.fixture
def action():
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name="",
        description="",
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    return action


def test_simplify_doi():
    with pytest.raises(sampledb.logic.errors.InvalidDOIError):
        sampledb.logic.publications.simplify_doi('invalid')
    with pytest.raises(sampledb.logic.errors.InvalidDOIError):
        sampledb.logic.publications.simplify_doi('10.invalid')
    with pytest.raises(sampledb.logic.errors.InvalidDOIError):
        sampledb.logic.publications.simplify_doi('10./invalid')
    with pytest.raises(sampledb.logic.errors.InvalidDOIError):
        sampledb.logic.publications.simplify_doi('10.doi/invalid')
    with pytest.raises(sampledb.logic.errors.InvalidDOIError):
        sampledb.logic.publications.simplify_doi('10.1000/in<alid')
    with pytest.raises(sampledb.logic.errors.InvalidDOIError):
        sampledb.logic.publications.simplify_doi('10.1000/in>alid')
    with pytest.raises(sampledb.logic.errors.InvalidDOIError):
        sampledb.logic.publications.simplify_doi('10.1000/inval"d')
    sampledb.logic.publications.simplify_doi('10.1000/valid')

    assert sampledb.logic.publications.simplify_doi('10.1000/valid') == '10.1000/valid'
    assert sampledb.logic.publications.simplify_doi('10.1000/VALID') == '10.1000/valid'
    assert sampledb.logic.publications.simplify_doi('doi:10.1000/VALID') == '10.1000/valid'


def test_link_publications_to_objects(user, action):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    assert sampledb.logic.publications.get_publications_for_object(object_id=object.id) == []

    sampledb.logic.publications.link_publication_to_object(user_id=user.id, object_id=object.id, doi='10.1000/valid', title='Test')

    assert len(sampledb.logic.publications.get_publications_for_object(object_id=object.id)) == 1
    publication, = sampledb.logic.publications.get_publications_for_object(object_id=object.id)
    assert publication.doi == '10.1000/valid'
    assert publication.title == 'Test'

    sampledb.logic.publications.link_publication_to_object(user_id=user.id, object_id=object.id, doi='10.1000/valid', title='Title', object_name='Object A')

    assert len(sampledb.logic.publications.get_publications_for_object(object_id=object.id)) == 1
    publication, = sampledb.logic.publications.get_publications_for_object(object_id=object.id)
    assert publication.doi == '10.1000/valid'
    assert publication.title == 'Title'
    assert publication.object_name == 'Object A'

    with pytest.raises(sampledb.logic.errors.ObjectDoesNotExistError):
        sampledb.logic.publications.get_publications_for_object(object_id=object.id + 1)

    assert sampledb.logic.publications.get_object_ids_linked_to_doi('10.1000/valid') == [object.id]
    assert not sampledb.logic.publications.get_object_ids_linked_to_doi('10.1001/valid')
