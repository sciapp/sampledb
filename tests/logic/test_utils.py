# coding: utf-8
'''

'''
import datetime

import pytest
import pytz

from sampledb.logic import utils, errors
from sampledb.models import Tag
from sampledb import db, config


def test_parse_url():
    assert utils.parse_url('https://www.example.com') == {
        'scheme': 'https',
        'domain': 'www.example.com',
        'host': None,
        'ip_address': None,
        'ipv6_address': None,
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('https://example.com:1234') == {
        'scheme': 'https',
        'domain': 'example.com',
        'host': None,
        'ip_address': None,
        'ipv6_address': None,
        'port': '1234',
        'path': '',
        'query': None
    }
    assert utils.parse_url('https://example.com') == {
        'scheme': 'https',
        'domain': 'example.com',
        'host': None,
        'ip_address': None,
        'ipv6_address': None,
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('https://example.com', max_length=23) == {
        'scheme': 'https',
        'domain': 'example.com',
        'host': None,
        'ip_address': None,
        'ipv6_address': None,
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('file://host/file/path') == {
        'scheme': 'file',
        'domain': None,
        'host': 'host',
        'ip_address': None,
        'ipv6_address': None,
        'port': None,
        'path': '/file/path',
        'query': None
    }
    assert utils.parse_url('ftp://host/file/path') == {
        'scheme': 'ftp',
        'domain': None,
        'host': 'host',
        'ip_address': None,
        'ipv6_address': None,
        'port': None,
        'path': '/file/path',
        'query': None
    }
    assert utils.parse_url('sftp://localhost') == {
        'scheme': 'sftp',
        'domain': None,
        'host': 'localhost',
        'ip_address': None,
        'ipv6_address': None,
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('http://123.123.123.123') == {
        'scheme': 'http',
        'domain': None,
        'host': None,
        'ip_address': '123.123.123.123',
        'ipv6_address': None,
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('https://[2001:0db8:85a3:08d3:1319:8a2e:0370:7344]') == {
        'scheme': 'https',
        'domain': None,
        'host': None,
        'ip_address': None,
        'ipv6_address': '2001:0db8:85a3:08d3:1319:8a2e:0370:7344',
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('https://[2001:db8:85a3:08d3:0:8a2e:0370:7344]') == {
        'scheme': 'https',
        'domain': None,
        'host': None,
        'ip_address': None,
        'ipv6_address': '2001:db8:85a3:08d3:0:8a2e:0370:7344',
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('https://[2001::85a3:08d3:1319:8a2e:0370:7344]') == {
        'scheme': 'https',
        'domain': None,
        'host': None,
        'ip_address': None,
        'ipv6_address': '2001::85a3:08d3:1319:8a2e:0370:7344',
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('https://[2001:0db8:85a3:08d3::8a2e:0370:7344]') == {
        'scheme': 'https',
        'domain': None,
        'host': None,
        'ip_address': None,
        'ipv6_address': '2001:0db8:85a3:08d3::8a2e:0370:7344',
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('https://[2001:0db8:85a3:08d3::]') == {
        'scheme': 'https',
        'domain': None,
        'host': None,
        'ip_address': None,
        'ipv6_address': '2001:0db8:85a3:08d3::',
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('https://[2001:0db8::7344]') == {
        'scheme': 'https',
        'domain': None,
        'host': None,
        'ip_address': None,
        'ipv6_address': '2001:0db8::7344',
        'port': None,
        'path': '',
        'query': None
    }
    assert utils.parse_url('https://[::2001:0db8:1234:7344]') == {
        'scheme': 'https',
        'domain': None,
        'host': None,
        'ip_address': None,
        'ipv6_address': '::2001:0db8:1234:7344',
        'port': None,
        'path': '',
        'query': None
    }

    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('example')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('com')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('ftp://example.com', valid_schemes=['http', 'https', 'file', 'sftp', 'smb'])
    with pytest.raises(errors.URLTooLongError):
        utils.parse_url('https://www.example.com', max_length=10)
    with pytest.raises(errors.InvalidIPAddressError):
        utils.parse_url('http://999.123.123.123')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http://.example.com')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http:///example.com')
    with pytest.raises(errors.InvalidPortNumberError):
        utils.parse_url('http://example.com:99999')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http://example.com:')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http://-example.com')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http://test.-example.com')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http://example-.com')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http://example.com-')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http://example.com-')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http://[2001::85a3:08d3::8a2e:0370:7344]')


def test_do_numeric_tags_exist():
    assert not utils.do_numeric_tags_exist()
    db.session.add(Tag(name='test'))
    db.session.commit()
    assert not utils.do_numeric_tags_exist()
    db.session.add(Tag(name=''))
    db.session.commit()
    assert not utils.do_numeric_tags_exist()
    db.session.add(Tag(name='123'))
    db.session.commit()
    assert utils.do_numeric_tags_exist()
    db.session.delete(Tag.query.filter_by(name='123').first())
    db.session.commit()
    assert not utils.do_numeric_tags_exist()


def test_get_translated_text():
    assert utils.get_translated_text(None) == ''
    assert utils.get_translated_text(None, default='default') == 'default'
    assert utils.get_translated_text('test') == 'test'
    assert utils.get_translated_text({'en': 'test'}) == 'test'
    assert utils.get_translated_text({'en': 'test_en', 'de': 'test_de'}) == 'test_en'
    assert utils.get_translated_text({'en': 'test_en', 'de': 'test_de'}, 'de') == 'test_de'
    assert utils.get_translated_text({'en': 'test_en'}, 'de') == 'test_en'
    assert utils.get_translated_text({'de': 'test_de'}, 'en') == 'test_de'
    assert utils.get_translated_text({'de': 'test_de'}) == 'test_de'


def test_cache():
    config.ENABLE_FUNCTION_CACHES = True
    evaluations_counter = 0

    @utils.cache
    def f():
        nonlocal evaluations_counter
        evaluations_counter += 1
        return evaluations_counter

    assert f() == 1
    assert f() == 1
    utils.clear_cache_functions()
    assert f() == 2
    assert f() == 2

    config.ENABLE_FUNCTION_CACHES = False
    evaluations_counter = 0

    @utils.cache
    def f():
        nonlocal evaluations_counter
        evaluations_counter += 1
        return evaluations_counter

    assert f() == 1
    assert f() == 2


def test_get_data_and_schema_by_id_path():
    data = {
        'name': {
            'text': {'en': 'Test'},
            '_type': 'text'},
        'array': [
            {
                'data': [
                    ['2024-01-01 00:02:03.123456', 1.0, 100000.0],
                    ['2024-01-01 00:02:04.123456', 1.0, 100000.0],
                    ['2024-01-01 00:02:05.123456', 2.0, 200000.0]
                ],
                '_type': 'timeseries',
                'units': 'bar',
                'dimensionality': '[mass] / [length] / [time] ** 2'
            }
        ]
    }
    schema = {
        "title": {
            "en": "Object Information"
        },
        "type": "object",
        "properties": {
            "name": {
                "title": {
                    "en": "Name"
                },
                "type": "text"
            },
            "array": {
                "type": "array",
                "title": "Array",
                "items": {
                    "title": "Pressure Series",
                    "type": "timeseries",
                    "units": "bar",
                    "display_digits": 2
                }
            }
        },
        "required": [
            "name"
        ],
        "propertyOrder": [
            "name",
            "array"
        ]
    }
    data_and_schema = utils.get_data_and_schema_by_id_path(data, schema, ['array', '0'], convert_id_path_elements=True)
    assert data_and_schema == (data['array'][0], schema['properties']['array']['items'])


def test_get_postgres_timezone_alias():
    for month in (1, 6):
        reference_datetime = datetime.datetime(2024, month, 4, 12, 34, 56)
        for timezone_name in pytz.all_timezones:
            postgres_timezone_alias = utils.get_postgres_timezone_alias(timezone_name, reference_datetime.date())
            if postgres_timezone_alias != timezone_name:
                assert postgres_timezone_alias.startswith('UTC')
                pytz_datetime = reference_datetime.replace(tzinfo=datetime.timezone.utc).astimezone(pytz.timezone(timezone_name))
                postgres_datetime = db.session.execute(db.text(
                    f"SELECT to_timestamp('2024-{month:02d}-4 12:34:56', 'YYYY-MM-DD HH24:MI:SS') AT TIME ZONE '{postgres_timezone_alias}';"
                )).scalar()
                assert postgres_datetime == pytz_datetime.replace(tzinfo=None)
                assert postgres_datetime.strftime('%Y-%m-%d %H:%M:%S') == pytz_datetime.strftime('%Y-%m-%d %H:%M:%S')
