import collections
import dataclasses
import datetime
import typing

import flask

from .. import db, models
from . import errors, users


@dataclasses.dataclass(frozen=True)
class InfoPage:
    """
    This class provides an immutable wrapper around models.info_pages.InfoPage.
    """
    id: int
    title: typing.Dict[str, str]
    content: typing.Dict[str, str]
    endpoint: typing.Optional[str]
    disabled: bool

    @classmethod
    def from_database(cls, info_page: models.InfoPage) -> 'InfoPage':
        return cls(
            id=info_page.id,
            title=info_page.title,
            content=info_page.content,
            endpoint=info_page.endpoint,
            disabled=info_page.disabled,
        )


def get_info_pages() -> typing.Sequence[InfoPage]:
    """
    Get all info pages.

    :return: the list of all info pages
    """
    return [
        InfoPage.from_database(info_page)
        for info_page in models.InfoPage.query.order_by(models.InfoPage.id).all()
    ]


def get_info_page(info_page_id: int) -> InfoPage:
    """
    Get an info page with a given info page ID.

    :param info_page_id: the info page ID
    :return: the info page
    :raise errors.InfoPageDoesNotExistError: if no info page with the given ID
        exists
    """
    info_page = models.InfoPage.query.filter_by(id=info_page_id).first()
    if info_page is None:
        raise errors.InfoPageDoesNotExistError()
    return InfoPage.from_database(info_page)


def get_info_pages_for_endpoint(
        endpoint: typing.Optional[str],
        user_id: typing.Optional[int],
        exclude_disabled: bool = True
) -> typing.Sequence[InfoPage]:
    """
    Get all unacknowledged info pages for an endpoint.

    :param endpoint: the endpoint to get info pages for
    :param user_id: the user id to get info pages for
    :param exclude_disabled: whether to exclude disabled info pages
    :return: a list of info pages
    """
    info_page_query = models.info_pages.InfoPage.query.filter(
        db.or_(
            models.InfoPage.endpoint == endpoint,
            models.InfoPage.endpoint == db.null(),
        )
    )
    if exclude_disabled:
        info_page_query = info_page_query.filter(models.InfoPage.disabled == db.false())
    if user_id is not None:
        info_page_query = info_page_query.where(db.not_(models.InfoPageAcknowledgement.query.filter(
            db.and_(
                models.InfoPageAcknowledgement.info_page_id == models.info_pages.InfoPage.id,
                models.InfoPageAcknowledgement.user_id == user_id,
            )
        ).exists()))
    return [
        InfoPage.from_database(info_page)
        for info_page in info_page_query.all()
    ]


def acknowledge_info_pages(
        info_page_ids: typing.Set[int],
        user_id: int,
) -> None:
    """
    Create acknowledgements for a user for a set of info pages.

    :param info_page_ids: a set of info page IDs to create acknowledgements for
    :param user_id: the user to create the acknowledgements for
    :raise errors.InfoPageDoesNotExistError: if no info page with one of the
        given IDs exists
    :raise errors.UserDoesNotExistError: if no user with the given ID exists
    """
    users.check_user_exists(user_id)
    existing_acknowledgements = {
        acknowledgement.info_page_id: acknowledgement
        for acknowledgement in models.InfoPageAcknowledgement.query.filter(
            db.and_(
                models.InfoPageAcknowledgement.user_id == user_id,
                models.InfoPageAcknowledgement.info_page_id.in_(info_page_ids),
            )
        ).all()
    }
    utc_datetime = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None)
    all_info_pages = get_info_pages()
    all_info_page_ids = {info_page.id for info_page in all_info_pages}
    for info_page_id in info_page_ids:
        if info_page_id not in all_info_page_ids:
            raise errors.InfoPageDoesNotExistError()
        if info_page_id not in existing_acknowledgements:
            db.session.add(models.InfoPageAcknowledgement(
                info_page_id=info_page_id,
                user_id=user_id,
                utc_datetime=utc_datetime
            ))
        elif existing_acknowledgements[info_page_id].utc_datetime is None:
            existing_acknowledgements[info_page_id].utc_datetime = utc_datetime
            db.session.add(existing_acknowledgements[info_page_id])
    db.session.commit()


