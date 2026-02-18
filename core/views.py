from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import permission_required, login_required
from .models import AccessGrant, Resource

@login_required
@permission_required("core.view_resource", raise_exception=True)
def resource_list(request):
    resources = Resource.objects.all().order_by("name")
    return render(request, "core/resource_list.html", {"resources": resources})

@login_required
@permission_required("core.view_resource", raise_exception=True)
def resource_detail(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    grants = (
        AccessGrant.objects
        .filter(resource=resource)
        .select_related("user")
        .order_by("status", "-end_at")
    )
    return render(request, "core/resource_detail.html", {
        "resource": resource,
        "grants": grants,
    })