from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import AccessGrant, Resource
from django.contrib.auth.models import User, Group


class AccessGrantForm(forms.ModelForm):
    class Meta:
        model = AccessGrant
        fields = ["user", "access_level", "start_at", "end_at", "notes"]

    def clean(self):
        cleaned_data = super().clean()
        start_at = cleaned_data.get("start_at")
        end_at = cleaned_data.get("end_at")
        if start_at and end_at:
            if end_at <= start_at:
                raise forms.ValidationError(
                    "Error no puede ser anterior la fecha fin a la de fecha de inicio"
                )
        return cleaned_data


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ["name", "resource_type", "environment", "url", "is_active"]


class UserForm(forms.ModelForm):
    role = forms.ModelChoiceField(queryset=Group.objects.all())
    password = forms.CharField(required=False, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]


class UserCreateForm(UserForm):
    password = forms.CharField(required=True, widget=forms.PasswordInput)


class CustomPasswordChangeForm(PasswordChangeForm):
    """PasswordChangeForm variant that exposes the current username via the
    ``data-username`` attribute on the new-password input.

    This lets ``core/static/core/js/password_change.js`` read the username
    without an inline ``<script>const USERNAME = "..."</script>`` block —
    which was previously a reflected XSS vector for users with crafted
    usernames (issue #55). Django's HTML autoescape escapes ``"`` to
    ``&quot;`` inside the attribute, closing the escape hatch that the inline
    JS string literal relied on.
    """

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(user, *args, **kwargs)
        if user is not None:
            self.fields["new_password1"].widget.attrs["data-username"] = (
                user.get_username()
            )
