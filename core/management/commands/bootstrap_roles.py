from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from core.models import Resource, AccessGrant

class Command(BaseCommand):
    help = "Bootstrap Roles"
    
    
    
    def handle(self, *args, **options):
        self.stdout.write("bootstrap_roles running")
        
        def ensure_perm(group: Group, model, codename: str) -> None:
            ct = ContentType.objects.get_for_model(model)
            perm = Permission.objects.get(content_type=ct, codename=codename)
            if not group.permissions.filter(content_type=ct, codename=codename).exists():
                group.permissions.add(perm)
                self.stdout.write(f"✅ Asignado {codename} a {group.name}")
        
        def ensure_custom_perm(group: Group, codename: str) -> None:
            perm = Permission.objects.get(codename=codename)
            if not group.permissions.filter(codename=codename).exists():
                group.permissions.add(perm)
                self.stdout.write(f"✅ Asignado {codename} a {group.name}")

        viewer, viewer_created = Group.objects.get_or_create(name="viewer")
        self.stdout.write(f"viewer creado ahora? {viewer_created}")
        
        editor, editor_created = Group.objects.get_or_create(name="editor")
        self.stdout.write(f"editor creado ahora? {editor_created}")
        
        admin, admin_created = Group.objects.get_or_create(name="admin")
        self.stdout.write(f"admin creado ahora? {admin_created}")
        
        for codename in ("view_resource", "add_resource", "change_resource", "delete_resource"):
            ensure_perm(admin, Resource, codename)
        
        for codename in ("view_accessgrant", "add_accessgrant", "change_accessgrant", "delete_accessgrant"):
            ensure_perm(admin, AccessGrant, codename)
        
        ensure_custom_perm(admin, "can_grant_access")
        ensure_custom_perm(admin, "can_revoke_access")
        
        
        ensure_perm(viewer, Resource, "view_resource")
        ensure_perm(viewer, AccessGrant, "view_accessgrant")
        
        ensure_perm(editor, Resource, "view_resource")
        ensure_perm(editor, Resource, "change_resource")
        ensure_perm(editor, AccessGrant, "view_accessgrant")
        ensure_perm(editor, AccessGrant, "change_accessgrant")
        
        perms = viewer.permissions.values_list("codename", flat=True)
        self.stdout.write(f"Permisos viewer: {sorted(perms)}")
        
        perms = editor.permissions.values_list("codename", flat=True)
        self.stdout.write(f"Permisos editor: {sorted(perms)}")
        
        perms = admin.permissions.values_list("codename", flat=True)
        self.stdout.write(f"Permisos admin: {sorted(perms)}")

