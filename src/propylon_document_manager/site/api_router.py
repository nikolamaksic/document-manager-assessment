from django.conf import settings
from django.urls import path, re_path
from rest_framework.routers import DefaultRouter, SimpleRouter

from propylon_document_manager.file_versions.api.views import (
    FileVersionViewSet,
)
from propylon_document_manager.users.api.views import CreateUserView


if settings.DEBUG:
    router = DefaultRouter(trailing_slash=False)
else:
    router = SimpleRouter(trailing_slash=False)

documents_view = FileVersionViewSet.as_view({
    "get": "retrieve_document", 
    "post": "create_document_version", 
    "delete": "delete_document_version"})

documents_mine_view = FileVersionViewSet.as_view({"get": "list_available_files"})
documents_diff_view = FileVersionViewSet.as_view({"get": "diff_file_versions"})

urlpatterns = [
    path("documents/mine", documents_mine_view, name="documents-mine"),
    re_path(r"^documents/diff/(?P<path>.+)$", documents_diff_view, name="documents-diff"),
    re_path(r"^documents/(?P<path>.+)$", documents_view, name="documents"),
]
