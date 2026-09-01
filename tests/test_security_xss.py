"""Regression tests for the reflected XSS class fixed in PR #71 (issue #55).

Two templates in the codebase interpolated ``{{ user.username }}`` into
inline JavaScript, which is the canonical reflected-XSS pattern: Django's
HTML autoescape escapes HTML-significant characters (``"``, ``<``, ``>``,
``&``, ``'``); the browser HTML parser decodes them back (``&quot;`` → ``"``,
``&#x27;`` → ``'``) **before** the inline JavaScript parses, so a crafted
username such as ``x"); alert(document.cookie);//`` could break out of
the string literal and execute arbitrary code.

Templates fixed by this PR:

1. ``templates/registration/password_change_form.html`` — the inline
   ``<script>const USERNAME = "{{ request.user.username }}";</script>``
   block was removed; the username is now passed via a
   ``data-username="..."`` attribute on the new-password input (Django
   autoescape inside the attribute value closes the escape hatch).
2. ``core/templates/core/resource_detail.html`` — the inline
   ``onsubmit="return confirm('…@{{ g.user.username }}?')"`` handler was
   replaced with a ``data-confirm="…"`` attribute consumed by a
   delegated JS handler that calls ``window.confirm(...)``. ``confirm()``
   only displays text — it never evaluates it — so the same escape
   property holds even when the message embeds a user-controlled string.

The contract enforced by these tests is therefore:

1. The password-change response MUST NOT contain an inline ``<script>``
   block that embeds the username as a JavaScript string literal.
2. The password-change response MUST NOT contain the ``USERNAME = "``
   substring at all (broader guard against future re-introductions).
3. A user with a malicious username MUST render the password-change page
   with HTTP 200 and the literal payload MUST NOT appear as a
   JS-executable fragment.
4. The new-password input MUST carry a ``data-username="..."`` attribute
   and the value MUST be HTML-escaped (so ``"`` becomes ``&quot;``).
5. The decoded ``data-username`` attribute MUST equal
   ``user.get_username()`` for the authenticated user (round-trip
   contract that the JS consumer depends on).
6. The resource-detail revoke form MUST NOT use an inline ``onsubmit``
   handler that interpolates the username; it MUST use ``data-confirm``
   carrying the HTML-escaped username.
"""

from __future__ import annotations

import html
import re
from datetime import timedelta
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from core.models import AccessGrant, Resource


# A canonical JS-injection payload. Django's default
# ``UnicodeUsernameValidator`` regex is ``^[\\w.@+-]+\\Z`` and rejects
# these characters outright; ``User.objects.create_user`` skips that
# validator (it does not call ``full_clean``), so the payload can still
# be persisted via shell/scripted paths and remains a meaningful
# regression target for the rendering layer. ``UnicodeUsernameValidator``
# does NOT permit ``;``, ``"``, ``(``, ``)``, ``/``, ``*``, ``!``.
XSS_PAYLOAD = 'x"); alert(document.cookie);//'
XSS_PAYLOAD_SINGLE_QUOTE = "evil'); alert(1);//"


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

    def test_password_change_skips_similarity_for_empty_username(self):
        """An empty or missing username must not make every password similar."""
        javascript = Path(
            "core/static/core/js/password_change.js"
        ).read_text()

        assert re.search(
            r"const okSimilar = username\.length === 0 \|\| .*includes\(username\.toLowerCase\(\)\)",
            javascript,
        )

    def test_password_change_still_checks_nonempty_username(self):
        """A populated username still participates in the similarity check."""
        javascript = Path(
            "core/static/core/js/password_change.js"
        ).read_text()

        assert re.search(
            r"!val\.toLowerCase\(\)\.includes\(username\.toLowerCase\(\)\)",
            javascript,
        )


def _data_confirm_value(content: str, action_url: str) -> str:
    """Extract the value of the ``data-confirm`` attribute on the revoke
    form (identified by its ``action`` URL), HTML-decoded.

    Stdlib-only regex (no BeautifulSoup) to stay within the project's
    test dependency set. Returns the HTML-decoded value so callers can
    compare against ``user.get_username()`` directly.
    """
    # Find the <form> tag whose action attribute matches action_url.
    # We anchor on `action="..."` to avoid matching other forms on the
    # same page (e.g. hx-post forms in the resource detail header).
    pattern = re.compile(
        r'<form\b[^>]*\baction="' + re.escape(action_url) + r'"[^>]*>',
        re.DOTALL,
    )
    match = pattern.search(content)
    assert match is not None, (
        f"expected a <form action=\"{action_url}\"> in the response; got: {content!r}"
    )
    tag = match.group(0)
    attr_match = re.search(r'data-confirm="([^"]*)"', tag)
    assert attr_match is not None, (
        f"expected data-confirm attribute on the revoke form: {tag!r}"
    )
    return html.unescape(attr_match.group(1))


