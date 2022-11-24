
import smtplib
import typing

import flask
import flask_mail

from ... import mail
from . import core
from ...models import BackgroundTask, BackgroundTaskStatus


def post_send_mail_task(
        subject: str,
        recipients: typing.List[str],
        text: str,
        html: str,
        auto_delete: bool = True
) -> typing.Tuple[BackgroundTaskStatus, typing.Optional[BackgroundTask]]:
    return core.post_background_task(
        type='send_mail',
        data={
            'subject': subject,
            'recipients': recipients,
            'text': text,
            'html': html
        },
        auto_delete=auto_delete
    )


def handle_send_mail_task(
        data: typing.Dict[str, typing.Any],
        task_id: typing.Optional[int]
) -> typing.Tuple[bool, typing.Optional[dict[str, typing.Any]]]:
    try:
        mail.send(flask_mail.Message(
            subject=data['subject'],
            sender=flask.current_app.config['MAIL_SENDER'],
            recipients=data['recipients'],
            body=data['text'],
            html=data['html']
        ))
        return True, None
    except smtplib.SMTPRecipientsRefused:
        return False, None
