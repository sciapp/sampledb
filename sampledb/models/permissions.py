# coding: utf-8
"""

"""

import enum

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

import typing


class Permissions(enum.Enum):
    NONE = 0
    READ = 1
    WRITE = 2  # includes READ
    GRANT = 3  # includes READ and WRITE

    def __contains__(self, item: 'Permissions') -> bool:
        return self.value >= item.value

    def __str__(self) -> str:
        return self.name.lower()

    def __le__(self, other: 'Permissions') -> bool:
        if isinstance(other, Permissions):
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other: 'Permissions') -> bool:
        if isinstance(other, Permissions):
            return self.value < other.value
        return NotImplemented

    @staticmethod
    def from_name(
            name: str
    ) -> 'Permissions':
        members = {
            'none': Permissions.NONE,
            'read': Permissions.READ,
            'write': Permissions.WRITE,
            'grant': Permissions.GRANT,
        }
        try:
            return members[name.lower()]
        except KeyError:
            raise ValueError('Invalid name')

    @staticmethod
    def from_value(
            value: typing.Optional[int]
    ) -> 'Permissions':
        if value is None:
            return Permissions.NONE
        for member in Permissions:
            if member.value == value:
                return member
        return Permissions.NONE
