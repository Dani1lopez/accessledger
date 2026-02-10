from django.contrib import admin
from .models import Resource, AccessGrant

admin.site.register(Resource)
admin.site.register(AccessGrant)