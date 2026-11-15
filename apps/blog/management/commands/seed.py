import random
import time
from datetime import datetime,timedelta
from typing import Any


from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand,CommandError, CommandParser
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker

from apps.blog.models import Category, Comment, Post, Tag

DEFAULT_USERS=20
DEFAULT_POSTS=100
DEFAULT_COMMENTS=500
SEED_PASSWORD="OceanD12345!"
EMAIL_DOMAIN="example.com"
INACTIVE_RATIO=0.15
STAFF_RATIO=0.1
PUBLISHED_RATIO=0.7
NO_CATEGORY_RATIO=0.1
MAX_TAGS_PER_POST=5
BODY_PARAGRAPHS=5
TITLE_WORDS=6
MIN_COMMENT_SENTENCES=1
MAX_COMMENT_SENTENCES=3
BATCH_SIZE=500


POST_AGE_DAYS=365
EDITED_RATIO=0.3
MIN_EDIT_DELAY_DAYS=1
MAX_EDIT_DELAY_DAYS=30


CATEGORY_NAMES=["Python", "Django", "DevOps", "Testing", "Frontend", 
                "Databases", "UI/UX", "Cybersecurity"]

TAG_NAMES=["rest", "orm", "react", "django", "api",
           "ethic", "git", "auth", "docker", "postgres", "firewall", 
           "deployment", "test", "migrations", "logging", "angular", "sdg", 
           "cryptography", "netacad", "networks"]

User=get_user_model()

def unique_slug(base:str, used:set[str])->str:
    """Return base, base-2, base-3 posts if titles are same"""
    base=base or "post"
    slug, number=base,2
    while slug in used:
        slug=f"{base}-{number}"
        number+=1
    used.add(slug)
    return slug

def random_moment(start:datetime, end: datetime)->datetime:
    seconds=int((end-start).total_seconds())
    return start+timedelta(seconds=random.randint(0, max(seconds, 0)))

