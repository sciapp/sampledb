# coding: utf-8
'''

'''

import pytest

from sampledb.logic import utils, errors


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
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('https://www.example.com', max_length=10)
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http://999.123.123.123')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http://.example.com')
    with pytest.raises(errors.InvalidURLError):
        utils.parse_url('http:///example.com')
    with pytest.raises(errors.InvalidURLError):
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
