from django.db.models import Count, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.request import Request

from apps.blog.models import Post


class PostLookupMixin:
    def get_post_queryset(self) -> QuerySet:
        return (
            Post.objects
            .select_related("author", "category")
            .prefetch_related("tags")
            .annotate(comments_count=Count("comments"))
        )

    def get_visible_post(self, request: Request, pk: str) -> Post:
        """Published: for everyone.  Draft: it is onlt for author"""
        post = get_object_or_404(self.get_post_queryset(), pk=pk)
        if post.status == Post.Status.DRAFT and post.author_id != request.user.id:
            raise Http404
        return post

    def get_published_post(self, pk: str) -> Post:
        """For comments: a draft does not exist"""
        return get_object_or_404(Post, pk=pk, status=Post.Status.PUBLISHED)