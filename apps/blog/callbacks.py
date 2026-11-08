import json
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import HttpRequest
from django.urls import reverse

from apps.blog.models import Category, Comment, Post

LOCAL_ENV_ID = "local"  
STATUS_PUBLISHED = "published"
STATUS_DRAFT = "draft"
TOP_AUTHORS_LIMIT = 5
PERCENT = 100





def environment_callback(request: HttpRequest) -> list[str]:
    if settings.ENV_ID == LOCAL_ENV_ID:
        return ["Local", "warning"]  
    return ["Production", "danger"]  


def drafts_badge(request: HttpRequest) -> str:
    return str(Post.objects.filter(status=STATUS_DRAFT).count())


def is_superuser(request: HttpRequest) -> bool:
    return request.user.is_superuser


def all_posts_link(request: HttpRequest) -> str:
    return reverse("admin:blog_post_changelist")


def published_posts_link(request: HttpRequest) -> str:
    return f"{reverse('admin:blog_post_changelist')}?status__exact={STATUS_PUBLISHED}"


def draft_posts_link(request: HttpRequest) -> str:
    return f"{reverse('admin:blog_post_changelist')}?status__exact={STATUS_DRAFT}"





def _share(part: int, total: int) -> int:
    """Percent of `total` that `part` makes up; 0 when there is nothing."""
    return round(part / total * PERCENT) if total else 0


def dashboard_callback(
    request: HttpRequest, context: dict[str, Any]
) -> dict[str, Any]:
    user_model = get_user_model()
    published = Post.objects.filter(status=STATUS_PUBLISHED).count()
    drafts = Post.objects.filter(status=STATUS_DRAFT).count()
    total_posts = published + drafts

    categories = Category.objects.annotate(posts_count=Count("posts")).order_by("name")
    chart = {
        "labels": [category.name for category in categories],
        "datasets": [
            {
                "label": "Posts",
                "data": [category.posts_count for category in categories],
                "backgroundColor": "var(--color-primary-600)",
            }
        ],
    }

    top_authors = user_model.objects.annotate(posts_count=Count("posts")).order_by(
        "-posts_count"
    )[:TOP_AUTHORS_LIMIT]

    context.update(
        {
            "cards": [
                {"title": "Users", "value": user_model.objects.count()},
                {"title": "Published posts", "value": published},
                {"title": "Drafts", "value": drafts},
                {"title": "Comments", "value": Comment.objects.count()},
            ],
            "chart_data": json.dumps(chart),
            "authors_table": {
                "headers": ["Author", "Posts"],
                "rows": [
                    [author.get_full_name() or author.email, author.posts_count]
                    for author in top_authors
                ],
            },
            "progress": [
                {"title": "Published", "value": _share(published, total_posts)},
                {"title": "Drafts", "value": _share(drafts, total_posts)},
            ],
        }
    )
    return context