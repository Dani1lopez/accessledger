from contextlib import contextmanager

from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.http import require_POST
from core.decorators import admin_required
from core.forms import AccessGrantForm, ResourceForm, UserForm, UserCreateForm
from core.permissions import user_can_modify_resource
from core.utils.snapshots import resource_snapshot, grant_snapshot, user_role
from .models import AccessGrant, Resource, Profile, AuditLog
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from .utils import log_action

PAGE_SIZE = 20


def _paginate(request, qs):
    """Wrap a queryset in a Paginator and return (page_obj, paginator).

    Uses ``paginator.get_page()`` so out-of-range and non-integer ``?page=``
    values fall back to the last valid page (or page 1) without 404s.
    """
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return page_obj, paginator


def _is_ajax(request) -> bool:
    """Return True if the request was issued via XHR.

    Wraps the X-Requested-With check that was inlined at 6 view sites
    (74, 107, 191, 200, 369, 422). Single source of truth for the
    'is this an AJAX call?' question.
    """
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _snapshot_for(obj) -> dict | None:
    """Return the right snapshot dict for ``obj``, or None for unknown types."""
    if isinstance(obj, Resource):
        return resource_snapshot(obj)
    if isinstance(obj, AccessGrant):
        return grant_snapshot(obj)
    return None


@contextmanager
def _audit(action, *, user, obj, before=None):
    """Context manager that emits an ``AuditLog`` row on successful exit.

    On exception the atomic block rolls back and no log row is written.
    The view keeps its explicit ``form.save()`` + ``user.save()`` lines
    inside the block, so the audit row only lands when the mutation
    fully commits. The ``after`` snapshot uses ``_snapshot_for(obj)``
    so each call site stays type-driven.

    Usage:
        with _audit(action=AuditLog.Action.USER_UPDATED,
                    user=request.user, obj=user, before=before):
            user.save()
    """
    with transaction.atomic():
        yield
        log_action(
            user=user,
            action=action,
            obj=obj,
            before=before,
            after=_snapshot_for(obj),
        )


@login_required
@permission_required("core.view_resource", raise_exception=True)
def resource_list(request):
    resources = Resource.objects.all().order_by("name")
    page_obj, paginator = _paginate(request, resources)
    if request.htmx:
        template = "core/_resource_table.html"
    else:
        template = "core/resource_list.html"
    return render(
        request,
        template,
        {
            "page_obj": page_obj,
            "paginator": paginator,
            "form": ResourceForm(),
            "page_url_name": "resource_list",
        },
    )


@login_required
@permission_required("core.view_resource", raise_exception=True)
def resource_detail(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    grants = (
        AccessGrant.objects.filter(resource=resource)
        .select_related("user")
        .order_by("status", "-end_at")
    )
    return render(
        request,
        "core/resource_detail.html",
        {
            "resource": resource,
            "grants": grants,
            "can_modify": user_can_modify_resource(request.user, resource),
        },
    )


@login_required
@permission_required("core.add_resource", raise_exception=True)
@require_POST
def resource_create(request):
    is_ajax = _is_ajax(request)

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
                after=resource_snapshot(resource),
            )
            return (
                JsonResponse({"success": True})
                if is_ajax
                else redirect("resource_list")
            )
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
    is_ajax = _is_ajax(request)
    resource = get_object_or_404(Resource, pk=pk)
    if not user_can_modify_resource(request.user, resource):
        raise PermissionDenied
    before = resource_snapshot(resource)
    if request.method == "POST":
        form = ResourceForm(request.POST, instance=resource)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.save()
            log_action(
                user=request.user,
                action=AuditLog.Action.RESOURCE_UPDATED,
                obj=resource,
                before=before,
                after=resource_snapshot(resource),
            )
            return (
                JsonResponse({"success": True})
                if is_ajax
                else redirect("resource_list")
            )
        elif is_ajax:
            return JsonResponse({"success": False, "errors": form.errors})
    elif is_ajax:
        return HttpResponseNotAllowed(["POST"])
    else:
        form = ResourceForm(instance=resource)
    return render(
        request, "core/resource_update.html", {"resource": resource, "form": form}
    )


