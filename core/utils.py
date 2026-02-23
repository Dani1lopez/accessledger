from .models import AuditLog

def log_action(user, action, obj, before=None, after= None):
    AuditLog.objects.create(
        user = user,
        action = action,
        object_type = obj.__class__.__name__, 
        object_id = obj.pk,
        object_repr = str(obj), 
        before = before,
        after = after,
    )