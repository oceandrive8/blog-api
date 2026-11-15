from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import (F, Q, QuerySet, Value, Max, Min, Count, Avg, Case, When , CharField, Prefetch, OuterRef, Subquery, Exists)
from django.db.models.functions import Coalesce, Concat, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

from apps.auths.models import User
from apps.blog.models import Category, Post, Comment, Tag



NEWEST_POST_LIMIT=5
POSTS_PER_PAGE=10
EDITED_AFTER=timedelta(hours=1)
UNCATEGORIZED="Uncategorized"
AVERAGE_DIGITS=2
TOP_AUTHORS_LIMIT=5
HOT_COMMENTS=10
POPULARITY_HOT="hot"
NORMAL_COMMENTS=3
POPULARITY_NORMAL="normal"
POPULARITY_QUIET="quiet"
SAME_CATEGORY_MESSAGE="Source and target category must be different"
FEED_LIMIT=50
FEED_SEPERATOR= " | "
NEWEST_TAGGED_LIMIT=20


#----------------------------------------
#Level 1 — First Queries
#----------------------------------------



def categories_by_name()->QuerySet[Category]:
    """All categories, sorted by name from a to z"""
    return Category.objects.order_by("name")



def published_posts()->QuerySet[Post]:
    """Published posts, new one pop up first"""
    return Post.objects.filter(status=Post.Status.PUBLISHED).order_by("-created_at")



def newest_published_posts()->QuerySet[Post]:
    """The newest published posts"""
    return published_posts()[:NEWEST_POST_LIMIT]



def post_by_slug(slug: str)-> Post | None:
    """posts with slug, or none if there is no such post"""
    return Post.objects.filter(slug=slug).first()



def active_users_count()-> int:
    """Number of active users, but staff users not counted """
    return User.objects.filter(is_active=True, is_staff=False).count()



def has_drafts()-> bool:
    """True if there is at least one draft post."""
    return Post.objects.filter(status=Post.Status.DRAFT).exists()



def published_posts_page(page: int) -> QuerySet[Post]:
    """One page of published posts, newest first. 10 posts per page: page 1 is posts 1–10, page 2 is posts 11–20."""
    if page<1:
        raise ValueError("page must be 1 or greater")
    offset=(page-1)*POSTS_PER_PAGE
    return published_posts()[offset: offset + POSTS_PER_PAGE]










#----------------------------------------
#Level 2 — Field Lookups
#----------------------------------------


def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """Posts whose title contains word. Letter case does not matter."""
    return Post.objects.filter(title__icontains=word)



def users_with_email_domain(domain: str) -> QuerySet[User]:
    """Users whose email ends with @ + domain, for example domain="example.com"""
    return User.objects.filter(email__iendswith=f"@{domain}")



def posts_without_category() -> QuerySet[Post]:
    """Posts that have no category."""
    return Post.objects.filter(category__isnull=True)



def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """Categories whose slug is in the list slugs."""
    return Category.objects.filter(slug__in=slugs)



def posts_in_month(year: int, month: int) -> QuerySet[Post]:  
    """Posts created in this month of this year."""
    return Post.objects.filter(created_at__year=year, created_at__month=month)


def posts_last_days(days: int) -> QuerySet[Post]: 
    """Posts created in the last days days."""
    return Post.objects.filter(created_at__gte=timezone.now() - timedelta(days=days))



def posts_between(start: date, end: date) -> QuerySet[Post]:
    """Posts created from start to end. Posts from the start day and from the end day are both included."""
    return Post.objects.filter(created_at__date__range=(start, end))









#----------------------------------------
#Level 3 — Queries Across Relations
#----------------------------------------

def author_published_posts(email: str) -> QuerySet[Post]:
    """Published posts of the author with this email. Letter case of the email does not matter."""
    return Post.objects.filter(author__email__iexact=email, status=Post.Status.PUBLISHED)



def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """Posts that have the tag with this slug."""
    return Post.objects.filter(tags__slug=tag_slug)


def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """Comments on posts of the category with this slug."""
    return Comment.objects.filter(post__category__slug=category_slug)


