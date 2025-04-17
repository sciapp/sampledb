import pytest

import sampledb.logic

@pytest.fixture
def user():
    return sampledb.logic.users.create_user(
        name='Test User',
        email='example@example.org',
        type=sampledb.logic.users.UserType.PERSON
    )

@pytest.fixture
def other_user():
    return sampledb.logic.users.create_user(
        name='Test User',
        email='example@example.org',
        type=sampledb.logic.users.UserType.PERSON
    )

@pytest.fixture
def info_page():
    return sampledb.logic.info_pages.create_info_page(
        title={
            'en': 'Title'
        },
        content={
            'en': 'Content'
        },
        endpoint='frontend.index',
        disabled=False
    )

def test_get_info_pages():
    assert sampledb.logic.info_pages.get_info_pages() == []
    info_page = sampledb.logic.info_pages.create_info_page(
        title={
            'en': 'Title'
        },
        content={
            'en': 'Content'
        },
        endpoint='frontend.index',
        disabled=False
    )
    info_pages = sampledb.logic.info_pages.get_info_pages()
    assert info_pages[0] == info_page
    assert len(info_pages) == 1
    assert info_pages[0].title == {'en': 'Title'}
    assert info_pages[0].content == {'en': 'Content'}
    assert info_pages[0].endpoint == 'frontend.index'
    assert not info_pages[0].disabled

def test_get_info_page(info_page):
    with pytest.raises(sampledb.logic.errors.InfoPageDoesNotExistError):
        sampledb.logic.info_pages.get_info_page(info_page.id+1)
    assert sampledb.logic.info_pages.get_info_page(info_page.id) == info_page

def test_get_info_pages_for_endpoint(user):
    assert sampledb.logic.info_pages.get_info_pages_for_endpoint('frontend.index', None, False) == []
    info_page = sampledb.logic.info_pages.create_info_page(
        title={
            'en': 'Title'
        },
        content={
            'en': 'Content'
        },
        endpoint='frontend.index',
        disabled=False
    )
    assert sampledb.logic.info_pages.get_info_pages_for_endpoint('frontend.index', None, False) == [info_page]
    sampledb.logic.info_pages.set_info_page_disabled(info_page.id, True)
    info_page = sampledb.logic.info_pages.get_info_page(info_page.id)
    assert sampledb.logic.info_pages.get_info_pages_for_endpoint('frontend.index', None, False) == [info_page]
    assert sampledb.logic.info_pages.get_info_pages_for_endpoint('frontend.index', None, True) == []
    assert sampledb.logic.info_pages.get_info_pages_for_endpoint('frontend.index', user.id, False) == [info_page]
    assert sampledb.logic.info_pages.get_info_pages_for_endpoint('frontend.index', user.id, True) == []
    sampledb.logic.info_pages.acknowledge_info_pages({info_page.id}, user.id)
    assert sampledb.logic.info_pages.get_info_pages_for_endpoint('frontend.index', user.id, False) == []
    assert sampledb.logic.info_pages.get_info_pages_for_endpoint('frontend.index', user.id, True) == []

def test_acknowledge_info_pages(user, other_user, info_page):
    with pytest.raises(sampledb.logic.errors.InfoPageDoesNotExistError):
        sampledb.logic.info_pages.acknowledge_info_pages({info_page.id + 1}, user.id)
    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.info_pages.acknowledge_info_pages({info_page.id}, max(user.id, other_user.id)+1)
    assert sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id) == {}
    sampledb.logic.info_pages.acknowledge_info_pages({info_page.id}, user.id)
    acknowledgements = sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
    assert set(acknowledgements.keys()) == {user.id}
    assert acknowledgements[user.id] is not None
    sampledb.logic.info_pages.acknowledge_info_page_for_existing_users(info_page.id)
    acknowledgements = sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
    assert set(acknowledgements.keys()) == {user.id, other_user.id}
    assert acknowledgements[user.id] is not None
    assert acknowledgements[other_user.id] is None
    sampledb.logic.info_pages.acknowledge_info_pages({info_page.id}, other_user.id)
    acknowledgements = sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)
    assert set(acknowledgements.keys()) == {user.id, other_user.id}
    assert acknowledgements[user.id] is not None
    assert acknowledgements[other_user.id] is not None
    assert acknowledgements[user.id] < acknowledgements[other_user.id]

