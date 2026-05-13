"""WP 구 URL → Wagtail 신 URL 301 매핑.

WP permalink_structure='/%postname%/' → /{slug}/ 형태였으므로
모든 BlogPostPage 에 대해 /{slug}/ → /blog/{slug}/ 301 등록.
멱등.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from wagtail.contrib.redirects.models import Redirect

from apps.blog.models import BlogPostPage


class Command(BaseCommand):
    help = "구 워드프레스 슬러그 → Wagtail 페이지로 301 redirect 등록"

    def handle(self, *args, **options):
        created = updated = 0
        for page in BlogPostPage.objects.live():
            old = f"/{page.slug}".rstrip("/")  # Wagtail Redirect는 trailing slash 없는 형태
            existing = Redirect.objects.filter(old_path=old).first()
            if existing:
                if existing.redirect_page_id != page.pk or not existing.is_permanent:
                    existing.redirect_page = page
                    existing.is_permanent = True
                    existing.save()
                    updated += 1
                continue
            Redirect.objects.create(
                old_path=old,
                redirect_page=page,
                is_permanent=True,
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"created={created}, updated={updated}, total_pages={BlogPostPage.objects.live().count()}"))