def users_with_published_posts() -> QuerySet[User]: 
    """Users who have at least one published post. Every user appears once."""
    return User.objects.filter(posts__status=Post.Status.PUBLISHED).distinct()


def posts_without_tags() -> QuerySet[Post]:
    """Posts that have no tags. """
    return Post.objects.filter(tags__isnull=True)


def users_without_comments() -> QuerySet[User]: 
    """Users who have never written a comment."""
    return User.objects.filter(comments__isnull=True)



def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]: 
    """Posts that have both tags. A post with only one of them is not included."""
    return Post.objects.filter(tags__slug=first_slug).filter(tags__slug=second_slug)











#----------------------------------------
#Level 4 — Q and F
#----------------------------------------


def search_posts(text: str) -> QuerySet[Post]: 
    """Posts that have text in the title or in the body. Letter case does not matter."""
    return Post.objects.filter(Q(title__icontains=text) | Q(body__icontains=text))


def published_posts_missing_info() -> QuerySet[Post]: 
    """Published posts that have no category or no tags. Every post appears once."""
    return Post.objects.filter(Q(category__isnull=True) | Q(tags__isnull=True), status=Post.Status.PUBLISHED,).distinct()



def edited_posts() -> QuerySet[Post]: 
    """Posts that were edited more than 1 hour after they were created."""
    return Post.objects.filter(updated_at__gt=F("created_at")+ EDITED_AFTER)



def comments_by_post_author() -> QuerySet[Comment]:
    """Comments that the author of the post wrote under their own post."""
    return Comment.objects.filter(author=F("post__author"))


def comments_before_post() -> QuerySet[Comment]: 
    """Comments created before their post. Must be empty if Part 1 is correct"""
    return Comment.objects.filter(created_at__lt=F("post__created_at"))












#----------------------------------------
#Level 5 — values and values_list
#----------------------------------------

def published_authors_emails() -> list[str]: 
    """Emails of authors who have published posts. Unique, sorted A → Z. A plain list of strings. """
    return list(Post.objects.filter(status=Post.Status.PUBLISHED)
                .values_list("author__email", flat=True)
                .distinct()
                .order_by("author__email")
                )



def published_posts_overview() -> list[dict[str, Any]]: 
    """One dict for each published post with exactly three keys: title, author_email, category_name.
    If a post has no category, category_name is "Uncategorized""" 
    return list(Post.objects.filter(status=Post.Status.PUBLISHED)
                .order_by("-created_at")
                .values("title", author_email=F("author__email"), 
                        category_name=Coalesce("category__name", Value(UNCATEGORIZED))))









#----------------------------------------
#Level 6 — aggregate
#----------------------------------------


def posts_stats() -> dict[str, Any]:
    """ | In one SQL query: "the number of all posts, of published posts and of drafts, 
    and the date of the first and of the last post. 
    Keys: total, published, drafts, first_post_at, last_post_at. """
    return Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.Status.DRAFT)),
        first_post_at=Min("created_at"),
        last_post_at=Max("created_at"),
    )



def average_comments_per_post() -> float:  
    """The average number of comments on a published post, rounded to 2 digits after the point. 
    Posts with 0 comments count too. If there are no posts, return 0.0.""" 
    result=(Post.objects.filter(status=Post.Status.PUBLISHED)
            .annotate(comment_count=Count("comments"))
            .aggregate(average=Avg("comment_count", default=0.0)))
    return round(result["average"], AVERAGE_DIGITS)





#----------------------------------------
#Level 7 — annotate
#----------------------------------------

def categories_with_post_count() -> QuerySet[Category]:  
    """Every category with post_count. Most posts first. Same count → sort by name."""
    return Category.objects.annotate(
        post_count=Count("posts")
        ).order_by("-post_count", "name")



def categories_with_published_count() -> QuerySet[Category]: 
    """Every category with published_count, the number of its published posts. 
    Categories with 0 published posts must be in the result too. """
    return Category.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
                                     ).order_by("name")



