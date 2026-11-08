from django.contrib import admin, messages
from django.db import models
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.text import Truncator
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.sections import TableSection

from apps.blog.models import Category, Comment, Post, Tag

STATUS_PUBLISHED = "published"
STATUS_DRAFT = "draft"
BODY_PREVIEW_CHARS = 60
INLINE_COMMENTS_PER_PAGE = 10


# ---------- Category ----------

class CategoryPostsSection(TableSection):
    verbose_name = "Posts"
    related_name = "posts"
    fields = ["title", "status", "created_at"]


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "posts_total")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_sections = [CategoryPostsSection]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(posts_count=Count("posts"))

    @display(description="Posts", ordering="posts_count")
    def posts_total(self, obj) -> int:
        return obj.posts_count


# ---------- Tag ----------

@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug", "posts_total")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(posts_count=Count("posts"))

    @display(description="Posts", ordering="posts_count")
    def posts_total(self, obj) -> int:
        return obj.posts_count


# ---------- Comment ----------

@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("post_title", "author", "short_body", "created_at")
    list_select_related = ("post", "author")
    list_filter = [
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    ]
    list_filter_submit = True
    search_fields = ("body", "author__email", "post__title")
    autocomplete_fields = ("post", "author")

    @display(description="Post", ordering="post__title")
    def post_title(self, obj) -> str:
        return obj.post.title

    @display(description="Comment")
    def short_body(self, obj) -> str:
        return Truncator(obj.body).chars(BODY_PREVIEW_CHARS)


# ---------- Post ----------

class PostCommentsSection(TableSection):
    verbose_name = "Comments"
    related_name = "comments"
    fields = ["author", "body", "created_at"]


class CommentInline(TabularInline):
    model = Comment
    extra = 0
    tab = True
    per_page = INLINE_COMMENTS_PER_PAGE
    autocomplete_fields = ("author",)


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = (
        "header", "status_label", "category", "tags_dropdown", "comments_total", "created_at",
    )
    list_filter = [
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    ]
    list_filter_submit = True
    search_fields = ("title", "body", "author__email")
    list_select_related = ("author", "category")
    list_sections = [PostCommentsSection]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author", "category", "tags")
    readonly_fields = ("created_at", "updated_at")
    warn_unsaved_form = True
    formfield_overrides = {models.TextField: {"widget": WysiwygWidget}}
    inlines = [CommentInline]

    fieldsets = (
        ("Content", {"fields": ("title", "slug", "body"), "classes": ["tab"]}),
        ("Classification", {"fields": ("category", "tags", "status"), "classes": ["tab"]}),
        ("Meta", {"fields": ("author", "created_at", "updated_at"), "classes": ["tab"]}),
    )

    actions = ["publish_selected", "move_to_drafts"]
    actions_row = ["toggle_publish"]
    actions_list = ["publish_all_drafts"]
    actions_detail = ["open_comments"]
    actions_submit_line = ["save_and_publish"]

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .annotate(comments_count=Count("comments", distinct=True))
            .prefetch_related("tags")
        )

    # --- columns ---

    @display(description="Post", header=True)
    def header(self, obj):
        return [obj.title, obj.author.email]

    @display(description="Status", label={STATUS_PUBLISHED: "success", STATUS_DRAFT: "warning"})
    def status_label(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="Tags", dropdown=True)
    def tags_dropdown(self, obj):
        tags = obj.tags.all()  # uses prefetch_related, no extra query
        return {"title": f"{len(tags)} tags", "items": [{"title": tag.name} for tag in tags]}

    @display(description="Comments", ordering="comments_count")
    def comments_total(self, obj) -> int:
        return obj.comments_count

    # --- actions ---

    @action(description="Publish selected", permissions=["change"])
    def publish_selected(self, request, queryset):
        updated = queryset.update(status=STATUS_PUBLISHED)
        self.message_user(request, f"{updated} post(s) published.")

    @action(description="Move to drafts", permissions=["change"])
    def move_to_drafts(self, request, queryset):
        updated = queryset.update(status=STATUS_DRAFT)
        self.message_user(request, f"{updated} post(s) moved to drafts.")

    @action(description="Publish / unpublish", url_path="toggle-publish")
    def toggle_publish(self, request, object_id):
        post = get_object_or_404(Post, pk=object_id)
        post.status = STATUS_DRAFT if post.status == STATUS_PUBLISHED else STATUS_PUBLISHED
        post.save(update_fields=["status"])
        return redirect(reverse("admin:blog_post_changelist"))

    @action(description="Publish all drafts", url_path="publish-all-drafts")
    def publish_all_drafts(self, request):
        updated = Post.objects.filter(status=STATUS_DRAFT).update(status=STATUS_PUBLISHED)
        messages.success(request, f"{updated} draft(s) published.")
        return redirect(reverse("admin:blog_post_changelist"))

    @action(description="Open comments", url_path="open-comments")
    def open_comments(self, request, object_id):
        return redirect(f"{reverse('admin:blog_comment_changelist')}?post__id__exact={object_id}")

    @action(description="Save & publish")
    def save_and_publish(self, request, obj):
        obj.status = STATUS_PUBLISHED  # runs after the object is saved
        obj.save(update_fields=["status"]) 
