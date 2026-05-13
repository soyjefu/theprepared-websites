"""WP 홈 구조와 동일하게 HomePage.body 시드:
  1) "생각할 거리"  (사회/문화/초안)   line layout 4건
  2) "영상 기록"   (영상 기록)         grid 2col 4건
  3) "관심 분야"   (사회/문화/코드 스케치/초안)   카드 showcase 2col

`--force` 옵션이 있으면 기존 body 덮어씀.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.blog.models import Category, HomePage


CAT_SLUGS_FEED = ["society", "culture", "drafts"]
CAT_SLUG_GRID = "image-records"
CAT_SLUGS_SHOWCASE = ["society", "culture", "code_sketch", "drafts"]


class Command(BaseCommand):
    help = "HomePage.body를 WP 홈 구조로 시드"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        home = HomePage.objects.live().first()
        if home is None:
            self.stderr.write("HomePage가 없습니다. init_site를 먼저 실행하세요.")
            return

        # 이미 body가 있으면 --force 없는 한 스킵
        try:
            existing = home.body.raw_data if hasattr(home.body, "raw_data") else []
        except Exception:
            existing = []
        if existing and not options["force"]:
            self.stdout.write(self.style.WARNING(
                f"HomePage.body에 이미 {len(existing)}개 블록이 있습니다. --force로 덮어쓰세요."
            ))
            return

        def cat_id(slug: str) -> int | None:
            c = Category.objects.filter(slug=slug).first()
            return c.id if c else None

        feed_cats = [cat_id(s) for s in CAT_SLUGS_FEED]
        feed_cats = [c for c in feed_cats if c]
        grid_cat = cat_id(CAT_SLUG_GRID)
        showcase_cats = [cat_id(s) for s in CAT_SLUGS_SHOWCASE]
        showcase_cats = [c for c in showcase_cats if c]

        stream = []

        # 1) 생각할 거리
        if feed_cats:
            stream.append({
                "type": "category_feed",
                "value": {
                    "title": "생각할 거리",
                    "subtitle": "스쳐간 생각에 대한 기록.",
                    "categories": feed_cats,
                    "count": 4,
                    "show_more_link": True,
                },
            })

        # 2) 영상 기록
        if grid_cat:
            stream.append({
                "type": "category_grid",
                "value": {
                    "title": "영상 기록",
                    "subtitle": "삶에서 마주한 곳곳에 대한 영상 기록.",
                    "categories": [grid_cat],
                    "count": 4,
                    "columns": "2",
                    "show_more_link": True,
                },
            })

        # 3) 관심 분야
        if showcase_cats:
            stream.append({
                "type": "category_showcase",
                "value": {
                    "title": "관심 분야",
                    "columns": "2",
                    "items": [
                        {"category": c, "preview_count": 3, "description_override": ""}
                        for c in showcase_cats
                    ],
                },
            })

        home.body = json.dumps(stream)
        home.save_revision().publish()
        self.stdout.write(self.style.SUCCESS(f"HomePage.body 시드 완료: {len(stream)}개 섹션"))
