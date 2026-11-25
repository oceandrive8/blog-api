from django.db.models import Model
from django.db.models.functions import Lower
from django.core.cache import cache
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from apps.blog.mixins import PostLookupMixin
from apps.blog.models import Category, Comment, Post, Tag
from apps.blog.pagination import PostPagination
from apps.blog.permissions import IsAuthorOrStaffForDelete
from apps.blog.serializers import (
    CategorySerializer,
    CommentCreateSerializer,
    CommentSerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
    TagSerializer,
)
from apps.blog.tasks import send_new_comment_email
from apps.blog.utils import generate_unique_slug
from apps.mixins import ValidatedSerializerMixin


CACHE_TIMEOUT = 60 * 10
CATEGORIES_CACHE_KEY = "categories"
TAGS_CACHE_KEY = "tags"


class NameListViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    model: type[Model]
    serializer_class: type[BaseSerializer]
    cache_key: str

    def list(self, request: Request) -> Response:
        data = cache.get(self.cache_key)
        if data is None:
            queryset = self.model.objects.order_by(Lower("name"))
            serialized = self.serializer_class(queryset, many=True).data
            data = [dict(item) for item in serialized]
            cache.set(self.cache_key, data, CACHE_TIMEOUT)
        return Response(data)


class CategoryViewSet(NameListViewSet):
    model = Category
    serializer_class = CategorySerializer
    cache_key = CATEGORIES_CACHE_KEY

class TagViewSet(NameListViewSet):
    model = Tag
    serializer_class = TagSerializer
    cache_key = TAGS_CACHE_KEY


class PostViewSet(ValidatedSerializerMixin, PostLookupMixin, viewsets.ViewSet):
    lookup_value_regex = r"[0-9]{1,9}"

    def get_permissions(self) -> list:
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAuthenticated(), IsAuthorOrStaffForDelete()]

    def list(self, request: Request) -> Response:
        queryset = (
            self.get_post_queryset()
            .filter(status=Post.Status.PUBLISHED)
            .order_by("-created_at", "-id")
        )
        category_slug = request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        paginator = PostPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = PostListSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    def retrieve(self, request: Request, pk: str) -> Response:
        post = self.get_visible_post(request, pk)
        return Response(PostDetailSerializer(post).data)

    def _detail_response(self, pk: int, status_code):
        """Read the post agagin wiht its annotation and send the 'one post' format."""
        post = self.get_post_queryset().get(pk=pk)
        return Response(PostDetailSerializer(post).data, status=status_code)

    def create(self, request: Request) -> Response:
        serializer = self.get_valid_serializer(PostWriteSerializer, request.data)
        slug = generate_unique_slug(serializer.validated_data["title"])
        post = serializer.save(author=request.user, slug=slug)
        return self._detail_response(post.pk, status.HTTP_201_CREATED)

    def partial_update(self, request: Request, pk:str) -> Response:
        post = self.get_visible_post(request, pk)
        self.check_object_permissions(request, post)
        serializer =self.get_valid_serializer(
            PostWriteSerializer, request.data, instance=post, partial=True
        )
        serializer.save()
        return self._detail_response(post.pk, status.HTTP_200_OK)

    def destroy(self, request: Request, pk:str) -> Response:
        post = self.get_visible_post(request, pk)
        self.check_object_permissions(request, post)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request: Request, pk:str ) -> Response:
        post = self.get_published_post(pk)
        if request.method == "POST":
            return self._create_comment(request, post)
        return self._list_comments(post)

    def _list_comments(self, post: Post) -> Response:
        comments = (
            Comment.objects.filter(post=post)
            .select_related("author")
            .order_by("created_at", "id")
        )
        return Response(CommentSerializer(comments, many=True).data)

    def _create_comment(self, request: Request, post: Post) -> Response:
        serializer = self.get_valid_serializer(CommentCreateSerializer, request.data)
        comment = serializer.save(post=post, author=request.user)
        send_new_comment_email.delay(comment.id)
        return Response(
            CommentSerializer(comment).data, status=status.HTTP_201_CREATED
        )