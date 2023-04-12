import typing

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, Query, relationship

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .groups import Group
    from .projects import Project

basic_group_category_association_table = db.Table(
    "basic_group_category_association_table",
    db.metadata,
    db.Column("group_category_id", db.ForeignKey("group_categories.id", ondelete="CASCADE")),
    db.Column("basic_group_id", db.ForeignKey("groups.id", ondelete="CASCADE")),
)

project_group_category_association_table = db.Table(
    "project_group_category_association_table",
    db.metadata,
    db.Column("group_category_id", db.ForeignKey("group_categories.id", ondelete="CASCADE")),
    db.Column("project_group_id", db.ForeignKey("projects.id", ondelete="CASCADE")),
)


class GroupCategory(Model):
    __tablename__ = 'group_categories'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[typing.Dict[str, str]] = db.Column(postgresql.JSON, nullable=False)
    parent_category_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('group_categories.id', ondelete="CASCADE"), nullable=True)
    basic_groups: Mapped[typing.List['Group']] = relationship("Group", secondary=basic_group_category_association_table, back_populates="categories")
    project_groups: Mapped[typing.List['Project']] = relationship("Project", secondary=project_group_category_association_table, back_populates="categories")

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["GroupCategory"]]
