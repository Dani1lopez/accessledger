from dataclasses import fields

from django import forms
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
                raise forms.ValidationError("Error no puede ser anterior la fecha fin a la de fecha de inicio")
        return cleaned_data


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ["name", "resource_type", "environment", "url", "is_active"]


class UserForm(forms.ModelForm):
    role = forms.ModelChoiceField(queryset=Group.objects.all())
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]