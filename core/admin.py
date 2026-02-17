from django.contrib import admin
from .models import Resource, AccessGrant

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "resource_type", "environment", "owner", "is_active", "updated_at")
    list_filter = ("resource_type", "environment", "is_active")
    search_fields = ("name", "url", "owner__username", "owner__email")
    ordering = ("-updated_at",)
    autocomplete_fields = ("owner",)
    list_select_related = ("owner",)
        
    fieldsets = (
        (None, {"fields": ("name", "resource_type", "environment", "is_active")}),
        ("Enlace", {"fields": ("url",)}),
        ("Responsable", {"fields": ("owner",)}),
        ("Tiempos", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")

@admin.register(AccessGrant)
class AccessGrantAdmin(admin.ModelAdmin):
    list_display = ("user", "resource", "access_level", "status", "start_at", "end_at")
    list_filter = ("status", "access_level", "resource__environment", "resource__resource_type")
    search_fields = ("user__username", "user__email", "resource__name", "resource__url")
    ordering = ("-end_at",)
    autocomplete_fields = ("user","resource")
    list_select_related = ("user","resource")
    
    fieldsets = (
        (None, {"fields": ("user", "resource", "access_level", "status")}),
        ("Vigencia", {"fields": ("start_at", "end_at")}),
        ("Notas", {"fields": ("notes",)}),
    )