def acknowledge_info_page_for_existing_users(
        info_page_id: int
) -> None:
    """
    Create pseudo-acknowledgements for all existing users for an info page.

    :param info_page_id: the ID of the info page to create
        pseudo-acknowledgements for
    :raise errors.InfoPageDoesNotExistError: if no info page with the given
        info page ID exists
    """
    info_page = models.InfoPage.query.filter_by(id=info_page_id).first()
    if info_page is None:
        raise errors.InfoPageDoesNotExistError()
    existing_acknowledgements = {
        acknowledgement.user_id
        for acknowledgement in models.InfoPageAcknowledgement.query.filter_by(info_page_id=info_page_id).all()
    }
    users = models.User.query.all()
    for user in users:
        if user.id in existing_acknowledgements:
            continue
        db.session.add(models.InfoPageAcknowledgement(
            info_page_id=info_page_id,
            user_id=user.id,
            utc_datetime=None
        ))
    db.session.commit()


def clear_acknowledgements_for_info_page(
        info_page_id: int
) -> None:
    """
    Clear all (real) user acknowledgements for an info page.

    This will not clear pseudo-acknowledgements that were created for
    existing users when the info page was created.

    :param info_page_id: the ID of the info page to clean acknowledgements for
    :raise errors.InfoPageDoesNotExistError: if no info page with the given
        info page ID exists
    """
    acknowledgements = models.InfoPageAcknowledgement.query.filter(
        db.and_(
            models.InfoPageAcknowledgement.info_page_id == info_page_id,
            models.InfoPageAcknowledgement.utc_datetime != db.null(),
        )
    ).all()
    if acknowledgements:
        for acknowledgement in acknowledgements:
            db.session.delete(acknowledgement)
        db.session.commit()
    else:
        info_page = models.InfoPage.query.filter_by(id=info_page_id).first()
        if info_page is None:
            raise errors.InfoPageDoesNotExistError()


def get_acknowledgements_for_info_page(
        info_page_id: int
) -> typing.Dict[int, typing.Optional[datetime.datetime]]:
    """
    Get user acknowledgements for an info page ID.

    :param info_page_id: the ID of the info page to get acknowledgements for
    :return: a dict mapping user IDs to their acknowledgements for the info page
    :raise errors.InfoPageDoesNotExistError: if no info page with the given
        info page ID exists
    """
    acknowledgements = models.InfoPageAcknowledgement.query.filter_by(info_page_id=info_page_id).all()
    if not acknowledgements:
        info_page = models.InfoPage.query.filter_by(id=info_page_id).first()
        if info_page is None:
            raise errors.InfoPageDoesNotExistError()
        return {}
    return {
        acknowledgement.user_id: acknowledgement.utc_datetime
        for acknowledgement in acknowledgements
    }


def create_info_page(
        title: typing.Dict[str, str],
        content: typing.Dict[str, str],
        endpoint: typing.Optional[str],
        disabled: bool = False,
) -> InfoPage:
    """
    Create a new info page.

    :param title: the title for the info page
    :param content: the content for the info page
    :param endpoint: the endpoint for the info page
    :param disabled: whether the info page should be disabled
    :return: the created info page
    """
    info_page = models.InfoPage(
        title=title,
        content=content,
        endpoint=endpoint,
        disabled=disabled,
    )
    db.session.add(info_page)
    db.session.commit()
    return InfoPage.from_database(info_page)


