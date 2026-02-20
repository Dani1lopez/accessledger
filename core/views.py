from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import permission_required, login_required
from django.http import JsonResponse, HttpResponseNotAllowed
from core.forms import AccessGrantForm, ResourceForm
from .models import AccessGrant, Resource
from django.contrib.auth.models import User

@login_required
@permission_required("core.view_resource", raise_exception=True)
def resource_list(request):
    resources = Resource.objects.all().order_by("name")
    return render(request, "core/resource_list.html", {"resources": resources, "form": ResourceForm()})

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
@permission_required("core.add_resource", raise_exception=True)
def resource_create(request):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    
    if request.method == "POST":
        form = ResourceForm(request.POST)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.owner = request.user
            resource.save()
            return JsonResponse({"success": True}) if is_ajax else redirect("resource_list")
        elif is_ajax:
            return JsonResponse({"success": False, "errors": form.errors})
    elif is_ajax:
        return HttpResponseNotAllowed(["POST"])
    else:
        form = ResourceForm()
    
    return render(request, "core/resource_create.html", {"form": form})

@login_required
@permission_required("core.change_resource", raise_exception=True)
def resource_update(request, pk):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    resource = get_object_or_404(Resource, pk=pk)
    if request.method == "POST":
        form = ResourceForm(request.POST,instance=resource)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.save()
            return JsonResponse({"success": True}) if is_ajax else redirect("resource_list")
        elif is_ajax:
            return JsonResponse({"success": False, "errors": form.errors})
    elif is_ajax:
        return HttpResponseNotAllowed(["POST"])
    else:
        form = ResourceForm(instance=resource)
    return render(request, "core/resource_update.html", {
        "resource": resource,
        "form": form
    })

@login_required
@permission_required("core.change_resource", raise_exception=True)
def resource_data(request, pk):
    resource = get_object_or_404(Resource, pk = pk)
    return JsonResponse({
        "name": resource.name,
        "resource_type": resource.resource_type,
        "environment": resource.environment,
        "url": resource.url,
        "is_active": resource.is_active
    })


@login_required
@permission_required("core.delete_resource", raise_exception=True)
def resource_delete(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    if request.method == "POST":
        resource.delete()
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        return JsonResponse({"success": True}) if is_ajax else redirect("resource_list")
    else:
        return render(request, "core/resource_delete.html",{
            "resource": resource
        })

@login_required
@permission_required("core.can_grant_access", raise_exception=True)
def grant_create(request, resource_pk):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    resource = get_object_or_404(Resource, pk=resource_pk)
    if request.method == "POST":
        form = AccessGrantForm(request.POST)
        if form.is_valid():
            grant = form.save(commit=False)
            grant.resource = resource
            grant.status = AccessGrant.Status.ACTIVE
            grant.save()
            return JsonResponse({"success": True}) if is_ajax else redirect("resource_detail", pk=resource_pk)
        elif is_ajax:
            return JsonResponse({"success": False, "errors": form.errors})
    elif is_ajax:
        return HttpResponseNotAllowed(["POST"])
    else:
        form = AccessGrantForm()
    return render(request, "core/grant_create.html", {
        "resource": resource,
        "form": form,
    })

@login_required
@permission_required("core.can_revoke_access", raise_exception=True)
def grant_revoke(request, pk):
    grant = get_object_or_404(AccessGrant, pk=pk)
    if request.method == "POST":
        grant.status = AccessGrant.Status.REVOKED
        grant.save()
        return redirect("resource_detail", pk=grant.resource.pk)
    else:
        return redirect("resource_detail", pk=grant.resource.pk)


@login_required
@permission_required("core.can_grant_access", raise_exception=True)
def user_list(request):
    user = User.objects.values("id","username").order_by("username")
    return JsonResponse({
        "users": list(user)
    })