from rest_framework.routers import SimpleRouter

from apps.blog.views import CategoryViewSet, PostViewSet, TagViewSet

router = SimpleRouter(trailing_slash=False)
router.register("categories", CategoryViewSet, basename="category")
router.register("tags", TagViewSet, basename="tag")
router.register("posts", PostViewSet, basename="post")

urlpatterns = router.urls