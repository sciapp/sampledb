# coding: utf-8
"""

"""
import re
import typing
from flask_babel import _

from .. import db


class Component(db.Model):
    __tablename__ = 'components'

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.Text, nullable=True)
    uuid = db.Column(db.Text, nullable=False, unique=True)
    name = db.Column(db.Text, nullable=True, unique=True)
    description = db.Column(db.Text, nullable=False, default='')

    def __init__(self, uuid: str, name: typing.Optional[str] = None, description: typing.Optional[str] = '', address: typing.Optional[str] = None):
        self.address = address
        self.uuid = uuid
        self.name = name
        self.description = description

    def __repr__(self):
        return '<{0}(id={1.id}, address={1.address}, uuid={1.uuid}, name={1.name}, description={1.description})>'.format(type(self).__name__, self)

    def get_name(self):
        if self.name is None:
            if self.address is not None:
                regex = re.compile(r"^https?://(www\.)?")    # should usually be https
                return regex.sub('', self.address).strip().strip('/')
            return _('Database #%(id)s', id=self.id)
        else:
            return self.name
