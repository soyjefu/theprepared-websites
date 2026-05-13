"""모든 BlogPostPage의 SEO description을 새 톤으로 재생성.

기존 search_description을 비우고 Gemini 호출. 분당 5건 throttle.
seo_auto_locked=True 글은 건너뜀.
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "모든 글의 SEO description을 새 톤으로 재생성"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="0=전체")
        parser.add_argument("--sleep", type=float, default=15.0,
                            help="분당 5건 → 15초 간격")
        parser.add_argument("--only-empty", action="store_true",
                            help="search_description 비어 있는 글만")
        parser.add_argument("--only-empty-intro", action="store_true",
                            help="intro 비어 있는 글만 (카드 excerpt용)")
        parser.add_argument("--keep-locked", action="store_true",
                            help="seo_auto_locked=True는 건드리지 않음 (기본 True)")

    def handle(self, *args, **options):
        from apps.ai.tasks import generate_seo_meta
        from apps.blog.models import BlogPostPage

        qs = BlogPostPage.objects.live()
        if options["keep_locked"]:
            qs = qs.exclude(seo_auto_locked=True)
        if options["only_empty"]:
            qs = qs.filter(search_description="")
        if options["only_empty_intro"]:
            qs = qs.filter(intro="")
        qs = qs.order_by("first_published_at")
        if options["limit"] > 0:
            qs = qs[: options["limit"]]

        total = qs.count()
        self.stdout.write(f"대상: {total}건, 간격 {options['sleep']}s")
        ok = err = skipped = 0
        # intro만 채우는 모드면 description은 보존 (이미 좋은 톤으로 채워져 있음)
        preserve_desc = options["only_empty_intro"] or options["only_empty"]
        for i, p in enumerate(qs, 1):
            if p.search_description and not preserve_desc:
                p.search_description = ""
                p.save(update_fields=["search_description"])
            r = generate_seo_meta(p.pk, force=True)
            st = r.get("status")
            if st in ("ok", "too_short_used_body"):
                ok += 1
                p.refresh_from_db()
                shown = (p.intro or p.search_description or "")[:80]
                self.stdout.write(f"  [{i}/{total}] {p.slug}: {shown}")
            elif st in ("locked", "too_short", "has_alt"):
                skipped += 1
                self.stdout.write(f"  [{i}/{total}] {p.slug}: skipped ({st})")
            else:
                err += 1
                self.stdout.write(self.style.WARNING(
                    f"  [{i}/{total}] {p.slug}: {st}"
                ))
            if i < total:
                time.sleep(options["sleep"])

        self.stdout.write(self.style.SUCCESS(
            f"완료: ok={ok}, skipped={skipped}, errors={err}"
        ))