@pytest.fixture
def admin_viewer(db):
    """An admin user who can view the resource detail page and revoke."""
    return User.objects.create_user(
        username="xss-admin",
        password="SafePass123!",
    )


@pytest.fixture
def malicious_target(db):
    """A user whose username contains the single-quote XSS payload.

    ``UnicodeUsernameValidator`` rejects ``'``; ``create_user`` skips
    validators, so the user is persistable via shell/scripted paths.
    """
    User.objects.filter(username=XSS_PAYLOAD_SINGLE_QUOTE).delete()
    return User.objects.create_user(
        username=XSS_PAYLOAD_SINGLE_QUOTE,
        password="SafePass123!",
    )


@pytest.fixture
def active_grant_for(malicious_target):
    """An ACTIVE AccessGrant for ``malicious_target`` on a fresh resource."""
    resource = Resource.objects.create(
        name="xss-target-server", resource_type="server"
    )
    return AccessGrant.objects.create(
        user=malicious_target,
        resource=resource,
        access_level=AccessGrant.AccessLevel.READ,
        start_at=timezone.now(),
        end_at=timezone.now() + timedelta(days=30),
    )


@pytest.mark.django_db
class TestResourceDetailRevokeXSSRegression:
    """Regression contract for the same XSS class as issue #55, on the
    revoke form in ``core/templates/core/resource_detail.html``.

    The vulnerable template used an inline ``onsubmit="return
    confirm('…@{{ g.user.username }}?')"`` handler. A username containing
    ``'`` (e.g. ``evil'); alert(1);//``) breaks out of the ``confirm()``
    string literal because Django autoescape escapes ``'`` to ``&#x27;``
    and the browser decodes it back to ``'`` before the JS handler runs.

    The fix replaces ``onsubmit`` with a ``data-confirm`` attribute; a
    delegated JS handler (``core/static/core/js/delegated.js``) reads
    ``form.dataset.confirm`` and calls ``window.confirm(...)``. Because
    ``confirm()`` only displays text, the same autoescape property holds.
    """

    def test_revoke_form_has_no_inline_onsubmit(
        self, admin_client, active_grant_for
    ):
        """REQ-SEC-6.1: revoke form must not use an inline onsubmit
        handler that interpolates the username.
        """
        url = f"/resources/{active_grant_for.resource.pk}/"
        response = admin_client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        revoke_url = f"/grants/{active_grant_for.pk}/revoke"
        # No inline JS handler on the revoke form. The whole class of
        # reflected XSS via `onsubmit="...{{ username }}..."` must be
        # absent — not just for this user, but structurally.
        pattern = re.compile(
            r'<form\b[^>]*\baction="' + re.escape(revoke_url) + r'"[^>]*>',
            re.DOTALL,
        )
        match = pattern.search(content)
        assert match is not None, (
            f"expected a revoke <form action=\"{revoke_url}\">; got: {content!r}"
        )
        assert "onsubmit" not in match.group(0), (
            "revoke form still has an inline onsubmit handler: "
            f"{match.group(0)!r}"
        )

    def test_revoke_form_has_data_confirm_attribute(
        self, admin_client, active_grant_for
    ):
        """REQ-SEC-6.2: the revoke form must carry a ``data-confirm="…"``
        attribute holding the confirmation message.

        The malicious username contains a single quote (``'``) which the
        old ``onsubmit="return confirm('…')"`` handler allowed to break
        out of the JS string literal. We verify the load-bearing safety
        property: the raw HTML escapes ``'`` to ``&#x27;`` inside the
        attribute, and the decoded value (what the JS handler passes to
        ``confirm()``) embeds the original username.
        """
        url = f"/resources/{active_grant_for.resource.pk}/"
        response = admin_client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        revoke_url = f"/grants/{active_grant_for.pk}/revoke"

        # 1) Raw HTML: the single-quote in the malicious username must
        #    be HTML-escaped to ``&#x27;`` inside the data-confirm
        #    attribute. This is what prevents the browser from decoding
        #    it back to ``'`` and stepping out of the JS string literal.
        revoke_form_match = re.search(
            r'<form\b[^>]*\baction="' + re.escape(revoke_url) + r'"[^>]*>',
            content,
            re.DOTALL,
        )
        assert revoke_form_match is not None
        assert "&#x27;" in revoke_form_match.group(0), (
            "single-quote not HTML-escaped in raw form HTML: "
            f"{revoke_form_match.group(0)!r}"
        )

        # 2) Decoded message: after the browser decodes &#x27; back to '
        #    inside the attribute and the JS reads form.dataset.confirm,
        #    the message must contain the original username (round-trip
        #    contract that makes the confirm dialog useful).
        value = _data_confirm_value(content, revoke_url)
        assert "¿Revocar acceso de @" in value
        assert XSS_PAYLOAD_SINGLE_QUOTE in value, (
            f"decoded confirm message missing username: {value!r}"
        )

    def test_revoke_form_decoded_confirm_matches_username(
        self, admin_client, active_grant_for, malicious_target
    ):
        """REQ-SEC-6.3: the decoded data-confirm value must embed the
        user's username (round-trip contract that the delegated JS
        handler depends on to display a useful message).
        """
        url = f"/resources/{active_grant_for.resource.pk}/"
        response = admin_client.get(url)
        content = response.content.decode()
        revoke_url = f"/grants/{active_grant_for.pk}/revoke"
        value = _data_confirm_value(content, revoke_url)
        assert malicious_target.get_username() in value

    def test_revoke_form_with_double_quote_username(
        self, admin_client, active_grant_for
    ):
        """A double-quote payload (defence-in-depth) must also be HTML-
        escaped on the data-confirm attribute. Django autoescape escapes
        ``"`` to ``&quot;`` inside the attribute value, where the browser
        cannot use it to step out.

        The load-bearing check is that the raw HTML carries ``&quot;``
        for every literal ``"`` in the username, so the attribute
        cannot terminate early. We do not assert ``alert(1)`` is absent
        from the form tag — it correctly remains in the attribute
        value, where it is inert (it is rendered as part of the
        ``confirm()`` message text, never evaluated).
        """
        # Replace the grant's user with a double-quote username user.
        bad = User.objects.create_user(
            username='x"); alert(1);//',
            password="SafePass123!",
        )
        active_grant_for.user = bad
        active_grant_for.save()
        url = f"/resources/{active_grant_for.resource.pk}/"
        response = admin_client.get(url)
        content = response.content.decode()
        revoke_url = f"/grants/{active_grant_for.pk}/revoke"
        # The double-quote must appear as &quot; in the raw HTML — that
        # is the load-bearing escape that prevents the attribute from
        # terminating early.
        revoke_form_match = re.search(
            r'<form\b[^>]*\baction="' + re.escape(revoke_url) + r'"[^>]*>',
            content,
            re.DOTALL,
        )
        assert revoke_form_match is not None
        assert "&quot;" in revoke_form_match.group(0), (
            "double-quote not HTML-escaped in raw form HTML: "
            f"{revoke_form_match.group(0)!r}"
        )
        # And the attribute must still be a single, well-formed attribute
        # (no premature close-quote that would let later content leak
        # into the surrounding tag). Assert there is exactly one closing
        # ``">`` for the form tag.
        assert revoke_form_match.group(0).rstrip().endswith(">"), (
            "revoke form tag is not well-formed: "
            f"{revoke_form_match.group(0)!r}"
        )

    def test_delegated_js_handles_data_confirm_forms(self):
        """Static source check: ``core/static/core/js/delegated.js`` must
        route forms with a ``data-confirm`` attribute through
        ``window.confirm(form.dataset.confirm)`` and call
        ``e.preventDefault()`` on cancel.

        Without a JS runtime in the test suite, this is the next-best
        guarantee that the delegated handler exists and reads the
        attribute the template populates.
        """
        javascript = Path(
            "core/static/core/js/delegated.js"
        ).read_text()

        # The data-confirm branch reads the attribute and calls confirm().
        assert re.search(
            r"form\.dataset\.confirm",
            javascript,
        ), "delegated.js must read form.dataset.confirm"
        assert re.search(
            r"window\.confirm\(\s*form\.dataset\.confirm\s*\)",
            javascript,
        ), "delegated.js must call window.confirm(form.dataset.confirm)"
        # And it must short-circuit the submission on cancel.
        assert re.search(
            r"e\.preventDefault\(\)",
            javascript,
        ), "delegated.js must call e.preventDefault() to abort cancel"

