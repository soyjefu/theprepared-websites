"""WP terms (category, post_tag) → Wagtail Category snippet + django-taggit Tag.

slug 보존. 멱등.
"""
from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from taggit.models import Tag

from apps.blog.models import Category
from apps.migration.models import MigrationMap, MigrationRun
from apps.migration.wp_db import fetch_all

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "WP category + post_tag → Wagtail"

    def handle(self, *args, **options):
        run = MigrationRun.objects.create(command="wp_import_taxonomy")
        counters = {"category_created": 0, "category_skipped": 0,
                    "tag_created": 0, "tag_skipped": 0, "errors": 0}

        # 1) 카테고리
        rows = fetch_all("""
            SELECT t.term_id AS wp_id, t.name, t.slug, tt.description, tt.count
            FROM wp_terms t JOIN wp_term_taxonomy tt ON tt.term_id=t.term_id
            WHERE tt.taxonomy='category'
        """)
        self.stdout.write(f"category {len(rows)}건 처리…")
        for row in rows:
            try:
                with transaction.atomic():
                    existing = MigrationMap.objects.filter(kind="category", wp_id=row["wp_id"]).first()
                    if existing:
                        counters["category_skipped"] += 1
                        continue
                    cat, created = Category.objects.get_or_create(
                        slug=row["slug"][:80],
                        defaults={"name": row["name"][:80], "description": (row["description"] or "")[:240]},
                    )
                    if not created:
                        # 같은 slug가 이미 있으면 그대로 사용
                        pass
                    MigrationMap.objects.create(
                        wp_id=row["wp_id"], kind="category",
                        wagtail_pk=cat.pk, wagtail_model="blog.Category",
                        extra={"wp_count": row["count"]},
                    )
                    counters["category_created" if created else "category_skipped"] += 1
            except Exception as e:
                counters["errors"] += 1
                log.exception("category import 실패: %s", e)

        # 2) 태그
        rows = fetch_all("""
            SELECT t.term_id AS wp_id, t.name, t.slug, tt.count
            FROM wp_terms t JOIN wp_term_taxonomy tt ON tt.term_id=t.term_id
            WHERE tt.taxonomy='post_tag'
        """)
        self.stdout.write(f"post_tag {len(rows)}건 처리…")
        for row in rows:
            try:
                with transaction.atomic():
                    existing = MigrationMap.objects.filter(kind="tag", wp_id=row["wp_id"]).first()
                    if existing:
                        counters["tag_skipped"] += 1
                        continue
                    tag, created = Tag.objects.get_or_create(
                        slug=row["slug"][:100],
                        defaults={"name": row["name"][:100]},
                    )
                    MigrationMap.objects.create(
                        wp_id=row["wp_id"], kind="tag",
                        wagtail_pk=tag.pk, wagtail_model="taggit.Tag",
                        extra={"wp_count": row["count"]},
                    )
                    counters["tag_created" if created else "tag_skipped"] += 1
            except Exception as e:
                counters["errors"] += 1
                log.exception("tag import 실패: %s", e)

        from django.utils import timezone
        run.finished_at = timezone.now()
        run.success = counters["errors"] == 0
        run.counters = counters
        run.save()
        self.stdout.write(self.style.SUCCESS(f"완료: {counters}"))
