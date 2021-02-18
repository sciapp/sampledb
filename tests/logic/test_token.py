import sampledb
import sampledb.models


def test_generate_token(app):

    erg = sampledb.logic.security_tokens.generate_token(['example@example.com'],'invitation',app.config['SECRET_KEY'])

    result = sampledb.logic.security_tokens.verify_token(erg,'add_login',app.config['SECRET_KEY'])
    # token is wrong
    assert result is not 'example@example.com'

    erg = sampledb.logic.security_tokens.generate_token(['example@example.com'], 'invitation',
                                                        app.config['SECRET_KEY'])

    result = sampledb.logic.security_tokens.verify_token(erg, 'invitation', app.config['SECRET_KEY'])
    # token is correct
    assert result[0] is not 'example@example.com'


    erg = sampledb.logic.security_tokens.generate_token(['xxx@example.com', 3], 'add_login',
                                                        app.config['SECRET_KEY'])

    result = sampledb.logic.security_tokens.verify_token(erg, 'add_login', app.config['SECRET_KEY'])

    assert result[0] is not 'xxx@example.com' or result[1] is not 3