def test_acknowledge_info_page_for_existing_users(user, info_page):
    with pytest.raises(sampledb.logic.errors.InfoPageDoesNotExistError):
        sampledb.logic.info_pages.acknowledge_info_page_for_existing_users(info_page.id + 1)
    assert sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id) == {}
    sampledb.logic.info_pages.acknowledge_info_page_for_existing_users(info_page.id)
    assert sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id) == {user.id: None}

def test_clear_acknowledgements_for_info_page(user, other_user, info_page):
    with pytest.raises(sampledb.logic.errors.InfoPageDoesNotExistError):
        sampledb.logic.info_pages.clear_acknowledgements_for_info_page(info_page.id + 1)
    assert set(sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id).keys()) == set()
    sampledb.logic.info_pages.clear_acknowledgements_for_info_page(info_page.id)
    assert set(sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id).keys()) == set()
    sampledb.logic.info_pages.acknowledge_info_page_for_existing_users(info_page.id)
    assert set(sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id).keys()) == {user.id, other_user.id}
    sampledb.logic.info_pages.clear_acknowledgements_for_info_page(info_page.id)
    assert set(sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id).keys()) == {user.id, other_user.id}
    sampledb.logic.info_pages.acknowledge_info_pages({info_page.id}, user.id)
    assert set(sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id).keys()) == {user.id, other_user.id}
    sampledb.logic.info_pages.clear_acknowledgements_for_info_page(info_page.id)
    assert set(sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id).keys()) == {other_user.id}

def test_get_acknowledgements_for_info_page(user, info_page):
    with pytest.raises(sampledb.logic.errors.InfoPageDoesNotExistError):
        sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id + 1)
    assert sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id) == {}
    sampledb.logic.info_pages.acknowledge_info_page_for_existing_users(info_page.id)
    assert sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id) == {user.id: None}
    sampledb.logic.info_pages.acknowledge_info_pages({info_page.id}, user.id)
    assert sampledb.logic.info_pages.get_acknowledgements_for_info_page(info_page.id)[user.id] is not None

def test_set_info_page_disabled(info_page):
    with pytest.raises(sampledb.logic.errors.InfoPageDoesNotExistError):
        sampledb.logic.info_pages.set_info_page_disabled(info_page.id + 1)
    assert not sampledb.logic.info_pages.get_info_page(info_page.id).disabled
    sampledb.logic.info_pages.set_info_page_disabled(info_page.id)
    assert sampledb.logic.info_pages.get_info_page(info_page.id).disabled
    sampledb.logic.info_pages.set_info_page_disabled(info_page.id, False)
    assert not sampledb.logic.info_pages.get_info_page(info_page.id).disabled

def test_update_info_page(info_page):
    with pytest.raises(sampledb.logic.errors.InfoPageDoesNotExistError):
        sampledb.logic.info_pages.update_info_page(
            info_page_id=info_page.id + 1,
            title=info_page.title,
            content=info_page.content,
            endpoint=info_page.endpoint
        )
    assert sampledb.logic.info_pages.get_info_page(info_page.id).title == {'en': 'Title'}
    assert sampledb.logic.info_pages.get_info_page(info_page.id).content == {'en': 'Content'}
    assert sampledb.logic.info_pages.get_info_page(info_page.id).endpoint == 'frontend.index'
    sampledb.logic.info_pages.update_info_page(
        info_page_id=info_page.id,
        title={'en': 'New Title'},
        content={'en': 'New Content'},
        endpoint='frontend.sign_in'
    )
    assert sampledb.logic.info_pages.get_info_page(info_page.id).title == {'en': 'New Title'}
    assert sampledb.logic.info_pages.get_info_page(info_page.id).content == {'en': 'New Content'}
    assert sampledb.logic.info_pages.get_info_page(info_page.id).endpoint == 'frontend.sign_in'
    sampledb.logic.info_pages.update_info_page(
        info_page_id=info_page.id,
        title={'en': 'New Title'},
        content={'en': 'New Content'},
        endpoint=None
    )
    assert sampledb.logic.info_pages.get_info_page(info_page.id).endpoint is None

def test_delete_info_page(user, info_page):
    with pytest.raises(sampledb.logic.errors.InfoPageDoesNotExistError):
        sampledb.logic.info_pages.delete_info_page(info_page.id + 1)
    sampledb.logic.info_pages.acknowledge_info_pages({info_page.id}, user.id)
    sampledb.logic.info_pages.delete_info_page(info_page.id)

def test_get_url_rules_by_endpoint():
    assert sampledb.logic.info_pages.get_url_rules_by_endpoint()['frontend.index'] == ['/']
    assert sampledb.logic.info_pages.get_url_rules_by_endpoint()['frontend.objects'] == ['/objects/']
