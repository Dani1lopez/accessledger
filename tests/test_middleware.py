import pytest


@pytest.mark.django_db
class TestForcePasswordChangeMiddleware:
    """Verify middleware redirects forced-password users away from non-allowed paths,
    and blocks /logout/ specifically."""

    def test_logout_blocked_when_must_change_password(self, forced_password_client):
        """User with must_change_password=True cannot access /logout/ — redirected to password change."""
        response = forced_password_client.post("/logout/")
        assert response.status_code == 302
        assert response.url == "/password/change/"

    def test_logout_allowed_after_password_change(self, viewer_client):
        """User with must_change_password=False can logout normally."""
        response = viewer_client.post("/logout/")
        assert response.status_code == 302
        assert response.url == "/login/"

    def test_password_change_page_accessible_when_forced(self, forced_password_client):
        """/password/change/ is in ALLOWED_PATHS — should return 200 even when forced."""
        response = forced_password_client.get("/password/change/")
        assert response.status_code == 200

    def test_non_allowed_path_redirects_when_forced(self, forced_password_client):
        """Any path not in ALLOWED_PATHS redirects to password change when forced."""
        response = forced_password_client.get("/resources/")
        assert response.status_code == 302
        assert response.url == "/password/change/"

    def test_login_page_accessible_when_forced(self, forced_password_client):
        """/login/ is in ALLOWED_PATHS — middleware must not redirect to password/change/.
        (LoginView itself redirects authenticated users to LOGIN_REDIRECT_URL — that's fine.)"""
        response = forced_password_client.get("/login/")
        # Response is a redirect (LoginView redirects authenticated users),
        # but it must NOT be the middleware-forced redirect to /password/change/
        assert response.status_code == 302
        assert response.url != "/password/change/"
