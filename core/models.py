from django.conf import settings
from django.db import models


class Resource(models.Model):
    class ResourceType(models.TextChoices):
        REPO = "repo", "Repository"
        SERVER = "server", "Server"
        VPN = "vpn", "VPN"
        SAAS = "saas", "SaaS"
        DATABASE = "database", "Database"
        DASHBOARD = "dashboard", "Dashboard"
        OTHER = "other", "Other"
    
    class Environment(models.TextChoices):
        PROD = "prod", "Production"
        STAGING = "staging", "Staging"
        DEV = "dev", "Development"
        NA = "na", "N/A"
    
    name = models.CharField(max_length=120, unique=True)
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    environment = models.CharField(max_length=30, choices=Environment.choices, default=Environment.NA)
    url = models.URLField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="owned_resources"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self) -> str:
        return self.name


class AccessGrant(models.Model):
    class AccessLevel(models.TextChoices):
        READ = "read", "Read"
        WRITE = "write", "Write"
        ADMIN = "admin", "Admin"
    
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_grants")
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="access_grants")
    access_level = models.CharField(max_length=10, choices=AccessLevel.choices)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["user", "resource"]),
            models.Index(fields=["end_at"]),
        ]
        
        permissions = [
            ("can_grant_access", "Can grant access to resource"),
            ("can_revoke_access", "Can revoke access grants"),
        ]
    
    def __str__(self):
        return f"{self.user} → {self.resource} ({self.access_level})"