def top_authors() -> QuerySet[User]:
    """The top 5 users by number of published posts, with published_count. """
    return User.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    ).order_by("-published_count", "email")[:TOP_AUTHORS_LIMIT]


def popular_tags(min_posts: int) -> QuerySet[Tag]: 
    """Tags used in at least min_posts posts, with post_count."""
    return (
        Tag.objects.annotate(post_count=Count("posts"))
        .filter(post_count__gte=min_posts)
        .order_by("-post_count", "name")
    )


def posts_per_status() -> list[dict[str, Any]]: 
    """The number of posts for each status: [{"status": "draft", "count": 30}, {"status": "published", "count": 70}]."""
    return list(
        Post.objects.values("status").annotate(count=Count("id")).order_by("status")
    )


def users_activity() -> QuerySet[User]: 
    """Every user with post_count and comment_count. Both numbers must be correct."""
    return User.objects.annotate(
        post_count=Count("posts", distinct=True),
        comment_count=Count("comments", distinct=True),
        ).order_by("email")







#----------------------------------------
#Level 8 — Database Functions and Conditions
#----------------------------------------

def search_users_by_full_name(text: str) -> QuerySet[User]: 
    """Users whose full name ("First Last") contains text. Letter case does not matter. 
    A search for "john smi" finds John Smith. Every user has full_name."""
    return User.objects.annotate(
        full_name=Concat("first_name", Value(" "), "last_name")
    ).filter(full_name__icontains=text)

def published_posts_per_month() -> list[dict[str, Any]]:
    """The number of published posts in each month: [{"month": ..., "count": 7}, ...], oldest month first. """
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

def posts_with_popularity() -> QuerySet[Post]: 
    """Every post with comment_count and popularity: "hot" for 10 comments or more, "normal" for 3 or more,
      "quiet" for less."""
    return (
        Post.objects.annotate(comment_count=Count("comments"))
        .annotate(
            popularity=Case(
                When(comment_count__gte=HOT_COMMENTS, then=Value(POPULARITY_HOT)),
                When(comment_count__gte=NORMAL_COMMENTS, then=Value(POPULARITY_NORMAL)),
                default=Value(POPULARITY_QUIET),
                output_field=CharField(),
            )
        )
        .order_by("-created_at")
    )







#----------------------------------------
#Level 9 — Changing Data
#----------------------------------------

def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    """Return the tag with this name. Create it (slug from the name) if it does not exist. 
    The bool is True if the tag was created. Calling it twice must not create a second tag. """
    return Tag.objects.get_or_create(slug=slugify(name), defaults={"name": name})


def publish_old_drafts(days: int) -> int: 
    """ All drafts older than days days become published, with one SQL query. Return how many posts changed"""
    now=timezone.now()
    return Post.objects.filter(
        status=Post.Status.DRAFT,
        created_at__lt=now-timedelta(days=days),
    ).update(status=Post.Status.PUBLISHED, updated_at=now)



def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    """Add the tag to every post of the category. A post that already has this tag must not get it twice.
      Return the number of posts in the category."""
    tag=Tag.objects.get(slug=tag_slug)
    posts=list(Post.objects.filter(category__slug=category_slug))
    tag.posts.add(*posts)
    return len(posts)



def merge_categories(source_slug: str, target_slug: str) -> int:
    """Move all posts of the source category to the target category, then delete the source category. 
    Return how many posts moved."""
    if source_slug==target_slug:
        raise ValueError(SAME_CATEGORY_MESSAGE)
    with transaction.atomic():
        source=Category.objects.get(slug=source_slug)
        target=Category.objects.get(slug=target_slug)
        moved=Post.objects.filter(category=source).update(category=target)
        source.delete()
    return moved



def delete_inactive_users_comments() -> int:
    """Delete all comments written by inactive users. Return how many were deleted."""
    _, deleted_per_model=Comment.objects.filter(author__is_active=False).delete()
    return deleted_per_model.get(Comment._meta.label, 0)








#----------------------------------------
#Level 10 — select_related and prefetch_related
#----------------------------------------


