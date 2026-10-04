from django.contrib.admin import ModelAdmin, register
from apps.blog.models import(
    Category,
    Tag,
    Post,
    Comment
)

@register(Category)
class CategoryAdmin(ModelAdmin):
    """
    Category admin conf
    """
    ...



@register(Tag)
class TagAdmin(ModelAdmin):
    """
    Tag admin conf
    """
    ...
    


@register(Post)
class PostAdmin(ModelAdmin):
    """
    Post admin conf
    """
    ...
    


@register(Comment)
class CommentAdmin(ModelAdmin):
    """
    Comment admin conf
    """
    ...
    
