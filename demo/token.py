from itsdangerous import BadData, URLSafeTimedSerializer
from itsdangerous import BadTimeSignature, TimedSerializer, SignatureExpired
from demo import demo
from flask import abort,flash

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(demo.config['SECRET_KEY'])
    return serializer.dumps(email, salt=demo.config['SECURITY_PASSWORD_SALT'])

def confirm_token(token, expiration=36000):
    serializer = URLSafeTimedSerializer(demo.config['SECRET_KEY'])

    email = serializer.loads (
            token,
            salt = demo.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration,
            return_timestamp=True
        )
    return email

