import typing
import dataclasses

from .. import db
from ..models import group_categories, groups, projects
from . import errors


@dataclasses.dataclass(frozen=True)
class GroupCategory:
    """
    This class provides an immutable wrapper around models.group_categories.GroupCategory.
    """
    id: int
    name: typing.Dict[str, str]
    parent_category_id: typing.Optional[int]

    @classmethod
    def from_database(cls, category: group_categories.GroupCategory) -> 'GroupCategory':
        return GroupCategory(
            id=category.id,
            name=category.name,
            parent_category_id=category.parent_category_id
        )


def set_basic_group_categories(
        basic_group_id: int,
        category_ids: typing.Sequence[int]
) -> None:
    """
    Set the categories for a basic group.

    :param basic_group_id: the ID of an existing basic group
    :param category_ids: a list of group category IDs
    :raise errors.GroupDoesNotExistError: is the basic group does not exist
    :raise errors.GroupCategoryDoesNotExistError: if one of the categories does
        not exist
    """
    basic_group = groups.Group.query.filter_by(id=basic_group_id).first()
    if basic_group is None:
        raise errors.GroupDoesNotExistError()
    _set_group_categories(
        group=basic_group,
        category_ids=category_ids
    )


def set_project_group_categories(
        project_group_id: int,
        category_ids: typing.Sequence[int]
) -> None:
    """
    Set the categories for a project group.

    :param project_group_id: the ID of an existing project group
    :param category_ids: a list of group category IDs
    :raise errors.ProjectDoesNotExistError: is the project group does not exist
    :raise errors.GroupCategoryDoesNotExistError: if one of the categories does
        not exist
    """
    project_group = projects.Project.query.filter_by(id=project_group_id).first()
    if project_group is None:
        raise errors.ProjectDoesNotExistError()
    _set_group_categories(
        group=project_group,
        category_ids=category_ids
    )


def _set_group_categories(
        group: typing.Union[projects.Project, groups.Group],
        category_ids: typing.Sequence[int]
) -> None:
    categories = group_categories.GroupCategory.query.filter(group_categories.GroupCategory.id.in_(category_ids)).all()
    if len(categories) != len(set(category_ids)):
        raise errors.GroupCategoryDoesNotExistError()
    group.categories.clear()
    for category in categories:
        group.categories.append(category)
    db.session.add(group)
    db.session.commit()


def create_group_category(
        *,
        name: typing.Dict[str, str],
        parent_category_id: typing.Optional[int] = None
) -> GroupCategory:
    """
    Create a group category.

    :param name: the name translations
    :param parent_category_id: the ID of a parent category, or None
    :raise errors.GroupCategoryDoesNotExistError: if the parent category does
        not exist
    """
    if parent_category_id is not None:
        parent_category = group_categories.GroupCategory.query.filter_by(
            id=parent_category_id
        ).first()
        if parent_category is None:
            raise errors.GroupCategoryDoesNotExistError()
    category = group_categories.GroupCategory(
        name=name,
        parent_category_id=parent_category_id
    )
    db.session.add(category)
    db.session.commit()
    return GroupCategory.from_database(category)


def category_has_ancestor(
        category_id: int,
        potential_ancestor_id: int
) -> bool:
    """
    Check if a category has another category as an ancestor.

    :param category_id: the ID of an existing category
    :param potential_ancestor_id: the ID of an existing category
    :return: whether the potential ancestor category is indeed an ancestor
        of the given category
    :raise errors.GroupCategoryDoesNotExistError: if one of the checked
        categories does not exist
    """
    ancestor_category_id: typing.Optional[int] = category_id
    while ancestor_category_id is not None:
        if ancestor_category_id == potential_ancestor_id:
            return True
        ancestor_category = group_categories.GroupCategory.query.filter_by(id=ancestor_category_id).first()
        if ancestor_category is None:
            raise errors.GroupCategoryDoesNotExistError()
        ancestor_category_id = ancestor_category.parent_category_id
    return False


def update_group_category(
        category_id: int,
        name: typing.Dict[str, str],
        parent_category_id: typing.Optional[int]
) -> None:
    """
    Update a group category.

    :param category_id: the ID of an existing category
    :param name: the name translations
    :param parent_category_id: the ID of a parent category, or None
    :raise errors.GroupCategoryDoesNotExistError: if the category or parent
        category does not exist
    :raise errors.CyclicGroupCategoryError: if the new parent category would
        lead to a cyclic parent-child relationship
    """
    category = group_categories.GroupCategory.query.filter_by(id=category_id).first()
    if category is None:
        raise errors.GroupCategoryDoesNotExistError()
    # ensure this would not create a cyclical parent-child-relationship
    if parent_category_id != category.parent_category_id and parent_category_id is not None and category_has_ancestor(parent_category_id, category_id):
        raise errors.CyclicGroupCategoryError()
    category.name = name
    category.parent_category_id = parent_category_id
    db.session.add(category)
    db.session.commit()


def delete_group_category(
        category_id: int
) -> None:
    """
    Delete a group category.

    :param category_id: the ID of an existing category
    :raise errors.GroupCategoryDoesNotExistError: if the category does not
        exist
    """
    category = group_categories.GroupCategory.query.filter_by(id=category_id).first()
    if category is None:
        raise errors.GroupCategoryDoesNotExistError()
    db.session.delete(category)
    db.session.commit()


def get_group_category(
        category_id: int
) -> GroupCategory:
    """
    Get a group category.

    :param category_id: the ID of an existing category
    :return: the group category
    :raise errors.GroupCategoryDoesNotExistError: if the category does not
        exist
    """
    category = group_categories.GroupCategory.query.filter_by(id=category_id).first()
    if category is None:
        raise errors.GroupCategoryDoesNotExistError()
    return GroupCategory.from_database(category)


