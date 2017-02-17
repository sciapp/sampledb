from demo import mail
from flask_mail import Mail, Message


def send_mail(to,subject,template):
    print("send_mail")
    msg = Message(
        subject,
        sender='iffsamples@fz-juelich.de',
        recipients=['d.henkel@fz-juelich.de'],
        html=template
    )
    mail.send(msg)
    return "sent"
