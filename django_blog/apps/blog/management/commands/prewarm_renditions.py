"""모든 BlogPostPage 본문 이미지의 rendition 미리 생성 (일괄/백필용).

콜드 캐시 첫 방문자가 Pillow 변환 60초 기다리는 문제 해결.
spec 목록은 apps.blog.tasks.SPECS 단일 출처를 공유한다.
(평상시 신규 publish는 on_blog_post_published 시그널이 자동 prewarm)
"""
from __future__ import annotations

import json
import time

from django.core.management.base import BaseCommand

from apps.blog.tasks import SPECS


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
