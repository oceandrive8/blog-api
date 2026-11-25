from django.utils.text import slugify

from apps.blog.models import Post

SLUG_MAX_LEN = Post._meta.get_field("slug").max_length


def generate_unique_slug(title: str) -> str:
    base = slugify(title)[:SLUG_MAX_LEN].strip("-") or "post"
    slug, number = base, 2
    while Post.objects.filter(slug=slug).exists():
        suffix = f"-{number}"
        slug = f"{base[:SLUG_MAX_LEN - len(suffix)]}{suffix}"
        number+=1
    return slug
