"""모든 BlogPostPage 본문 이미지의 rendition 미리 생성.

콜드 캐시 첫 방문자가 Pillow 변환 60초 기다리는 문제 해결.
spec: width-800 + format-avif/webp/원본 3종.
"""
from __future__ import annotations

import json
import time

from django.core.management.base import BaseCommand


SPECS = [
    "width-800",
    "width-800|format-avif",
    "width-800|format-webp",
    "width-1920",            # lightbox용 고화질
    "width-1920|format-avif",
    "width-1920|format-webp",
    "fill-600x600",          # 영상 기록 카드
    "fill-600x600|format-avif",
    "fill-600x600|format-webp",
    "fill-200x200",          # 포스트 카드 썸네일
    "fill-200x200|format-avif",
    "fill-200x200|format-webp",
]


class Command(BaseCommand):
    help = "BlogPostPage 본문 + 표지 이미지의 rendition 미리 생성"

    def add_arguments(self, parser):
        parser.add_argument("--specs", nargs="+", help="override default specs")

    def handle(self, *args, **options):
        from apps.blog.models import BlogPostPage
        from apps.images.models import CustomImage

        specs = options.get("specs") or SPECS
        seen = set()
        total = 0
        errors = 0
        start = time.monotonic()

        def warm(img_id):
            nonlocal total, errors
            if img_id in seen:
                return
            seen.add(img_id)
            img = CustomImage.objects.filter(pk=img_id).first()
            if img is None:
                return
            for spec in specs:
                try:
                    img.get_rendition(spec)
                    total += 1
                except Exception as e:
                    errors += 1
                    self.stderr.write(f"  ! {img_id} {spec}: {e}")

        n_pages = 0
        for page in BlogPostPage.objects.all().iterator():
            n_pages += 1
            if page.cover_image_id:
                warm(page.cover_image_id)
            try:
                raw = page.body.raw_data if hasattr(page.body, "raw_data") else json.loads(str(page.body) or "[]")
            except Exception:
                continue
            for item in raw or []:
                t = item.get("type")
                if t == "image":
                    v = item.get("value") or {}
                    iid = v.get("image")
                    if iid:
                        warm(int(iid))
                # 추후 gallery 등 추가 가능
            if n_pages % 5 == 0:
                self.stdout.write(f"  {n_pages} pages / {len(seen)} images / {total} renditions / {time.monotonic()-start:.1f}s")

        elapsed = time.monotonic() - start
        self.stdout.write(self.style.SUCCESS(
            f"완료: {n_pages} pages, {len(seen)} 이미지, {total} renditions, "
            f"errors={errors}, elapsed={elapsed:.1f}s"
        ))
