from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.auths.views import HeaderTokenRefreshView, UserViewSet

router = SimpleRouter(trailing_slash=False)
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("token/refresh", HeaderTokenRefreshView.as_view(), name="token-refresh"),
    *router.urls,
]