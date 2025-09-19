from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from rest_framework.authtoken.views import obtain_auth_token
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from propylon_document_manager.users.api.views import CreateUserView
import propylon_document_manager.site.api_router as router

# API URLS
urlpatterns = [
    path('admin/', admin.site.urls),
    # API base url
    path("api/", include("propylon_document_manager.site.api_router")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    # DRF auth token
    path("api-auth/", include("rest_framework.urls")),
    path("auth-token/", obtain_auth_token),

    # User APIs
    # path("api/user/", include(("propylon_document_manager.users.api.urls"), namespace="users")),

    *router.urlpatterns,

]

if settings.DEBUG:
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
