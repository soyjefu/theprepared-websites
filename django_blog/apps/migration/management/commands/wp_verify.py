"""WP ↔ Wagtail 이전 검증 리포트."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.blog.models import BlogPostPage, Category
from apps.images.models import CustomImage
from apps.migration.models import MigrationMap
from apps.migration.wp_db import fetch_one


class Command(BaseCommand):
    help = "WP ↔ Wagtail 검증 리포트"

    def handle(self, *args, **options):
        wp_post = fetch_one("SELECT COUNT(*) AS c FROM wp_posts WHERE post_type='post' AND post_status='publish'")["c"]
        wp_att = fetch_one("SELECT COUNT(*) AS c FROM wp_posts WHERE post_type='attachment'")["c"]
        wp_cat = fetch_one("SELECT COUNT(*) AS c FROM wp_term_taxonomy WHERE taxonomy='category'")["c"]
        wp_tag = fetch_one("SELECT COUNT(*) AS c FROM wp_term_taxonomy WHERE taxonomy='post_tag'")["c"]

        wt_post = BlogPostPage.objects.live().count()
        wt_img = CustomImage.objects.count()
        wt_cat = Category.objects.count()
        wt_map_post = MigrationMap.objects.filter(kind="post").count()
        wt_map_att = MigrationMap.objects.filter(kind="attachment").count()
        wt_map_cat = MigrationMap.objects.filter(kind="category").count()
        wt_map_tag = MigrationMap.objects.filter(kind="tag").count()

        rows = [
            ("Posts (publish)", wp_post, wt_post, wt_map_post),
            ("Attachments", wp_att, wt_img, wt_map_att),
            ("Categories", wp_cat, wt_cat, wt_map_cat),
            ("Tags", wp_tag, "-", wt_map_tag),
        ]
        self.stdout.write(f"{'Kind':<22} {'WP':>8} {'Wagtail':>10} {'Map':>8}")
        for name, wp, wt, m in rows:
            mark = "✓" if (isinstance(wt, int) and wt >= wp) or wt == "-" else "✗"
            self.stdout.write(f"{name:<22} {str(wp):>8} {str(wt):>10} {str(m):>8} {mark}")

        # 슬러그 충돌
        from collections import Counter
        slugs = list(BlogPostPage.objects.values_list("slug", flat=True))
        dupes = [s for s, c in Counter(slugs).items() if c > 1]
        if dupes:
            self.stdout.write(self.style.WARNING(f"슬러그 중복: {dupes}"))
        else:
            self.stdout.write(self.style.SUCCESS("슬러그 충돌 없음"))
