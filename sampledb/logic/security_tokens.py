import itsdangerous

MAX_AGE = 60 * 60 * 24 * 2


def generate_token(data, salt, secret_key):
    serializer = itsdangerous.URLSafeTimedSerializer(secret_key)
    return serializer.dumps(data, salt=salt)


def verify_token(token, salt, secret_key, expiration=MAX_AGE):
    serializer = itsdangerous.URLSafeTimedSerializer(secret_key)
    try:
        return serializer.loads(
            token,
            salt=salt,
            max_age=expiration
        )
    except itsdangerous.BadData:
        return None
