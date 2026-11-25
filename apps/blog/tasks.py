from celery import shared_task
from django.core.mail import send_mail

from apps.blog.models import Comment


NEW_COMMENT_SUBJECT = 'New comment on "{title}"'
NEW_COMMENT_BODY =  "{first_name} {last_name} commented:\n\n{body}"
@shared_task
def send_new_comment_email(comment_id: int) -> None:
    comment = (
        Comment.objects
        .select_related("post__author", "author")
        .filter(pk=comment_id)
        .first()
    )
    if comment is None:
        return

    post_author = comment.post.author
    if comment.author_id == post_author.pk:
        return

    send_mail(
        subject=NEW_COMMENT_SUBJECT.format(title=comment.post.title),
        message=NEW_COMMENT_BODY.format(
            first_name=comment.author.first_name,
            last_name=comment.author.last_name,
            body=comment.body,
        ),
        from_email=None, # uses DEFAULT_FROM_EMAIL
        recipient_list=[post_author.email],
    )