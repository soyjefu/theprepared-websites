from django.apps import AppConfig


class BlogConfig(AppConfig):
    name = "apps.blog"
    label = "blog"
    verbose_name = "Blog"

    def ready(self):
        # BlogPostPage 새로 publish 시 Gemini가 원문 문체로 SEO 메타 자동 생성.
        from django.db.models.signals import post_save
        from wagtail.signals import page_published
        from .models import BlogPostPage
        from .signals import on_blog_post_save, on_blog_post_published
        post_save.connect(on_blog_post_save, sender=BlogPostPage)
        page_published.connect(on_blog_post_published, sender=BlogPostPage)
