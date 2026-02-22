from typing import Any

from django.shortcuts import redirect

ALLOWED_PATHS = ["/password/change/", "/logout/"]

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if (request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.must_change_password == True and request.path not in ALLOWED_PATHS):
            return redirect("password_change")
        response = self.get_response(request)
        return response