def set_info_page_disabled(
        info_page_id: int,
        disabled: bool = True
) -> None:
    """
    Disable or enable an info page.

    :param info_page_id: the ID of the info page to disable or enable
    :param disabled: whether the info page should be disabled
    :raise errors.InfoPageDoesNotExistError: if no info page with the given
        info page ID exists
    """
    info_page = models.InfoPage.query.filter_by(id=info_page_id).first()
    if info_page is None:
        raise errors.InfoPageDoesNotExistError()
    info_page.disabled = disabled
    db.session.add(info_page)
    db.session.commit()


def update_info_page(
        info_page_id: int,
        title: typing.Dict[str, str],
        content: typing.Dict[str, str],
        endpoint: typing.Optional[str],
) -> InfoPage:
    """
    Update an info page.

    :param info_page_id: the ID of the info page to update
    :param title: the new title for the info page
    :param content: the new content for the info page
    :param endpoint: the new endpoint for the info page
    :return: the updated info page
    :raise errors.InfoPageDoesNotExistError: if no info page with the given
        info page ID exists
    """
    info_page = models.InfoPage.query.filter_by(id=info_page_id).first()
    if info_page is None:
        raise errors.InfoPageDoesNotExistError()
    info_page.title = title
    info_page.content = content
    info_page.endpoint = endpoint
    db.session.add(info_page)
    db.session.commit()
    return InfoPage.from_database(info_page)


def delete_info_page(
        info_page_id: int
) -> None:
    """
    Delete an info page.

    :param info_page_id: the ID of the info page to delete
    :raise errors.InfoPageDoesNotExistError: if no info page with the given
        info page ID exists
    """
    info_page = models.InfoPage.query.filter_by(id=info_page_id).first()
    if info_page is None:
        raise errors.InfoPageDoesNotExistError()
    db.session.delete(info_page)
    db.session.commit()


def get_url_rules_by_endpoint() -> typing.Dict[str, typing.List[str]]:
    """
    Get the list of URL rules that are reasonable for info pages.

    :return: the list of rules

    While info pages can be created for any endpoint, info pages will not
    work with many endpoints, e.g. because they cannot be accessed with GET or
    because they will not use the base template that displays info pages. This
    function tries to filter out these endpoints that would not be useful for
    displaying an info page.
    """
    url_rules_by_endpoint = collections.defaultdict(list)
    for url_rule in flask.current_app.url_map.iter_rules():
        # info pages can only be shown via GET
        if url_rule.methods and 'GET' not in url_rule.methods:
            continue
        # info pages only work in the frontend
        if not url_rule.endpoint.startswith('frontend.'):
            continue
        # info pages do not work during sign in
        if url_rule.rule.startswith('/users/me/sign_in'):
            continue
        if url_rule.rule.startswith('/users/me/two_factor_authentication/'):
            continue
        if url_rule.rule.startswith('/federated-login/'):
            continue
        if url_rule.rule.startswith('/users/me/oidc'):
            continue
        if url_rule.rule.startswith('/other-databases/') and 'identity' in url_rule.rule:
            continue
        # info pages do not work for files
        if '.' in url_rule.rule:
            continue
        if '/file_attachments/' in url_rule.rule:
            continue
        if url_rule.rule.startswith('/markdown_images/'):
            continue
        if url_rule.rule.startswith('/objects/') and (url_rule.rule.endswith('/export') or url_rule.rule.endswith('/label')):
            continue
        if url_rule.rule == '/multiselect_labels':
            continue
        # info pages do not work on routes that are simple redirects
        if url_rule.rule.endswith('/activity'):
            continue
        if url_rule.rule.startswith('/locations/') and url_rule.rule.endswith('_responsibility'):
            continue
        if '/redirect-uuid/' in url_rule.rule:
            continue
        if url_rule.rule == '/users/me':
            continue
        # info pages do not work on routes that do not use base.html
        if '/mobile_upload/' in url_rule.rule:
            continue
        if url_rule.rule in {'/objects/referencable', '/status/', '/users/me/shared_device_state'}:
            continue
        url_rules_by_endpoint[url_rule.endpoint].append(url_rule.rule)
    return url_rules_by_endpoint
