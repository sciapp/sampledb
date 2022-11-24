import pytest

import sampledb.logic
import sampledb.models


@pytest.fixture
def user_id():
    return sampledb.logic.users.create_user(
        name="Test User",
        email="example@example.org",
        type=sampledb.models.UserType.PERSON
    ).id


@pytest.fixture
def basic_group_id(user_id):
    return sampledb.logic.groups.create_group(
        name={"en": "Test Group"},
        description={},
        initial_user_id=user_id
    ).id


@pytest.fixture
def other_basic_group_id(user_id):
    return sampledb.logic.groups.create_group(
        name={"en": "Test Group 2"},
        description={},
        initial_user_id=user_id
    ).id


@pytest.fixture
def project_group_id(user_id):
    return sampledb.logic.projects.create_project(
        name={"en": "Test Group"},
        description={},
        initial_user_id=user_id
    ).id


def test_create_group_categories():
    category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category'}
    )
    assert category.name['en'] == 'Test Category'
    assert category.parent_category_id is None

    child_category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 2'},
        parent_category_id=category.id
    )
    assert child_category.name['en'] == 'Test Category 2'
    assert child_category.parent_category_id == category.id

    with pytest.raises(sampledb.logic.errors.GroupCategoryDoesNotExistError):
        sampledb.logic.group_categories.create_group_category(
            name={'en': 'Test Category 3'},
            parent_category_id=category.id + 1000
        )

def test_update_group_categories():
    category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category'}
    )
    other_category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 2'},
        parent_category_id=category.id
    )
    sampledb.logic.group_categories.update_group_category(other_category.id, name={'en': 'Test'}, parent_category_id=category.id)
    other_category = sampledb.logic.group_categories.get_group_category(other_category.id)
    assert other_category.name == {'en': 'Test'}
    assert other_category.parent_category_id == category.id
    with pytest.raises(sampledb.logic.errors.CyclicGroupCategoryError):
        sampledb.logic.group_categories.update_group_category(category.id, name=category.name, parent_category_id=other_category.id)
    assert category.name == {'en': 'Test Category'}
    assert category.parent_category_id is None


def test_delete_group_categories(basic_group_id, project_group_id):
    category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category'}
    )
    assert sampledb.models.group_categories.GroupCategory.query.filter_by(
        id=category.id
    ).first() is not None
    sampledb.logic.group_categories.delete_group_category(category.id)
    assert sampledb.models.group_categories.GroupCategory.query.filter_by(
        id=category.id
    ).first() is None
    with pytest.raises(sampledb.logic.errors.GroupCategoryDoesNotExistError):
        sampledb.logic.group_categories.delete_group_category(category.id)

    category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category'}
    )
    child_category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 2'},
        parent_category_id=category.id
    )
    sampledb.logic.group_categories.delete_group_category(category.id)
    assert sampledb.models.group_categories.GroupCategory.query.filter_by(
        id=category.id
    ).first() is None
    assert sampledb.models.group_categories.GroupCategory.query.filter_by(
        id=child_category.id
    ).first() is None

    category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category'}
    )
    child_category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 2'},
        parent_category_id=category.id
    )
    sampledb.logic.group_categories.set_basic_group_categories(
        basic_group_id,
        (category.id, child_category.id)
    )
    sampledb.logic.group_categories.set_project_group_categories(
        project_group_id,
        (category.id, child_category.id)
    )
    assert len(sampledb.models.Group.query.filter_by(id=basic_group_id).first().categories) == 2
    assert len(sampledb.models.Project.query.filter_by(id=project_group_id).first().categories) == 2
    sampledb.logic.group_categories.delete_group_category(category.id)
    assert len(sampledb.models.Group.query.filter_by(id=basic_group_id).first().categories) == 0
    assert len(sampledb.models.Project.query.filter_by(id=project_group_id).first().categories) == 0


def test_set_basic_group_categories(basic_group_id):
    category1 = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 1'}
    )
    category2 = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 2'}
    )
    sampledb.logic.group_categories.set_basic_group_categories(
        basic_group_id,
        (category1.id,)
    )
    assert {
        category.id
        for category in sampledb.models.Group.query.filter_by(id=basic_group_id).first().categories
    } == {category1.id}
    sampledb.logic.group_categories.set_basic_group_categories(
        basic_group_id,
        (category1.id, category2.id)
    )
    assert {
        category.id
        for category in sampledb.models.Group.query.filter_by(id=basic_group_id).first().categories
    } == {category1.id, category2.id}
    sampledb.logic.group_categories.set_basic_group_categories(
        basic_group_id,
        ()
    )
    assert {
        category.id
        for category in sampledb.models.Group.query.filter_by(id=basic_group_id).first().categories
    } == set()