@login_required
@permission_required("core.change_resource", raise_exception=True)
def resource_data(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    if not user_can_modify_resource(request.user, resource):
        raise PermissionDenied
    return JsonResponse(resource_snapshot(resource))


@login_required
@permission_required("core.delete_resource", raise_exception=True)
@require_POST
def resource_delete(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    if not user_can_modify_resource(request.user, resource):
        raise PermissionDenied
    if request.method == "POST":
        before = resource_snapshot(resource)
        log_action(
            user=request.user,
            action=AuditLog.Action.RESOURCE_DELETED,
            obj=resource,
            before=before,
            after=None,
        )
        resource.delete()
        is_ajax = _is_ajax(request)
        return JsonResponse({"success": True}) if is_ajax else redirect("resource_list")
    else:
        return render(request, "core/resource_delete.html", {"resource": resource})


@login_required
@permission_required("core.can_grant_access", raise_exception=True)
def grant_create(request, resource_pk):
    is_ajax = _is_ajax(request)
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
                after=grant_snapshot(grant),
            )
            return (
                JsonResponse({"success": True})
                if is_ajax
                else redirect("resource_detail", pk=resource_pk)
            )
        elif is_ajax:
            return JsonResponse({"success": False, "errors": form.errors})
    elif is_ajax:
        return HttpResponseNotAllowed(["POST"])
    else:
        form = AccessGrantForm()
    return render(
        request,
        "core/grant_create.html",
        {
            "resource": resource,
            "form": form,
        },
    )


@login_required
@permission_required("core.can_revoke_access", raise_exception=True)
@require_POST
def grant_revoke(request, pk):
    grant = get_object_or_404(AccessGrant, pk=pk)
    before = grant_snapshot(grant)
    grant.status = AccessGrant.Status.REVOKED
    grant.save()
    after = grant_snapshot(grant)
    log_action(
        user=request.user,
        action=AuditLog.Action.GRANT_REVOKED,
        obj=grant,
        before=before,
        after=after,
    )
    return redirect("resource_detail", pk=grant.resource.pk)


@login_required
@permission_required("core.can_grant_access", raise_exception=True)
def user_list(request):
    user = User.objects.values("id", "username").order_by("username")
    return JsonResponse({"users": list(user)})


class CustomPasswordChangeView(PasswordChangeView):
    success_url = reverse_lazy("resource_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.conf import settings
        context["admin_email"] = settings.ADMIN_EMAIL
        return context

    def form_valid(self, form):
        self.request.user.profile.must_change_password = False
        self.request.user.profile.save()
        log_action(self.request.user, AuditLog.Action.PASSWORD_CHANGED, self.request.user)
        return super().form_valid(form)


@login_required
def user_profile(request):
    user = request.user
    if request.htmx:
        template = "core/_user_profile.html"
    else:
        template = "core/user_profile.html"
    return render(
        request,
        template,
        {
            "user": user,
        },
    )


@login_required
@admin_required
def user_management(request):
    users = User.objects.all().prefetch_related("groups").order_by("id")
    page_obj, paginator = _paginate(request, users)
    groups = Group.objects.all()
    if request.htmx:
        template = "core/_user_management.html"
    else:
        template = "core/user_management.html"
    return render(
        request,
        template,
        {
            "page_obj": page_obj,
            "paginator": paginator,
            "groups": groups,
            "page_url_name": "user_management",
        },
    )


@login_required
@admin_required
def user_toggle_active(request, pk):
    if request.method == "POST":
        user = get_object_or_404(User, pk=pk)
        was_active = user.is_active
        user.is_active = not user.is_active
        user.save()
        action = (
            AuditLog.Action.USER_ACTIVATED
            if not was_active
            else AuditLog.Action.USER_DEACTIVATED
        )
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
    is_ajax = _is_ajax(request)
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
                email=form.cleaned_data["email"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
            )
            user.groups.add(form.cleaned_data["role"])
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
                    "role": user_role(user),
                },
            )
            return JsonResponse({"success": True})
        elif is_ajax:
            return JsonResponse({"success": False, "errors": form.errors})
    elif is_ajax:
        return HttpResponseNotAllowed(["POST"])
    else:
        return redirect("user_management")


@login_required
@admin_required
def user_data(request, pk):
    user = get_object_or_404(User, pk=pk)
    group = user.groups.first()
    return JsonResponse(
        {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "group": group.id if group is not None else None,
        }
    )


@login_required
@admin_required
def user_update(request, pk):
    is_ajax = _is_ajax(request)
    user = get_object_or_404(User, pk=pk)
    before = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user_role(user),
    }
    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.groups.clear()
            user.groups.add(form.cleaned_data["role"])
            password = form.cleaned_data.get("password")
            if password:
                user.set_password(password)
                # Force the user to change this admin-set password on next login.
                profile, _ = Profile.objects.get_or_create(
                    user=user, defaults={"must_change_password": True}
                )
                profile.must_change_password = True
                profile.save()
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
                    "role": user_role(user),
                },
            )
            return JsonResponse({"success": True})
        elif is_ajax:
            return JsonResponse({"success": False, "errors": form.errors})
    elif is_ajax:
        return HttpResponseNotAllowed(["POST"])
    else:
        return redirect("user_management")


@login_required
@admin_required
def audit_log(request):
    audit = AuditLog.objects.all().order_by("-timestamp").select_related("user")
    page_obj, paginator = _paginate(request, audit)
    if request.htmx:
        template = "core/_audit_log.html"
    else:
        template = "core/audit_log.html"
    return render(
        request,
        template,
        {
            "page_obj": page_obj,
            "paginator": paginator,
            "page_url_name": "audit_log",
        },
    )
