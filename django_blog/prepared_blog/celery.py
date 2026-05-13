import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prepared_blog.settings.prod")

app = Celery("prepared_blog")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
