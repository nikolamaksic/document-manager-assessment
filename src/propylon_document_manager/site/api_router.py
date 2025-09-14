from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from propylon_document_manager.file_versions.api.views import FileVersionViewSet
from propylon_document_manager.users.api.views import CreateUserView


if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("file_versions", FileVersionViewSet)


app_name = "api"
urlpatterns = router.urls
