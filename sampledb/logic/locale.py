import flask

SUPPORTED_LOCALES = {
    'de': {"english_name": "German", "native_name": "Deutsch"},
    'en': {"english_name": "English", "native_name": "English"}
}

DEFAULT_LOCALE = 'en'


def guess_request_locale() -> str:
    """
    Guess the best locale for a flask request.

    If no match is found, the default locale (English) is returned.

    :return: the locale language code
    """
    try:
        best_match_locale = flask.request.accept_languages.best_match(SUPPORTED_LOCALES.keys())
    except Exception:
        return DEFAULT_LOCALE
    if best_match_locale in SUPPORTED_LOCALES:
        return best_match_locale
    else:
        return DEFAULT_LOCALE
