from django.urls import path
from . import views

urlpatterns = [
    path("resources/", views.resource_list, name="resource_list"),
    path("resources/<int:pk>/", views.resource_detail, name="resource_detail"),
    path("resources/<int:resource_pk>/grants/create/", views.grant_create, name="grant_create"),
    path("grants/<int:pk>/revoke", views.grant_revoke, name="grant_revoke"),
    path("users/", views.user_list, name="user_list"),
    path("resources/create/", views.resource_create, name="resource_create"),
    path("resources/<int:pk>/edit/", views.resource_update, name="resource_update"),
    path("resources/<int:pk>/delete/", views.resource_delete, name="resource_delete"),
    path("resources/<int:pk>/data/", views.resource_data, name="resource_data"),
]
