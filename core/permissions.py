def user_can_modify_resource(user, resource) -> bool:
    """Check if a user can modify (update/delete) a resource.

    Returns True if the user is a superuser, belongs to the "admin" group,
    or is the owner of the resource. Resources with no owner (orphan) are
    restricted to admins and superusers only.
    """
    if user.is_superuser:
        return True
    if user.groups.filter(name="admin").exists():
        return True
    if resource.owner_id is None:
        return False
    return resource.owner_id == user.id
