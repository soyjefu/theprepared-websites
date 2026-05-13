from django.apps import AppConfig


class AIConfig(AppConfig):
    name = "apps.ai"
    label = "blog_ai"
    verbose_name = "AI"

    def ready(self):
        # Wagtail admin hook 등록
        from . import admin  # noqa: F401
