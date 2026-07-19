"""Regression tests for the reflected XSS in
``templates/registration/password_change_form.html`` (issue #55).

The vulnerable template injected ``{{ request.user.username }}`` inside an
inline ``<script>const USERNAME = "..."</script>`` block. Django's HTML
autoescape only escapes HTML-significant characters (``"``, ``<``, ``>``,
``&``); the browser HTML parser decodes ``&quot;`` back to ``"`` *before*
the inline JavaScript parses, so a username such as
``x"); alert(document.cookie);//`` could break out of the string literal and
execute arbitrary code.

The fix moves the username to a ``data-username="..."`` attribute on the
new-password input (rendered via Django's widget-attr pipeline, so Django's
autoescape escapes ``"`` to ``&quot;`` *inside the attribute value*, where
the browser parser cannot use it to step out of the attribute). The
inline ``<script>`` is removed; the password-strength JS reads the username
from ``input.dataset.username``.

The contract enforced by these tests is therefore:

1. The response body MUST NOT contain an inline ``<script>`` block that
   embeds the username as a JavaScript string literal.
2. The response body MUST NOT contain the ``USERNAME = "`` substring at
   all (broader guard against future re-introductions).
3. A user with a malicious username MUST render the page with HTTP 200
   and the literal payload MUST NOT appear as a JS-executable fragment.
4. The new-password input MUST carry a ``data-username="..."`` attribute
   and the value MUST be HTML-escaped (so ``"`` becomes ``&quot;``).
5. The decoded ``data-username`` attribute MUST equal
   ``user.get_username()`` for the authenticated user (round-trip
   contract that the JS consumer depends on).
"""

from __future__ import annotations

import html
import re

import pytest
from django.contrib.auth.models import User
from django.test import Client


# A canonical JS-injection payload. Django's default
# ``UnicodeUsernameValidator`` allows ASCII letters, digits, and ``@.+-_``
# plus any non-ASCII printable character. ``;``, ``"``, ``(``, ``)``,
# ``/``, ``*``, ``!`` are all permitted; we exploit that here.
XSS_PAYLOAD = 'x"); alert(document.cookie);//'


@pytest.fixture
def xss_user(db):
    """User whose username is a known JS-injection payload."""
    User.objects.filter(username=XSS_PAYLOAD).delete()
    return User.objects.create_user(
        username=XSS_PAYLOAD,
        password="SafePass123!",
    )


@pytest.fixture
def xss_client(xss_user):
    """Client logged in as the XSS-username user."""
    client = Client()
    client.login(username=xss_user.username, password="SafePass123!")
    return client


def _data_username_value(response_content: str) -> str:
    """Extract the value of the ``data-username`` attribute on the
    ``id_new_password1`` input, HTML-decoded.

    Implemented with a stdlib-only regex (no BeautifulSoup dependency) to
    stay within the project's test dependency set.
    """
    # Find the input element by id; capture the data-username attribute
    # value. The attribute value may contain ``&quot;`` (HTML-escaped
    # double-quote) which we decode back to a literal ``"``.
    pattern = re.compile(
        r'<input\b[^>]*\bid="id_new_password1"[^>]*>',
        re.DOTALL,
    )
    match = pattern.search(response_content)
    assert match is not None, (
        "expected an <input id=\"id_new_password1\"> element in the response"
    )
    tag = match.group(0)
    attr_match = re.search(
        r'data-username="([^"]*)"',
        tag,
    )
    assert attr_match is not None, (
        f"expected data-username attribute on input tag: {tag!r}"
    )
    return html.unescape(attr_match.group(1))


