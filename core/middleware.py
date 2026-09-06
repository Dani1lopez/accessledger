from django.shortcuts import redirect

# Paths that are always allowed when must_change_password=True.
# Exact-match paths (set membership) cover discrete endpoints; prefix-match
# paths (tuple of startswith prefixes) cover subpath families like the
# Django admin (/admin/login/, /admin/logout/, /admin/users/, etc.).
ALLOWED_EXACT = {"/login/", "/admin/logout/"}
ALLOWED_PREFIX = ("/password/", "/admin/")

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        is_allowed = path in ALLOWED_EXACT or any(
            path.startswith(p) for p in ALLOWED_PREFIX
        )
        if (
            request.user.is_authenticated
            and hasattr(request.user, "profile")
            and request.user.profile.must_change_password
            and not is_allowed
        ):
            return redirect("password_change")
        response = self.get_response(request)
        return response