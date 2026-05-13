"""영상 기록 글에서 image 블록 바로 다음 paragraph를 그 image의 caption으로 이동."""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

TARGET_SLUGS = [
    "2025-asansi-fall",
    "2025-gapyeong-yeonisan",
    "2025-yeosu-yeongchuisan",
    "2025-nonsan-sunshine",
    "2026-sky",
    "2026-gangneung",
    "2025-sky",
    "2025-china-shanghai",
]


def _plain_text(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


class Command(BaseCommand):
    help = "지정 글들에서 image 다음 paragraph → caption 으로 이동"

    def add_arguments(self, parser):
        parser.add_argument("--slugs", nargs="+", help="override target slugs")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--max-len", type=int, default=200,
                            help="이 이상 긴 paragraph는 caption으로 변환하지 않음")

    def handle(self, *args, **options):
        from apps.blog.models import BlogPostPage
        slugs = options.get("slugs") or TARGET_SLUGS
        max_len = options["max_len"]
        dry = options["dry_run"]

        total_pages = 0
        total_moved = 0
        for slug in slugs:
            page = BlogPostPage.objects.filter(slug=slug).first()
            if page is None:
                self.stderr.write(self.style.WARNING(f"slug={slug} not found"))
                continue
            try:
                raw = page.body.raw_data if hasattr(page.body, "raw_data") else json.loads(str(page.body) or "[]")
            except Exception:
                continue

            new_stream = []
            i = 0
            moved = 0
            while i < len(raw):
                cur = raw[i]
                nxt = raw[i + 1] if i + 1 < len(raw) else None
                if (cur.get("type") == "image"
                    and nxt is not None
                    and nxt.get("type") == "paragraph"):
                    cap_text = _plain_text(nxt.get("value") or "")
                    cap_text = re.sub(r"\s+", " ", cap_text).strip()
                    if cap_text and len(cap_text) <= max_len:
                        v = dict(cur.get("value") or {})
                        if not v.get("caption"):
                            v["caption"] = cap_text
                            cur = dict(cur, value=v)
                            new_stream.append(cur)
                            moved += 1
                            i += 2
                            continue
                new_stream.append(cur)
                i += 1

            if moved == 0:
                self.stdout.write(f"  {slug}: 변경 없음")
                continue
            total_pages += 1
            total_moved += moved
            self.stdout.write(self.style.SUCCESS(f"  {slug}: {moved}개 caption 이동"))
            if dry:
                continue
            page.body = json.dumps(new_stream)
            page.save_revision().publish()

        self.stdout.write(self.style.SUCCESS(
            f"완료: {total_pages}개 글 / {total_moved}개 caption 변환 (dry={dry})"
        ))
