from django import forms
from .models import AccessGrant

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
                raise forms.ValidationError("Error no puede ser anteiro la fecha fin a la de fecha de inicio")
        return cleaned_data