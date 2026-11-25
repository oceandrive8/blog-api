import os
from pathlib import Path

from celery import Celery
from decouple import AutoConfig

env_config = AutoConfig(search_path=str(Path(__file__).resolve().parent))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    f"settings.env.{env_config('BLOG_ENV_ID', default='local')}",
)

app = Celery("settings")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
