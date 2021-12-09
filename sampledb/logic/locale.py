import flask

from . import languages

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
    allowed_language_codes = get_allowed_language_codes()
    try:
        best_match_locale = flask.request.accept_languages.best_match(allowed_language_codes)
    except Exception:
        return DEFAULT_LOCALE
    if best_match_locale in SUPPORTED_LOCALES:
        return best_match_locale
    else:
        return DEFAULT_LOCALE


def get_allowed_language_codes():
    supported_language_codes = list(SUPPORTED_LOCALES.keys())
    language_codes_allowed = {
        language.lang_code: language.enabled_for_user_interface
        for language in languages.get_languages()
    }
    return [
        lang_code
        for lang_code in supported_language_codes
        if language_codes_allowed.get(lang_code, False)
    ]