def get_group_categories() -> typing.Sequence[GroupCategory]:
    """
    Get all group categories.

    :return: the list of all group categories
    """
    categories = group_categories.GroupCategory.query.order_by(group_categories.GroupCategory.id).all()
    return tuple(
        GroupCategory.from_database(category)
        for category in categories
    )


class GroupCategoryTree(typing.TypedDict):
    basic_group_ids: typing.Set[int]
    project_group_ids: typing.Set[int]
    child_categories: typing.Dict[int, 'GroupCategoryTree']
    contains_basic_groups: bool
    contains_project_groups: bool


def get_group_category_tree(
        basic_group_ids: typing.Optional[typing.Set[int]] = None,
        project_group_ids: typing.Optional[typing.Set[int]] = None
) -> GroupCategoryTree:
    """
    Get the group category tree containing all categories, basic and project groups.

    :return: the group category tree
    """
    categories = get_group_categories()
    basic_groups = groups.Group.query.all()
    project_groups = projects.Project.query.all()
    if basic_group_ids is not None:
        basic_groups = [
            group
            for group in basic_groups
            if group.id in basic_group_ids
        ]
    if project_group_ids is not None:
        project_groups = [
            group
            for group in project_groups
            if group.id in project_group_ids
        ]

    def _build_sub_tree(
            category_id: int,
            categories: typing.Sequence[GroupCategory],
            basic_groups: typing.Sequence[groups.Group],
            project_groups: typing.Sequence[projects.Project]
    ) -> GroupCategoryTree:
        category_tree = GroupCategoryTree(
            basic_group_ids={
                group.id
                for group in basic_groups
                if any(category.id == category_id for category in group.categories)
            },
            project_group_ids={
                group.id
                for group in project_groups
                if any(category.id == category_id for category in group.categories)
            },
            child_categories={
                category.id: _build_sub_tree(category.id, categories, basic_groups, project_groups)
                for category in categories
                if category.parent_category_id == category_id
            },
            contains_basic_groups=False,
            contains_project_groups=False
        )
        category_tree['contains_basic_groups'] = bool(category_tree['basic_group_ids']) or any(
            sub_tree['contains_basic_groups']
            for sub_tree in category_tree['child_categories'].values()
        )
        category_tree['contains_project_groups'] = bool(category_tree['project_group_ids']) or any(
            sub_tree['contains_project_groups']
            for sub_tree in category_tree['child_categories'].values()
        )
        return category_tree

    category_tree = GroupCategoryTree(
        basic_group_ids={
            group.id
            for group in basic_groups
            if not group.categories
        },
        project_group_ids={
            group.id
            for group in project_groups
            if not group.categories
        },
        child_categories={
            category.id: _build_sub_tree(category.id, categories, basic_groups, project_groups)
            for category in categories
            if category.parent_category_id is None
        },
        contains_basic_groups=False,
        contains_project_groups=False
    )
    category_tree['contains_basic_groups'] = bool(category_tree['basic_group_ids']) or any(
        sub_tree['contains_basic_groups']
        for sub_tree in category_tree['child_categories'].values()
    )
    category_tree['contains_project_groups'] = bool(category_tree['project_group_ids']) or any(
        sub_tree['contains_project_groups']
        for sub_tree in category_tree['child_categories'].values()
    )
    return category_tree


def get_full_group_category_names() -> typing.Dict[int, typing.Sequence[typing.Dict[str, str]]]:
    """
    Get the full sequence of ancestor names for all categories.

    :return: a dict containing the names for each category ID
    """
    categories = group_categories.GroupCategory.query.order_by(group_categories.GroupCategory.id).all()
    category_names = {}
    any_missing = True
    while any_missing:
        any_missing = False
        for category in categories:
            if category.id not in category_names:
                if category.parent_category_id is None:
                    category_names[category.id] = [category.name]
                elif category.parent_category_id in category_names:
                    category_names[category.id] = category_names[category.parent_category_id] + [category.name]
                else:
                    any_missing = True
    return {
        category_id: tuple(individual_category_names)
        for category_id, individual_category_names in category_names.items()
    }


def get_full_group_category_name(
        category_id: int
) -> typing.Sequence[typing.Dict[str, str]]:
    """
    Get the full sequence of ancestor names for a category.

    :param category_id: the ID of an existing category
    :return: the names for the category
    :raise errors.GroupCategoryDoesNotExist: if no group category with the given ID exists
    """
    category = get_group_category(category_id=category_id)
    if category.parent_category_id is None:
        return [category.name]
    return list(get_full_group_category_name(category_id=category.parent_category_id)) + [category.name]


def get_basic_group_categories(
        basic_group_id: int
) -> typing.Sequence[GroupCategory]:
    """
    Get the group categories for a basic group.

    :param basic_group_id: the ID of an existing basic group
    :return: the list of group categories
    :raise errors.GroupDoesNotExistError: if then basic group does not exist
    """
    basic_group = groups.Group.query.filter_by(id=basic_group_id).first()
    if basic_group is None:
        raise errors.GroupDoesNotExistError()
    return tuple(
        GroupCategory.from_database(category)
        for category in basic_group.categories
    )


def get_project_group_categories(
        project_group_id: int
) -> typing.Sequence[GroupCategory]:
    """
    Get the group categories for a project group.

    :param project_group_id: the ID of an existing project group
    :return: the list of group categories
    :raise errors.ProjectDoesNotExistError: if then project group does not
        exist
    """
    project_group = projects.Project.query.filter_by(id=project_group_id).first()
    if project_group is None:
        raise errors.ProjectDoesNotExistError()
    return tuple(
        GroupCategory.from_database(category)
        for category in project_group.categories
    )
