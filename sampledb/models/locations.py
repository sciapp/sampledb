# coding: utf-8
"""

"""

import datetime
import typing

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, Mapped, Query

from .. import db
from .objects import Objects
from .users import User
from .actions import ActionType
from .utils import Model

if typing.TYPE_CHECKING:
    from .components import Component
    from .topics import Topic


location_user_association_table = db.Table(
    'location_responsible_users',
    db.metadata,
    db.Column('location_id', db.Integer, db.ForeignKey('locations.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
)

topic_location_association_table = db.Table(
    'location_topics',
    db.metadata,
    db.Column('location_id', db.Integer, db.ForeignKey('locations.id')),
    db.Column('topic_id', db.Integer, db.ForeignKey('topics.id'))
)


class LocationType(Model):
    __tablename__ = 'location_types'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (name is NOT NULL)',
            name='location_types_not_null_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='location_types_fed_id_component_id_key'),
    )

    # default location type IDs
    # offset to -100 to allow later addition of new default location types
    # see: migrations/location_types_create_default_location_types.py
    LOCATION: int = -100 + 1

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[typing.Optional[typing.Dict[str, str]]] = db.Column(postgresql.JSON, nullable=True)
    location_name_singular: Mapped[typing.Optional[typing.Dict[str, str]]] = db.Column(postgresql.JSON, nullable=True)
    location_name_plural: Mapped[typing.Optional[typing.Dict[str, str]]] = db.Column(postgresql.JSON, nullable=True)
    admin_only: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    enable_parent_location: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    enable_sub_locations: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    enable_object_assignments: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    enable_responsible_users: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    enable_instruments: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    show_location_log: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    fed_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True)
    component_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component: Mapped[typing.Optional['Component']] = relationship('Component')
    enable_capacities: Mapped[bool] = db.Column(db.Boolean, nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["LocationType"]]

    def __init__(
            self,
            name: typing.Optional[typing.Dict[str, str]],
            location_name_singular: typing.Optional[typing.Dict[str, str]],
            location_name_plural: typing.Optional[typing.Dict[str, str]],
            admin_only: bool,
            enable_parent_location: bool,
            enable_sub_locations: bool,
            enable_object_assignments: bool,
            enable_responsible_users: bool,
            enable_instruments: bool,
            enable_capacities: bool,
            show_location_log: bool,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None
    ) -> None:
        super().__init__(
            name=name,
            location_name_singular=location_name_singular,
            location_name_plural=location_name_plural,
            admin_only=admin_only,
            enable_parent_location=enable_parent_location,
            enable_sub_locations=enable_sub_locations,
            enable_object_assignments=enable_object_assignments,
            enable_responsible_users=enable_responsible_users,
            enable_instruments=enable_instruments,
            show_location_log=show_location_log,
            fed_id=fed_id,
            component_id=component_id,
            enable_capacities=enable_capacities
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, name="{self.name}")>'


class Location(Model):
    __tablename__ = 'locations'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (name is NOT NULL AND description IS NOT NULL)',
            name='locations_not_null_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='locations_fed_id_component_id_key'),
    )

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[typing.Optional[typing.Dict[str, str]]] = db.Column(postgresql.JSON, nullable=True)
    description: Mapped[typing.Optional[typing.Dict[str, str]]] = db.Column(postgresql.JSON, nullable=True)
    parent_location_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    fed_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True)
    component_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component: Mapped[typing.Optional['Component']] = relationship('Component')
    type_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('location_types.id'), nullable=False)
    type: Mapped[LocationType] = relationship('LocationType')
    responsible_users: Mapped[typing.List['User']] = relationship("User", secondary=location_user_association_table, order_by="User.name")
    is_hidden: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)
    enable_object_assignments: Mapped[bool] = db.Column(db.Boolean, default=True, server_default=db.true(), nullable=False)
    topics: Mapped[typing.List['Topic']] = relationship('Topic', secondary=topic_location_association_table, back_populates='locations')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Location"]]

    def __init__(
            self,
            name: typing.Optional[typing.Dict[str, str]],
            description: typing.Optional[typing.Dict[str, str]],
            parent_location_id: typing.Optional[int] = None,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None,
            *,
            type_id: int
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            parent_location_id=parent_location_id,
            fed_id=fed_id,
            component_id=component_id,
            type_id=type_id
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, name="{self.name}", description="{self.description}", parent_location_id={self.parent_location_id})>'


class ObjectLocationAssignment(Model):
    __tablename__ = 'object_location_assignments'
    __table_args__ = (
        db.CheckConstraint(
            '(fed_id IS NOT NULL AND component_id IS NOT NULL) OR (description IS NOT NULL AND user_id IS NOT NULL AND utc_datetime IS NOT NULL)',
            name='object_location_assignments_not_null_check'
        ),
        db.CheckConstraint(
            'NOT (confirmed AND declined)',
            name='object_location_assignments_not_both_states_check'
        ),
        db.UniqueConstraint('fed_id', 'component_id', name='object_location_assignments_fed_id_component_id_key'),
    )

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    object_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    location_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=True)
    responsible_user_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    user_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey(User.id), nullable=True)
    description: Mapped[typing.Optional[typing.Dict[str, str]]] = db.Column(postgresql.JSON, nullable=True)
    utc_datetime: Mapped[typing.Optional[datetime.datetime]] = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    confirmed: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    location: Mapped[typing.Optional['Location']] = relationship('Location')
    fed_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True)
    component_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component: Mapped[typing.Optional['Component']] = relationship('Component')
    declined: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ObjectLocationAssignment"]]

    def __init__(
            self,
            object_id: int,
            location_id: typing.Optional[int],
            user_id: typing.Optional[int],
            description: typing.Optional[typing.Dict[str, str]],
            utc_datetime: typing.Optional[datetime.datetime] = None,
            responsible_user_id: typing.Optional[int] = None,
            confirmed: bool = False,
            declined: bool = False,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None
    ) -> None:
        super().__init__(
            object_id=object_id,
            location_id=location_id,
            responsible_user_id=responsible_user_id,
            user_id=user_id,
            description=description,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc),
            confirmed=confirmed,
            fed_id=fed_id,
            component_id=component_id,
            declined=declined
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, object_id={self.object_id}, location_id={self.location_id}, user_id={self.user_id}, responsible_user_id={self.responsible_user_id}, utc_datetime={self.utc_datetime}, description="{self.description}", confirmed={self.confirmed}, declined={self.declined})>'


class LocationCapacity(Model):
    __tablename__ = 'location_capacities'

    location_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Location.id), primary_key=True)
    action_type_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(ActionType.id), primary_key=True)
    capacity: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["LocationCapacity"]]
