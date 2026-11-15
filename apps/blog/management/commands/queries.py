from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.models import Model, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auths.models import User
from apps.blog.models import Post
from apps.blog.queries import QUERIES



PREVIEW_ROWS = 5
DATA_CHANGING_QUERIES = frozenset(range(40, 45))
SAMPLE_PAGE = 2
SAMPLE_DAYS=30
SAMPLE_DOMAIN="example.com"
SAMPLE_CATEGORY_SLUG="django"
SAMPLE_CATEGORY_SLUGS=["python", "django"]
SAMPLE_TAG_SLUG="orm"
SAMPLE_SECOND_TAG_SLUG="api"
SAMPLE_MIN_POSTS=5
SAMPLE_LAST_NAME_CHARS=3
SAMPLE_TAG_NAME="Django ORM"
SAMPLE_OLD_DAYS=180
SAMPLE_SOURCE_CATEGORY_SLUG="testing"
SAMPLE_TARGET_CATEGORY_SLUG="python"




def post_slug() -> str:
    """Slug of a post that exists in the database"""
    return Post.objects.values_list("slug", flat=True).first() or ""


def title_word()->str:
    """A word form title of published post"""
    title=Post.objects.values_list("title", flat=True).first() or ""
    return title.split()[0] if title else ""


def author_email()->str:
    """Email of an auhtor of post(upper case)"""
    email=(Post.objects.filter(status=Post.Status.PUBLISHED).values_list("author__email", flat=True).first())
    return (email or "").upper()


def newest_post_year()->int:
    """Year of newest post."""
    return Post.objects.order_by("-created_at").first().created_at.year


def newest_post_month()->int:
    """Month of newest post."""
    return Post.objects.order_by("-created_at").first().created_at.month


def start_date()-> date:
    """SAMPLE_DAYS days ago"""
    return (timezone.now()-timedelta(days=SAMPLE_DAYS)).date()

def end_date()-> date:
    """Today"""
    return timezone.now().date()


def user_full_name_part()->str:
    """Full anme of existing user"""
    user=User.objects.exclude(last_name="").first()
    if user is None:
        return ""
    return f"{user.first_name} {user.last_name[:SAMPLE_LAST_NAME_CHARS]}".lower()




QUERY_ARGUMENTS: dict[int, dict[str, Any]] = {
    4: {"slug": post_slug},
    7: {"page": SAMPLE_PAGE},
    8: {"word": title_word},
    9: {"domain":SAMPLE_DOMAIN},
    11: {"slugs": SAMPLE_CATEGORY_SLUGS},
    12: {"year": newest_post_year, "month":newest_post_month},
    13: {"days": SAMPLE_DAYS},
    14: {"start": start_date, "end": end_date},
    15: {"email": author_email},
    16: {"tag_slug": SAMPLE_TAG_SLUG},
    17: {"category_slug": SAMPLE_CATEGORY_SLUG},
    21: {"first_slug": SAMPLE_TAG_SLUG, "second_slug": SAMPLE_SECOND_TAG_SLUG},
    22: {"text": title_word},
    34: {"min_posts": SAMPLE_MIN_POSTS},
    37: {"text": user_full_name_part},
    40: {"name": SAMPLE_TAG_NAME},
    41: {"days": SAMPLE_OLD_DAYS},
    42: {"category_slug": SAMPLE_SOURCE_CATEGORY_SLUG, "tag_slug":SAMPLE_TAG_SLUG},
    43: {
        "source_slug": SAMPLE_SOURCE_CATEGORY_SLUG,
        "target_slug": SAMPLE_TARGET_CATEGORY_SLUG,
    },   
}



class Command(BaseCommand):
    help = "Run ORM queries and show the result and number of SQL queries"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--number", type=int, help="Run only this query")
        parser.add_argument(
            "--sql", action="store_true", help="Also print the SQL of each query"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        number: int | None = options["number"]

        if number is None:
            numbers = [n for n in sorted(QUERIES) if n not in DATA_CHANGING_QUERIES]
        elif number in QUERIES:
            numbers = [number]
        else:
            raise CommandError(
                f"Query {number} does not exist "
                f"(available: {min(QUERIES)}-{max(QUERIES)})."
            )

        for query_number in numbers:
            self._run_query(query_number, options["sql"])

    def _run_query(self, number: int, show_sql: bool) -> None:
        """Run one query, count its SQL and print the result"""
        function = QUERIES[number]
        arguments = self._resolve_arguments(number)

        annotations: list[str] = []
        with CaptureQueriesContext(connection) as context:
            result = function(**arguments)
            if isinstance(result, QuerySet):
                annotations = list(result.query.annotation_select)
                result = list(result)

        count = len(context.captured_queries)
        noun = "query" if count == 1 else "queries"
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"{number} {function.__name__} - {count} SQL {noun}"
            )
        )
        if show_sql:
            for captured in context.captured_queries:
                self.stdout.write(captured["sql"])
        self._write_result(result, annotations)
        self.stdout.write("")

    @staticmethod
    def _resolve_arguments(number: int) -> dict[str, Any]:
        """Sample arguments for a query. Functions are called to get the value"""
        arguments = QUERY_ARGUMENTS.get(number, {})
        return {
            name: value() if callable(value) else value
            for name, value in arguments.items()
        }

    def _write_result(self, result: Any, annotations: list[str]) -> None:
        """A list: first PREVIEW_ROWS rows and the total. Anything else: as it is"""
        if isinstance(result, list):
            for row in result[:PREVIEW_ROWS]:
                self.stdout.write(self._format_row(row, annotations))
            self.stdout.write(f"({len(result)} rows)")
        else:
            self.stdout.write(self._format_row(result, annotations))

    @staticmethod
    def _format_row(row: Any, annotations: list[str]) -> str:
        """Model object: its text plus the annotate() values. Others: str(row)"""
        if isinstance(row, Model) and annotations:
            extras = {name: getattr(row, name, None) for name in annotations}
            return f"{row} {extras}"
        return str(row)
