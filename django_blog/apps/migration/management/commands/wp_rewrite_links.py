"""본문 paragraph 블록 안의 wp-content/uploads/* URL → 새 Wagtail media URL 치환.

이미 image 블록은 import_posts에서 ImageChooserBlock(pk) 로 변환되었으므로
여기서는 RichText 안의 raw HTML img/src 와 a/href 만 치환.
"""
from __future__ import annotations

import json
import logging
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.blog.models import BlogPostPage
from apps.images.models import CustomImage
from apps.migration.models import MigrationMap, MigrationRun

log = logging.getLogger(__name__)

# WP uploads 절대/상대 경로 모두 캐치
WP_UPLOAD_RE = re.compile(
    r"(?:https?://[^\"'\s)]+)?/wp-content/uploads/(?P<rel>[^\"'\s)]+)"
)


class Command(BaseCommand):
    help = "본문 RichText 내부의 wp-content/uploads URL 치환"

    def handle(self, *args, **options):
        run = MigrationRun.objects.create(command="wp_rewrite_links")
        counters = {"pages_scanned": 0, "rewrites": 0, "missing": 0, "errors": 0}

        # rel_path -> CustomImage.url 매핑
        rel_to_url: dict[str, str] = {}
        for m in MigrationMap.objects.filter(kind="attachment"):
            rel = (m.extra or {}).get("src_rel")
            if not rel:
                continue
            img = CustomImage.objects.filter(pk=m.wagtail_pk).first()
            if img:
                rel_to_url[rel] = img.file.url

        for page in BlogPostPage.objects.all():
            counters["pages_scanned"] += 1
            try:
                stream_raw = page.body.raw_data if hasattr(page.body, "raw_data") else json.loads(str(page.body) or "[]")
                changed = False
                for item in stream_raw:
                    if item["type"] != "paragraph":
                        continue
                    text = item["value"]
                    new_text, n = WP_UPLOAD_RE.subn(
                        lambda m: rel_to_url.get(m.group("rel"), m.group(0)),
                        text,
                    )
                    if n > 0:
                        # 매칭됐는데 매핑 못 찾은 건 그대로 유지 (missing 카운터)
                        for mm in WP_UPLOAD_RE.finditer(text):
                            if mm.group("rel") not in rel_to_url:
                                counters["missing"] += 1
                        item["value"] = new_text
                        counters["rewrites"] += n
                        changed = True
                if changed:
                    with transaction.atomic():
                        page.body = json.dumps(stream_raw)
                        page.save()
                        page.save_revision().publish()
            except Exception as e:
                counters["errors"] += 1
                log.exception("rewrite 실패 page %s: %s", page.pk, e)

        from django.utils import timezone
        run.finished_at = timezone.now()
        run.success = counters["errors"] == 0
        run.counters = counters
        run.save()
        self.stdout.write(self.style.SUCCESS(f"완료: {counters}"))
