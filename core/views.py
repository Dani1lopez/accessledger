from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import permission_required, login_required
from django.http import JsonResponse, HttpResponseNotAllowed
from core.decorators import admin_required
from core.forms import AccessGrantForm, ResourceForm, UserForm
from .models import AccessGrant, Resource, Profile, AuditLog
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from .utils import log_action


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
            log_action(
                user=request.user,
                action=AuditLog.Action.RESOURCE_CREATED,
                obj=resource,
                before=None,
                after={"name": resource.name, "resource_type": resource.resource_type}
            )
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
    before = {
        "name": resource.name, 
        "resource_type": resource.resource_type,
        "environment": resource.environment,
        "url": resource.url,
        "is_active": resource.is_active,
    }
    if request.method == "POST":
        form = ResourceForm(request.POST,instance=resource)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.save()
            log_action(
                user=request.user,
                action=AuditLog.Action.RESOURCE_UPDATED,
                obj=resource,
                before=before,
                after={
                    "name": resource.name, 
                    "resource_type": resource.resource_type,
                    "environment": resource.environment,
                    "url": resource.url,
                    "is_active": resource.is_active,
                }
            )
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
        before = {
            "name": resource.name, 
            "resource_type": resource.resource_type,
            "environment": resource.environment,
            "url": resource.url,
            "is_active": resource.is_active,
        }
        resource.delete()
        log_action(
            user=request.user,
            action=AuditLog.Action.RESOURCE_DELETED,
            obj=resource,
            before=before,
            after=None
        )
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
            log_action(
                user=request.user,
                action=AuditLog.Action.GRANT_CREATED,
                obj=grant,
                before=None,
                after={
                    "user": grant.user.username,
                    "resource": grant.resource.name,
                    "access_level": grant.access_level,
                    "status": grant.status,
                    "start_at": grant.start_at.isoformat(),
                    "end_at": grant.end_at.isoformat(),
                    "notes": grant.notes
                }
            )
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
        log_action(
            user=request.user,
            action=AuditLog.Action.GRANT_REVOKED,
            obj=grant,
            before={
                "user": grant.user.username,
                "resource": grant.resource.name,
                "access_level": grant.access_level,
                "status": "active",
                "start_at": grant.start_at.isoformat(),
                "end_at": grant.end_at.isoformat(),
                "notes": grant.notes
            },
            after={
                "user": grant.user.username,
                "resource": grant.resource.name,
                "access_level": grant.access_level,
                "status": "revoked",
                "start_at": grant.start_at.isoformat(),
                "end_at": grant.end_at.isoformat(),
                "notes": grant.notes
            }
        )
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


class CustomPasswordChangeView(PasswordChangeView):
    success_url = reverse_lazy("resource_list")
    def form_valid(self, form):
        self.request.user.profile.must_change_password = False
        self.request.user.profile.save()
        return super().form_valid(form)

@login_required
def user_profile(request):
    user = request.user
    return render(request, "core/user_profile.html", {
        "user": user,
    })


@login_required
@admin_required
def user_management(request):
    users = User.objects.all().prefetch_related("groups")
    groups = Group.objects.all()
    return render(request, "core/user_management.html", {
        "users": users,
        "groups": groups,
    })

@login_required
@admin_required
def user_toggle_active(request, pk):
    if request.method == "POST":
        user = get_object_or_404(User, pk=pk)
        was_active = user.is_active
        user.is_active = not user.is_active
        user.save()
        action = AuditLog.Action.USER_ACTIVATED if not was_active else AuditLog.Action.USER_DEACTIVATED
        log_action(
            user=request.user,
            obj=user,
            action=action,
            before={"is_active": was_active},
            after={"is_active": user.is_active},
        )
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"success": False}, status=405)

@login_required
@admin_required
def user_create(request):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(username=form.cleaned_data['username'], password=form.cleaned_data['password'], email=form.cleaned_data['email'],first_name=form.cleaned_data['first_name'],last_name=form.cleaned_data['last_name'])
            user.groups.add(form.cleaned_data['role'])
            log_action(
                user=request.user,
                obj=user,
                action=AuditLog.Action.USER_CREATED,
                before=None,
                after={
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.groups.first().name
                }
            )
            return JsonResponse({"success": True})
        elif is_ajax:
            return JsonResponse({"success": False, "errors": form.errors})
    elif is_ajax:
        return HttpResponseNotAllowed(["POST"])
    else:
        form = UserForm()
    return render(request, "core/user_create.html", {
        "form": form
    })

@login_required
@admin_required
def user_data(request, pk):
    user = get_object_or_404(User, pk=pk)
    group = user.groups.first()
    return JsonResponse({
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "group": group.id if group is not None else None,
    })

@login_required
@admin_required
def user_update(request, pk):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    user = get_object_or_404(User, pk=pk)
    before = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.groups.first().name if user.groups.exists() else None,
    }
    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.groups.clear()
            user.groups.add(form.cleaned_data['role'])
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            log_action(
                user=request.user,
                obj=user,
                action=AuditLog.Action.USER_UPDATED,
                before=before,
                after={
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.groups.first().name if user.groups.exists() else None,
                }
            )
            return JsonResponse({"success": True})
        elif is_ajax:
            return JsonResponse({"success": False, "errors": form.errors})
    elif is_ajax:
        return HttpResponseNotAllowed(["POST"])
    else:
        form = UserForm()
    return render(request, "core/user_update.html", {
        "user": user,
        "form": form
    })