from .. import db
import sqlalchemy.dialects.postgresql as postgresql


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


class GroupCategory(db.Model):  # type: ignore
    __tablename__ = 'group_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(postgresql.JSON, nullable=False)
    parent_category_id = db.Column(db.Integer, db.ForeignKey('group_categories.id', ondelete="CASCADE"), nullable=True)
    basic_groups = db.relationship("Group", secondary=basic_group_category_association_table, backref="categories")
    project_groups = db.relationship("Project", secondary=project_group_category_association_table, backref="categories")