def published_feed() -> list[str]:
    """The 50 newest published posts as lines "title \| author email \| category name" 
    (Uncategorized if there is no category). Exactly 1 SQL query"""
    posts=(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .select_related("author", "category")
        .order_by("-created_at")[:FEED_LIMIT]
    )
    return [
        FEED_SEPERATOR.join(
            (post.title, post.author.email, post.category.name if post.category else UNCATEGORIZED)
        )
        for post in posts
    ]


def newest_posts_with_tags() -> list[str]:
    """The 20 newest posts as lines "title: tag1, tag2". At most 2 SQL queries. """
    posts=Post.objects.prefetch_related(
        Prefetch("tags", queryset=Tag.objects.order_by("name"))
    ).order_by("-created_at")[:NEWEST_TAGGED_LIMIT]
    return [
        f"{post.title} : {', '.join(tag.name for tag in post.tags.all())}"
        for post in posts
    ]



def categories_with_published_posts() -> dict[str, list[str]]:
    """{category name: [titles of its published posts, newest first]} for every category. 
    No drafts. At most 2 SQL queries."""
    categories=Category.objects.order_by("name").prefetch_related(
        Prefetch(
            "posts",
            queryset=Post.objects.filter(status=Post.Status.PUBLISHED).order_by(
                "-created_at"
            ),
            to_attr="published_posts",
        )
    )
    return {
        category.name: [post.title for post in category.published_posts]
        for category in categories
        }






#----------------------------------------
#Level 11 — Subquery and Exists
#----------------------------------------

def posts_with_last_comment() -> QuerySet[Post]:
    """Published posts. Each has last_comment: the body of its newest comment (None if there are no comments)."""
    newest_comment=(
        Comment.objects.filter(post=OuterRef("pk"))
        .order_by("-created_at", "-id")
        .values("body")[:1]
    )
    return (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(last_comment=Subquery(newest_comment))
        .order_by("-created_at")
    )


def posts_with_staff_comments() -> QuerySet[Post]:
    """Posts with at least one comment from a staff user. Use Exists, not distinct(). """
    staff_comments=Comment.objects.filter(post=OuterRef("pk"), author__is_staff=True)
    return Post.objects.filter(Exists(staff_comments)).order_by("-created_at")



def users_with_draft_as_latest_post() -> QuerySet[User]:
    """Users whose newest post is a draft. Each user has latest_post_status. """
    latest_post_status=(
        Post.objects.filter(author=OuterRef("pk"))
        .order_by("-created_at", "-id")
        .values("status")[:1]
    )
    return User.objects.annotate(
        latest_post_status=Subquery(latest_post_status)
    ).filter(latest_post_status=Post.Status.DRAFT)















QUERIES: dict[int, Callable[..., Any]]={
    1: categories_by_name, 
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
    8: posts_with_word_in_title,
    9: users_with_email_domain,
    10: posts_without_category,
    11: categories_by_slugs,
    12: posts_in_month,
    13: posts_last_days,
    14: posts_between,
    15: author_published_posts,
    16: posts_with_tag,
    17: comments_in_category,
    18: users_with_published_posts,
    19: posts_without_tags,
    20: users_without_comments,
    21: posts_with_both_tags,
    22: search_posts,
    23: published_posts_missing_info,
    24: edited_posts,
    25: comments_by_post_author,
    26: comments_before_post,
    27: published_authors_emails,
    28: published_posts_overview,
    29: posts_stats,
    30: average_comments_per_post,
    31: categories_with_post_count,
    32: categories_with_published_count,
    33: top_authors,
    34: popular_tags,
    35: posts_per_status,
    36: users_activity,
    37: search_users_by_full_name,
    38: published_posts_per_month,
    39: posts_with_popularity,
    40: get_or_create_tag,
    41: publish_old_drafts,
    42: tag_category_posts,
    43: merge_categories,
    44: delete_inactive_users_comments,
    45: published_feed,
    46: newest_posts_with_tags,
    47: categories_with_published_posts,
    48: posts_with_last_comment,
    49: posts_with_staff_comments,
    50: users_with_draft_as_latest_post,
}

