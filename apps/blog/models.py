
from django.db.models import(
    CharField,
    SlugField,
    TextChoices,
    TextField,
    Model, 
    ForeignKey, 
    CASCADE,
    SET_NULL,
    ManyToManyField,
    DateTimeField
)

from apps.auths.models import User

class Category(Model):
    """Categories db table"""

    NAME_MAX_LEN =100

    name=CharField(
        max_length=NAME_MAX_LEN,
        unique=True,
    )

    slug=SlugField(
        unique=True
    )

    class Meta:
        """Metadat for this table"""
        verbose_name_plural="Categories"

    def __str__(self)->str:
        return self.name 


class Tag(Model):
    """Tags db table"""
    NAME_MAX_LEN =50

    name=CharField(
        max_length=NAME_MAX_LEN,
        unique=True,
    )
    
    slug=SlugField(
        unique=True
    )
    def __str__(self)->str:
        return self.name 

class Post(Model):
    """Posts db table"""

    TITLE_MAX_LEN=200
    STATUS_MAX_LEN=20

    class Status(TextChoices):
        """Available post statuses"""
        DRAFT="draft", "Draft"
        PUBLISHED="published", "Published"

    author=ForeignKey(
        to=User,
        on_delete=CASCADE,
        related_name="posts"
    )

    title=CharField(
        max_length=TITLE_MAX_LEN
    )

    slug=SlugField(
        unique=True
    )

    body=TextField()

    category=ForeignKey(
        to=Category,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="posts"
    )

    tags=ManyToManyField(
        to=Tag,
        blank=True,
        related_name="posts"
    )
    status=CharField(
        max_length=STATUS_MAX_LEN,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_at=DateTimeField(
        auto_now_add=True
    )

    updated_at=DateTimeField(
        auto_now=True
    )

    def __str__(self)->str:
        return self.title

class Comment(Model):
    """Comments db table"""

    post=ForeignKey(
        to=Post,
        on_delete=CASCADE,
        related_name="comments"
    )

    author=ForeignKey(
        to=User,
        on_delete=CASCADE,
        related_name="comments"
    )

    body=TextField()

    created_at=DateTimeField(
        auto_now_add=True
    )

    def __str__(self)->str:
        return f"Comment {self.pk} on post {self.post}"
