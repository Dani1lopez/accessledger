import pytest


@pytest.mark.django_db
class TestForcePasswordChangeMiddleware:
    """REQ-AR-010 — verify middleware redirects forced-password users away
    from non-allowed paths, and allows /admin/* and /password/* subpaths."""

    def test_logout_allowed_after_password_change(self, viewer_client):
        """User with must_change_password=False can logout normally."""
        response = viewer_client.post("/logout/")
        assert response.status_code == 302
        assert response.url == "/login/"

    def test_password_change_page_accessible_when_forced(self, forced_password_client):
        """/password/change/ is in ALLOWED_PREFIX — should return 200 even when forced."""
        response = forced_password_client.get("/password/change/")
        assert response.status_code == 200

    def test_non_allowed_path_redirects_when_forced(self, forced_password_client):
        """Any path not in ALLOWED_EXACT or ALLOWED_PREFIX redirects to password change."""
        response = forced_password_client.get("/resources/")
        assert response.status_code == 302
        assert response.url == "/password/change/"

    def test_login_page_accessible_when_forced(self, forced_password_client):
        """/login/ is in ALLOWED_EXACT — middleware must not redirect to /password/change/.
        (LoginView itself redirects authenticated users to LOGIN_REDIRECT_URL — that's fine.)"""
        response = forced_password_client.get("/login/")
        assert response.status_code == 302
        assert response.url != "/password/change/"

    # ── REQ-AR-010: admin subpaths are allowed (regression for the audit) ──

    def test_admin_login_not_blocked_when_forced(self, forced_password_client):
        """REQ-AR-010 Scenario 10.1 — /admin/login/ must NOT redirect to password_change.
        Otherwise forced-password users can never reach the Django admin to recover."""
        response = forced_password_client.get("/admin/login/")
        # Must NOT be the middleware-forced 302 to /password/change/.
        # A 200 from admin's login view, or a 302 to admin's own login
        # redirect, both satisfy the spec.
        if response.status_code == 302:
            assert response.url != "/password/change/"
        else:
            assert response.status_code == 200

    def test_admin_subpath_not_blocked_when_forced(self, forced_password_client):
        """REQ-AR-010 Scenario 10.2 — any /admin/<subpath>/ must pass through."""
        response = forced_password_client.get("/admin/users/")
        if response.status_code == 302:
            assert response.url != "/password/change/"
        else:
            assert response.status_code in (200, 403)

    def test_admin_logout_not_blocked_when_forced(self, forced_password_client):
        """REQ-AR-010 Scenario 10.3 — /admin/logout/ is in ALLOWED_EXACT."""
        response = forced_password_client.get("/admin/logout/")
        if response.status_code == 302:
            assert response.url != "/password/change/"
        else:
            assert response.status_code in (200, 405)

    def test_password_prefix_allowed(self, forced_password_client):
        """REQ-AR-010 Scenario 10.5 — /password/<anything>/ is allowed by prefix."""
        response = forced_password_client.get("/password/change/done/")
        if response.status_code == 302:
            assert response.url != "/password/change/"
        else:
            assert response.status_code in (200, 302)
