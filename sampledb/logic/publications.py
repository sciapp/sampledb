# coding: utf-8
"""

"""

import collections
import dataclasses
import typing

from .. import db
from .. import models
from . import errors
from . import object_log
from . import user_log
from . import object_permissions
from .objects import check_object_exists
from .users import check_user_exists


@dataclasses.dataclass(frozen=True)
class Publication:
    """
    This class provides an immutable wrapper around models.object_publications.ObjectPublication.
    """
    doi: str
    title: typing.Optional[str]
    object_name: typing.Optional[str]

    @classmethod
    def from_database(cls, publication: models.object_publications.ObjectPublication) -> 'Publication':
        return Publication(
            doi=publication.doi,
            title=publication.title,
            object_name=publication.object_name
        )


def link_publication_to_object(
        user_id: int,
        object_id: int,
        doi: str,
        title: typing.Optional[str] = None,
        object_name: typing.Optional[str] = None
) -> None:
    """
    Link a publication to an object.

    :param user_id: the ID of an existing user
    :param object_id: the ID of an existing object
    :param doi: the DOI of an existing publication
    :param title: the title of the publication
    :param object_name: the name of the object in the publication
    :raise errors.ObjectDoesNotExistError: when no object with the given object
        ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    check_user_exists(user_id)
    check_object_exists(object_id)
    link = models.object_publications.ObjectPublication.query.filter_by(object_id=object_id, doi=doi).first()
    if link is None:
        link = models.object_publications.ObjectPublication(object_id=object_id, doi=doi)
    link.title = title
    link.object_name = object_name
    db.session.add(link)
    db.session.commit()
    user_log.link_publication(user_id=user_id, object_id=object_id, doi=doi, title=title, object_name=object_name)
    object_log.link_publication(user_id=user_id, object_id=object_id, doi=doi, title=title, object_name=object_name)


def get_publications_for_object(object_id: int) -> typing.Sequence[Publication]:
    """
    Get a list of publications linked to an object with a given ID.

    :param object_id: the ID of an existing object
    :return: a list of publications linked to the given object
    :raise errors.ObjectDoesNotExistError: when no object with the given object ID
        exists
    """
    check_object_exists(object_id)
    links = models.object_publications.ObjectPublication.query.filter_by(object_id=object_id).all()
    return [
        Publication.from_database(link)
        for link in links
    ]


def get_object_ids_linked_to_doi(doi: str) -> typing.Sequence[int]:
    """
    Get a list of object IDs linked to a publication.

    :param doi: the DOI of the publication
    :return: the list of object IDs
    :raise errors.InvalidDOIError: when the DOI is invalid
    """
    doi = simplify_doi(doi)
    links = models.object_publications.ObjectPublication.query.filter_by(doi=doi).all()
    return [
        link.object_id
        for link in links
    ]


def simplify_doi(doi: str) -> str:
    """
    Simplify a digital object identifier (DOI).

    :param doi: the DOI to simplify
    :return: the simplified DOI
    :raise errors.InvalidDOIError: when the DOI is invalid
    """
    doi = doi.lower()
    doi_prefixes = [
        'doi:',
        'https://doi.org/'
    ]
    for doi_prefix in doi_prefixes:
        if doi.startswith(doi_prefix):
            doi = doi[len(doi_prefix):]
            break
    # DOI organizer part must start with '10.'
    if not doi.startswith('10.'):
        raise errors.InvalidDOIError()
    # DOI must be split into organizer and object parts by a slash
    if '/' not in doi[4:-1]:
        raise errors.InvalidDOIError()
    organizer_id, object_id = doi[3:].split('/', 1)
    if any(c not in '0123456789.' for c in organizer_id):
        raise errors.InvalidDOIError()
    if any(c in '<>"' for c in object_id):
        raise errors.InvalidDOIError()
    return doi


def get_publications_for_user(user_id: int) -> typing.List[typing.Tuple[str, typing.Optional[str]]]:
    """
    Get a list of DOIs and titles for publications linked to objects readable by the given user.

    If multiple titles are used for the same DOI, the most used, non-empty
    title will be used, with lexicographical sorting as final criteria.

    :param user_id: the ID of an existing user
    :return: a list containing publication DOIs and titles
    """
    table, parameters = object_permissions.get_object_table_with_permissions(
        user_id=user_id,
        permissions=models.Permissions.READ,
        name_only=True
    )
    if table is None:
        return []
    publication_links = [
        row[0] for row in db.session.execute(
            db.select(models.ObjectPublication).select_from(
                table.join(
                    models.ObjectPublication,
                    table.c.object_id == models.ObjectPublication.object_id
                )
            ), parameters
        ).fetchall()
    ]
    publication_titles: typing.Dict[str, typing.List[str]] = {}
    for link in publication_links:
        if link.doi not in publication_titles:
            publication_titles[link.doi] = []
        if link.title:
            publication_titles[link.doi].append(link.title)
    publications = []
    for doi, titles in publication_titles.items():
        title: typing.Optional[str]
        if titles:
            # sort titles lexicographically, then find most commonly used title
            titles.sort()
            title = collections.Counter(titles).most_common(1)[0][0]
        else:
            title = None
        publications.append((doi, title))
    publications.sort()
    return publications
