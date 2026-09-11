from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from core.views import UserTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/vote/", include("votecount.urls")),
    # Auth/Account endpoints
    path(
        "api/vote/auth/jwt/create/",
        UserTokenObtainPairView.as_view(),
        name="jwt-create",
    ),
    path("api/vote/auth/", include("djoser.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
