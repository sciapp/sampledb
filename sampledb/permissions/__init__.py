# coding: utf-8
"""
Object Permissions

There are three types of permissions for each object:
 - READ, being able to access all information on an object,
 - WRITE, being able to update an object, and
 - GRANT, being able to grant permissions to other users.

When an object is created, its creator initially gets GRANT permissions for the object. In addition, if the object
was created performing an instrument action, the instrument responsible users will have GRANT access rights, not as
individuals, but in their role of responsible users. So even when a user becomes responsible user AFTER an object was
created using an instrument, this user will then have GRANT rights, until he is removed from the list of responsible
users for the instrument.

Objects can be made public, which grants READ permissions to anyone trying to access the object. While this can be
reverted, users should consider that anything that was public for any amount of time, might have been copied, cached or
simply linked to, so public objects should ideally stay public.
"""

from .views import permissions_api

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'