def test_set_project_group_categories(project_group_id):
    category1 = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 1'}
    )
    category2 = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 2'}
    )
    sampledb.logic.group_categories.set_project_group_categories(
        project_group_id,
        (category1.id,)
    )
    assert {
        category.id
        for category in sampledb.models.Project.query.filter_by(id=project_group_id).first().categories
    } == {category1.id}
    sampledb.logic.group_categories.set_project_group_categories(
        project_group_id,
        (category1.id, category2.id)
    )
    assert {
        category.id
        for category in sampledb.models.Project.query.filter_by(id=project_group_id).first().categories
    } == {category1.id, category2.id}
    sampledb.logic.group_categories.set_project_group_categories(
        project_group_id,
        ()
    )
    assert {
        category.id
        for category in sampledb.models.Project.query.filter_by(id=project_group_id).first().categories
    } == set()


def test_get_group_categories():
    category1 = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 1'}
    )
    category2 = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 2'}
    )
    categories = sampledb.logic.group_categories.get_group_categories()
    assert len(categories) == 2
    assert {category.id for category in categories} == {category1.id, category2.id}
    assert categories[0].id == min(category1.id, category2.id)
    assert categories[1].id == max(category1.id, category2.id)


def test_get_group_category():
    category1 = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 1'}
    )
    category = sampledb.logic.group_categories.get_group_category(category1.id)
    assert category.id == category1.id
    assert category.name == category1.name
    assert category.parent_category_id == category1.parent_category_id
    with pytest.raises(sampledb.logic.errors.GroupCategoryDoesNotExistError):
        sampledb.logic.group_categories.get_group_category(category1.id + 1000)


def test_get_group_category_tree(basic_group_id, project_group_id, other_basic_group_id):
    category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category'}
    )
    child_category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 2'},
        parent_category_id=category.id
    )
    sampledb.logic.group_categories.set_basic_group_categories(
        basic_group_id,
        (child_category.id, )
    )
    sampledb.logic.group_categories.set_project_group_categories(
        project_group_id,
        (category.id, child_category.id)
    )
    group_category_id_tree = sampledb.logic.group_categories.get_group_category_tree()
    assert group_category_id_tree == {
        'basic_group_ids': {other_basic_group_id},
        'project_group_ids': set(),
        'child_categories': {
            category.id: {
                'basic_group_ids': set(),
                'project_group_ids': {project_group_id},
                'child_categories': {
                    child_category.id: {
                        'basic_group_ids': {basic_group_id},
                        'project_group_ids': {project_group_id},
                        'child_categories': {},
                        'contains_basic_groups': True,
                        'contains_project_groups': True
                    }
                },
                'contains_basic_groups': True,
                'contains_project_groups': True
            }
        },
        'contains_basic_groups': True,
        'contains_project_groups': True
    }
    group_category_id_tree = sampledb.logic.group_categories.get_group_category_tree(
        basic_group_ids={basic_group_id},
        project_group_ids=set()
    )
    assert group_category_id_tree == {
        'basic_group_ids': set(),
        'project_group_ids': set(),
        'child_categories': {
            category.id: {
                'basic_group_ids': set(),
                'project_group_ids': set(),
                'child_categories': {
                    child_category.id: {
                        'basic_group_ids': {basic_group_id},
                        'project_group_ids': set(),
                        'child_categories': {},
                        'contains_basic_groups': True,
                        'contains_project_groups': False
                    }
                },
                'contains_basic_groups': True,
                'contains_project_groups': False
            }
        },
        'contains_basic_groups': True,
        'contains_project_groups': False
    }


def test_get_full_group_category_names():
    category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category'}
    )
    child_category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 2'},
        parent_category_id=category.id
    )
    assert sampledb.logic.group_categories.get_full_group_category_names() == {
        category.id: (category.name, ),
        child_category.id: (category.name, child_category.name)
    }


def test_category_has_ancestor():
    category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category'}
    )
    child_category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 2'},
        parent_category_id=category.id
    )
    other_category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category 3'}
    )
    assert sampledb.logic.group_categories.category_has_ancestor(category.id, child_category.id) is False
    assert sampledb.logic.group_categories.category_has_ancestor(child_category.id, category.id) is True
    assert sampledb.logic.group_categories.category_has_ancestor(category.id, other_category.id) is False
    assert sampledb.logic.group_categories.category_has_ancestor(child_category.id, other_category.id) is False


def test_get_basic_group_categories(basic_group_id):
    category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category'}
    )
    assert sampledb.logic.group_categories.get_basic_group_categories(basic_group_id) == ()
    sampledb.logic.group_categories.set_basic_group_categories(basic_group_id, (category.id,))
    assert sampledb.logic.group_categories.get_basic_group_categories(basic_group_id) == (category,)


def test_get_project_group_categories(project_group_id):
    category = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Test Category'}
    )
    assert sampledb.logic.group_categories.get_project_group_categories(project_group_id) == ()
    sampledb.logic.group_categories.set_project_group_categories(project_group_id, (category.id,))
    assert sampledb.logic.group_categories.get_project_group_categories(project_group_id) == (category,)
