from rest_framework.pagination import PageNumberPagination

from apps.blog.queries import POSTS_PER_PAGE
class PostPagination(PageNumberPagination):
    page_size = POSTS_PER_PAGE
    