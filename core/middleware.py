from typing import Any

from django.shortcuts import redirect


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated and request.user.profile.must_change_password == True and request.path != "/password/change/":
            return redirect("password_change")
        response = self.get_response(request)
        return response