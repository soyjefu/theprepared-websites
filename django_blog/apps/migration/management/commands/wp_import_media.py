"""WP attachment → Wagtail CustomImage 이전.

- wp_posts(post_type=attachment) 의 _wp_attached_file (상대 경로)을 보고
  /home/soyjefu/theprepared/websites/wordpress-app/www/html/wp-content/uploads/<상대경로>
  파일을 Wagtail media/original_images/ 로 등록.
- alt 는 _wp_attachment_image_alt 메타에서.
- MigrationMap(kind=attachment) 로 wp_id ↔ wagtail pk 매핑.
- 멱등: 이미 매핑된 wp_id 는 스킵 (--force 로 갱신).
- 이미지가 아닌 파일(pdf 등)은 별도 옵션으로 wagtaildocs.Document 로 (현재는 이미지만).
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.images.models import CustomImage
from apps.migration.models import MigrationMap, MigrationRun
from apps.migration.wp_db import fetch_all

log = logging.getLogger(__name__)

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".bmp", ".tiff"}


class Command(BaseCommand):
    help = "WP attachments → Wagtail CustomImage import"

    def add_arguments(self, parser):
        parser.add_argument(
            "--uploads",
            default=os.environ.get(
                "WP_UPLOADS_PATH",
                "/home/soyjefu/theprepared/websites/wordpress-app/www/html/wp-content/uploads",
            ),
        )
        parser.add_argument("--limit", type=int, default=0, help="0 = 전체")
        parser.add_argument("--force", action="store_true", help="기존 매핑 갱신")

    def handle(self, *args, **options):
        uploads_root = Path(options["uploads"])
        if not uploads_root.exists():
            self.stderr.write(self.style.ERROR(f"uploads 경로 없음: {uploads_root}"))
            return

        run = MigrationRun.objects.create(command="wp_import_media")
        counters = {"created": 0, "updated": 0, "skipped": 0, "missing_file": 0, "errors": 0, "non_image": 0}
        start = time.monotonic()

        sql = """
            SELECT p.ID AS wp_id, p.post_title AS title, p.post_date AS date,
                   pm1.meta_value AS attached_file,
                   pm2.meta_value AS alt
            FROM wp_posts p
            LEFT JOIN wp_postmeta pm1 ON pm1.post_id=p.ID AND pm1.meta_key='_wp_attached_file'
            LEFT JOIN wp_postmeta pm2 ON pm2.post_id=p.ID AND pm2.meta_key='_wp_attachment_image_alt'
            WHERE p.post_type='attachment'
            ORDER BY p.ID
        """
        if options["limit"] > 0:
            sql += f" LIMIT {int(options['limit'])}"
        rows = fetch_all(sql)
        self.stdout.write(f"WP attachment {len(rows)}건 처리 시작…")

        for row in rows:
            wp_id = row["wp_id"]
            rel = (row["attached_file"] or "").lstrip("/")
            if not rel:
                counters["skipped"] += 1
                continue
            ext = Path(rel).suffix.lower()
            if ext not in IMG_EXT:
                counters["non_image"] += 1
                continue
            src = uploads_root / rel
            if not src.exists():
                counters["missing_file"] += 1
                self.stdout.write(self.style.WARNING(f"파일 없음: {src}"))
                continue

            existing = MigrationMap.objects.filter(kind="attachment", wp_id=wp_id).first()
            if existing and not options["force"]:
                counters["skipped"] += 1
                continue

            try:
                with transaction.atomic():
                    title = (row["title"] or src.stem)[:255]
                    if existing:
                        img = CustomImage.objects.filter(pk=existing.wagtail_pk).first()
                        if img is None:
                            existing.delete()
                            existing = None
                    if existing is None:
                        img = CustomImage(title=title, alt_text=(row["alt"] or "")[:255])
                        with src.open("rb") as fp:
                            img.file.save(src.name, File(fp), save=False)
                        img.save()
                        MigrationMap.objects.create(
                            wp_id=wp_id,
                            kind="attachment",
                            wagtail_pk=img.pk,
                            wagtail_model="blog_images.CustomImage",
                            extra={"src_rel": rel, "wp_date": str(row["date"])},
                        )
                        counters["created"] += 1
                    else:
                        # force 갱신: alt만 갱신
                        img.title = title
                        img.alt_text = (row["alt"] or "")[:255]
                        img.save()
                        existing.updated_at  # noqa
                        existing.save(update_fields=["updated_at"])
                        counters["updated"] += 1
            except Exception as e:
                counters["errors"] += 1
                log.exception("attachment import 실패 wp_id=%s: %s", wp_id, e)

        elapsed = time.monotonic() - start
        run.finished_at = run.started_at.__class__.now() if hasattr(run.started_at.__class__, "now") else None
        from django.utils import timezone
        run.finished_at = timezone.now()
        run.success = counters["errors"] == 0
        run.counters = counters
        run.notes = f"elapsed={elapsed:.1f}s, total_rows={len(rows)}"
        run.save()

        self.stdout.write(self.style.SUCCESS(f"완료: {counters} ({elapsed:.1f}s)"))
