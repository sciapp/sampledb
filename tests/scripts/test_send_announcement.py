# coding: utf-8
"""

"""

import pytest
import sampledb
import sampledb.models
from sampledb.logic.notifications import get_notifications, NotificationType
import sampledb.__main__ as scripts


@pytest.fixture
def user():
    user = sampledb.models.User(
        name="User",
        email="example1@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert user.id is not None
    sampledb.db.session.expunge(user)
    return user


def test_send_announcement(user, capsys):
    scripts.main([scripts.__file__, 'send_announcement', __file__, __file__])
    notification = get_notifications(user.id, unread_only=True)[0]
    assert notification.type == NotificationType.ANNOUNCEMENT
    assert 'test_send_announcement' in notification.data['message']


def test_send_announcement_arguments(user, capsys):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'send_announcement', __file__])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
