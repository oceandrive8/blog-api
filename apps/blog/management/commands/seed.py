import random
import time
from typing import Any


from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand,CommandError, CommandParser
from django.db import transaction
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
STATUS_PUBLISHED="published"
STATUS_DRAFT="draft"


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

        with transaction.atomic():
            if options["clear"]:
                self._clear()
            users_created=self._create_users(users_count)
            categories_created=self._create_categories()
            tags_created=self._create_tags()


            user_ids=list(User.objects.values_list("id", flat=True))
            if (posts_count or comments_count) and not user_ids:
                raise CommandError("Posts and comments are required but there is no users. use --users")

                
            posts_created=self._create_posts(posts_count, user_ids)


            published_ids=list(Post.objects.filter(status=STATUS_PUBLISHED).values_list("id", flat=True))
            if comments_count and not published_ids:
                raise CommandError("Comments required but there are no published posts. Publish posts first")
            comments_created=self._create_comments(comments_count, user_ids, published_ids)


        elapsed=time.perf_counter()-started
        self.stdout.write(f"Users:  {users_created:>5} created")
        self.stdout.write(f"Categories:  {categories_created:>5} created")
        self.stdout.write(f"Tags:  {tags_created:>5} created")
        self.stdout.write(f"Posts:  {posts_created:>5} created")
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

    def _create_posts(self, count:int, user_ids: list[int])->int:
        if count==0:
            return 0

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
                status=STATUS_PUBLISHED if random.random()<PUBLISHED_RATIO else STATUS_DRAFT,
                category=random.choice(categories) if has_category else None,
            ))
        created=Post.objects.bulk_create(posts, batch_size=BATCH_SIZE)
        if tags:
            for post in created:
                amount=random.randint(0, min(MAX_TAGS_PER_POST, len(tags)))
                post.tags.set(random.sample(tags, amount))
        return len(created)


    def _create_comments(self, count: int, user_ids: list[int], post_ids: list[int])->int:
        comments=[
            Comment(
                post_id=random.choice(post_ids),
                author_id=random.choice(user_ids),
                body=" ".join(self.fake.sentences(nb=random.randint(MIN_COMMENT_SENTENCES,MAX_COMMENT_SENTENCES))),           
            )
            for _ in range(count)
        ]
        return len(Comment.objects.bulk_create(comments,batch_size=BATCH_SIZE))
    
                
                
                
