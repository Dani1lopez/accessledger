from django.shortcuts import render
from django.contrib.auth.decorators import permission_required, login_required
from .models import Resource

@login_required
@permission_required("core.view_resource", raise_exception=True)
def resource_list(request):
    resources = Resource.objects.all().order_by("name")
    return render(request, "core/resource_list.html", {"resources": resources})