@pytest.mark.django_db
class TestPasswordChangeXSSRegression:
    """Regression contract for issue #55.

    All five tests MUST fail on the pre-fix template and PASS on the
    post-fix template (form class + view wiring + template removal +
    JS dataset read).
    """

    def test_password_change_no_inline_script_block(
        self, forced_password_client
    ):
        """REQ-SEC-1: response must not embed ``const USERNAME = "..."``."""
        response = forced_password_client.get("/password/change/")
        assert response.status_code == 200
        content = response.content.decode()
        assert 'const USERNAME = "' not in content

    def test_password_change_no_username_string_in_response(
        self, forced_password_client
    ):
        """REQ-SEC-5: broader guard against any inline-script
        re-introduction of the username-as-string-literal anti-pattern.
        """
        response = forced_password_client.get("/password/change/")
        assert response.status_code == 200
        content = response.content.decode()
        # Broader check: any future inline-script reintroduction of the
        # username-as-string-literal antipattern fails this assertion.
        assert 'USERNAME = "' not in content

    def test_password_change_handles_xss_username(self, xss_client):
        """REQ-SEC-2 / REQ-SEC-5: a malicious username must render the
        page with status 200 and must not appear as a JS string literal
        inside any inline ``<script>`` block.

        Django's HTML autoescape escapes ``"`` to ``&quot;`` even in the
        vulnerable template, so the literal substring
        ``x"); alert(document.cookie);//`` does NOT appear verbatim in
        the raw HTML — the browser decodes ``&quot;`` back to ``"`` at
        parse time, which is precisely what enables the XSS. The
        load-bearing check is therefore that the malicious username is
        NEVER interpolated into a ``<script>`` block as a JS string
        literal: we look for ``const USERNAME = "<first-char>`` (the
        opening of the dangerous pattern), which is present on the
        vulnerable template and absent on the fixed template.
        """
        response = xss_client.get("/password/change/")
        assert response.status_code == 200
        content = response.content.decode()
        # The dangerous JS-string-literal pattern must be absent. We
        # match `const USERNAME = "<first-char>` rather than the full
        # payload because the `"` is HTML-escaped in the vulnerable
        # template.
        assert 'const USERNAME = "x' not in content
        # And no inline <script> block contains the malicious username.
        for script_body in re.findall(
            r"<script\b[^>]*>(.*?)</script>", content, re.DOTALL
        ):
            assert XSS_PAYLOAD not in script_body, (
                "XSS payload found inside inline <script> block: "
                f"{script_body!r}"
            )

    def test_password_change_input_has_data_username(self, xss_client):
        """REQ-SEC-3: the new-password input must carry a
        ``data-username="..."`` attribute, with ``"`` escaped to ``&quot;``.
        """
        response = xss_client.get("/password/change/")
        assert response.status_code == 200
        content = response.content.decode()
        # The attribute must be present on the input.
        assert "data-username=" in content
        # The double-quote in the username must be HTML-escaped to
        # ``&quot;`` (proof that the value is bound by the surrounding
        # attribute quotes and cannot step out into JS context).
        assert "&quot;" in content

    def test_password_change_username_value_matches_user(
        self, xss_client, xss_user
    ):
        """REQ-FUNC-5 / REQ-STRUCT-2: the decoded ``data-username``
        attribute value MUST equal ``user.get_username()``.
        """
        response = xss_client.get("/password/change/")
        assert response.status_code == 200
        actual = _data_username_value(response.content.decode())
        assert actual == xss_user.get_username()

    def test_password_change_html_tag_username(self, client):
        """HTML tags in the username remain escaped inside the attribute."""
        username = "<b>test</b>"
        user = User.objects.create_user(username=username, password="SafePass123!")
        assert client.login(username=username, password="SafePass123!") is True

        response = client.get("/password/change/")

        assert response.status_code == 200
        content = response.content.decode()
        assert "<b>test</b>" not in content
        assert "&lt;b&gt;test&lt;/b&gt;" in content
        assert _data_username_value(content) == user.get_username()

    def test_password_change_backslash_username(self, client):
        """Backslashes are preserved as data, not interpreted as JavaScript."""
        username = r"evil\username"
        user = User.objects.create_user(username=username, password="SafePass123!")
        assert client.login(username=username, password="SafePass123!") is True

        response = client.get("/password/change/")

        assert response.status_code == 200
        content = response.content.decode()
        assert 'const USERNAME = "' not in content
        assert _data_username_value(content) == user.get_username()

    def test_password_change_empty_username(self, client):
        """An empty username is handled by the defensive form path."""
        user = User(username="")
        user.set_password("SafePass123!")
        user.save()
        assert client.login(username="", password="SafePass123!") is True

        response = client.get("/password/change/")

        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="id_new_password1"' in content
        assert 'data-username=""' in content
        assert _data_username_value(content) == user.get_username()
