from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

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


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    must_change_password = models.BooleanField(default=True)


class AuditLog(models.Model):
    class Action(models.TextChoices):
        RESOURCE_CREATED = "resource_created", "Resource created"
        RESOURCE_UPDATED = "resource_updated", "Resource updated"
        RESOURCE_DELETED = "resource_deleted", "Resource deleted"
        GRANT_CREATED = "grant_created", "Grant created"
        GRANT_REVOKED = "grant_revoked", "Grant revoked"
        GRANT_EXPIRED = "grant_expired", "Grant expired"
        USER_CREATED = "user_created", "User created"
        USER_ACTIVATED = "user_activated", "User activated"
        USER_DEACTIVATED = "user_deactivated", "User deactivated"
        USER_UPDATED = "user_updated", "User updated"
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    object_type = models.CharField(max_length=20)
    object_id = models.PositiveIntegerField()
    object_repr = models.CharField(max_length=80)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.action} -> {self.object_type} -> {self.timestamp}" 