from django.urls import path
from . import views

urlpatterns = [
    path("resources/", views.resource_list, name="resource_list"),
    path("resources/<int:pk>/", views.resource_detail, name="resource_detail")
]
