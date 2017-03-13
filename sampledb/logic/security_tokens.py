import itsdangerous


def generate_token(data, salt, secret_key):
    serializer = itsdangerous.URLSafeTimedSerializer(secret_key)
    return serializer.dumps(data, salt=salt)


def verify_token(token, salt, secret_key, expiration=36000):
    serializer = itsdangerous.URLSafeTimedSerializer(secret_key)
    try:
        return serializer.loads(
            token,
            salt=salt,
            max_age=expiration
        )
    except itsdangerous.BadData:
        return None