class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser)->None:
        parser.add_argument("--users", type=int, default=DEFAULT_USERS, help="Number of users to create")
        parser.add_argument("--posts", type=int, default=DEFAULT_POSTS, help="Number of posts to create")
        parser.add_argument("--comments",type=int, default=DEFAULT_COMMENTS, help="Number of comments to create")
        parser.add_argument("--clear", action="store_true", help="Delete existing data before seeding")

    def handle(self, *args: Any, **options: Any) -> None: 
        users_count: int = options["users"] 
        posts_count: int =options["posts"]
        comments_count: int=options["comments"]

        for name, value in (("users", users_count), ("posts", posts_count), ("comments", comments_count)):
            if value<0:
                raise CommandError(f"--{name} must not be negative (got {value}).")

        started=time.perf_counter()
        self.fake=Faker()
        now=timezone.now()

        with transaction.atomic():
            if options["clear"]:
                self._clear()
            users_created=self._create_users(users_count)
            categories_created=self._create_categories()
            tags_created=self._create_tags()


            user_ids=list(User.objects.values_list("id", flat=True))
            if (posts_count or comments_count) and not user_ids:
                raise CommandError("Posts and comments are required but there is no users. use --users")

                
            posts=self._create_posts(posts_count, user_ids, now)

            #Published posts of this one taking from memory
            published_posts=[p for p in posts if p.status==Post.Status.PUBLISHED]
            if comments_count and not published_posts:
                #Fallback:this run made no published posts 
                #no use published posts that are alreday exist in db
                published_posts=list(Post.objects.filter(status=Post.Status.PUBLISHED))
            if comments_count and not published_posts:
                raise CommandError("Comments required but there are no published posts. Publish posts first")
            
            comments_created=self._create_comments(comments_count, user_ids, published_posts, now)


        elapsed=time.perf_counter()-started
        self.stdout.write(f"Users:  {users_created:>5} created")
        self.stdout.write(f"Categories:  {categories_created:>5} created")
        self.stdout.write(f"Tags:  {tags_created:>5} created")
        self.stdout.write(f"Posts:  {len(posts):>5} created")
        self.stdout.write(f"Comments:  {comments_created:>5} created")
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.2f} seconds"))

    def _clear(self)->None:
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write("Existing data cleared except superuser")

    def _create_users(self, count: int)-> int:
        used_emails={email.lower() for email in User.objects.values_list("email", flat=True)}
        hashed_password=make_password(SEED_PASSWORD)
        users=[]
        for _ in range(count):
            first, last =self.fake.first_name(), self.fake.last_name()
            local=f"{slugify(first)}.{slugify(last)}"
            email=f"{local}@{EMAIL_DOMAIN}"
            number=2
            while email in used_emails:
                email=f"{local}{number}@{EMAIL_DOMAIN}"
                number+=1
            used_emails.add(email)
            users.append(User(
                email=email, first_name=first, last_name=last,password=hashed_password,
                is_active=random.random()>=INACTIVE_RATIO,
                is_staff=random.random()<STAFF_RATIO,
            ))
        return len(User.objects.bulk_create(users,batch_size=BATCH_SIZE))

    def _create_categories(self)->int:
        existing=set(Category.objects.values_list("slug", flat=True))
        new=[Category(name=n, slug=slugify(n)) for n in CATEGORY_NAMES if slugify(n) not in existing]
        return len(Category.objects.bulk_create(new))

    def _create_tags(self)->int:
        existing=set(Tag.objects.values_list("slug", flat=True))
        new=[Tag(name=n, slug=slugify(n)) for n in TAG_NAMES if slugify(n) not in existing]
        return len(Tag.objects.bulk_create(new))

    def _create_posts(self, count: int, user_ids: list[int], now: datetime) -> list[Post]:
        if count == 0:
            return []

        used_slugs=set(Post.objects.values_list("slug", flat=True))
        categories=list(Category.objects.all())
        tags=list(Tag.objects.all())
        posts=[]

        for _ in range(count):
            title=self.fake.sentence(nb_words=TITLE_WORDS).rstrip(".")
            has_category=categories and random.random()>=NO_CATEGORY_RATIO
            posts.append(Post(
                author_id=random.choice(user_ids),
                title=title,
                slug=unique_slug(slugify(title), used_slugs),
                body="\n\n".join(self.fake.paragraphs(nb=BODY_PARAGRAPHS)),
                status=Post.Status.PUBLISHED if random.random()<PUBLISHED_RATIO else Post.Status.DRAFT,
                category=random.choice(categories) if has_category else None,
            ))
        created=Post.objects.bulk_create(posts, batch_size=BATCH_SIZE)
        self._set_post_dates(created, now)

        if tags:
            for post in created:
                amount=random.randint(0, min(MAX_TAGS_PER_POST, len(tags)))
                post.tags.set(random.sample(tags, amount))
        return created

    def _set_post_dates(self, posts:list[Post], now:datetime)->None:
        """Giving every post realistic dates"""
        oldest=now-timedelta(days=POST_AGE_DAYS)

        for post in posts:
            post.created_at=random_moment(oldest, now)
            post.updated_at=post.created_at

            if random.random()<EDITED_RATIO and post.created_at + timedelta(days=MIN_EDIT_DELAY_DAYS) <= now:
                latest_edit = min(
                    post.created_at + timedelta(days=MAX_EDIT_DELAY_DAYS), now,
                    )
                post.updated_at = random_moment(
                    post.created_at + timedelta(days=MIN_EDIT_DELAY_DAYS), latest_edit,
                )
        Post.objects.bulk_update(posts, ["created_at", "updated_at"], batch_size=BATCH_SIZE)


    def _create_comments(self, count: int, user_ids: list[int], posts: list[Post], now:datetime)->int:
        if count==0:
            return 0
        comments=[
            Comment(
                post=random.choice(posts),
                author_id=random.choice(user_ids),
                body=" ".join(self.fake.sentences(nb=random.randint(MIN_COMMENT_SENTENCES,MAX_COMMENT_SENTENCES))),           
            )
            for _ in range(count)
        ]
        created=Comment.objects.bulk_create(comments,batch_size=BATCH_SIZE)
        for comment in created:
            comment.created_at=random_moment(comment.post.created_at, now)
        Comment.objects.bulk_update(created, ["created_at"], batch_size=BATCH_SIZE)
        return len(created)
    
                
                
                
