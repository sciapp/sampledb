import typing

import itsdangerous

MAX_AGE = 60 * 60 * 24 * 2


def generate_token(
        data: typing.Any,
        salt: str,
        secret_key: str
) -> str:
    serializer = itsdangerous.URLSafeTimedSerializer(secret_key)
    return serializer.dumps(data, salt=salt)


def verify_token(
        token: str,
        salt: str,
        secret_key: str,
        expiration: typing.Optional[int] = MAX_AGE
) -> typing.Optional[typing.Any]:
    serializer = itsdangerous.URLSafeTimedSerializer(secret_key)
    try:
        return serializer.loads(
            token,
            salt=salt,
            max_age=expiration
        )
    except itsdangerous.BadData:
        return None
