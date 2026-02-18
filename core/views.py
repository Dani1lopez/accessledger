from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import permission_required, login_required

from core.forms import AccessGrantForm
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

@login_required
@permission_required("core.can_grant_access", raise_exception=True)
def grant_create(request, resource_pk):
    resource = get_object_or_404(Resource, pk=resource_pk)
    if request.method == "POST":
        form = AccessGrantForm(request.POST)
        if form.is_valid():
            grant = form.save(commit=False)
            grant.resource = resource
            grant.status = AccessGrant.Status.ACTIVE
            grant.save()
            return redirect("resource_detail", pk=resource.pk)
    else:
        form = AccessGrantForm()
    return render(request, "core/grant_create.html", {
        "resource": resource,
        "form": form,
    })