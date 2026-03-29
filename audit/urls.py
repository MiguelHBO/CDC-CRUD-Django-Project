from django.urls import path
from audit import views

urlpatterns = [
    path("", views.dashboard, name="audit_dashboard"),
    path("api/recent/", views.api_recent, name="audit_api_recent"),
]
