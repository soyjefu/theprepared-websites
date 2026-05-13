"""WP wp_posts (post_type=post, post_status=publish) → BlogPostPage import.

- Gutenberg 본문 → ContentStreamBlock JSON 변환 (apps.migration.gutenberg)
- 슬러그 보존 (BlogIndexPage 하위)
- 첫 published 날짜 보존
- 카테고리 1개 (Rank Math primary, 없으면 첫 번째)
- 태그 다중
- cover_image: _thumbnail_id → MigrationMap 매핑
- Rank Math meta → SEO 필드 초기값 (description, og_title 등)
- 멱등: 기존 매핑 있으면 스킵 (--force 로 갱신)
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from taggit.models import Tag

from apps.blog.models import BlogIndexPage, BlogPostPage, Category
from apps.images.models import CustomImage
from apps.migration.gutenberg import to_streamfield
from apps.migration.models import MigrationMap, MigrationRun
from apps.migration.wp_db import fetch_all

log = logging.getLogger(__name__)


def _image_mapper_factory():
    """wp_attachment_id -> CustomImage.pk (없으면 None). 캐시 사용."""
    cache: dict[int, int | None] = {}

    def lookup(wp_id: int) -> int | None:
        if wp_id in cache:
            return cache[wp_id]
        m = MigrationMap.objects.filter(kind="attachment", wp_id=wp_id).first()
        cache[wp_id] = m.wagtail_pk if m else None
        return cache[wp_id]

    return lookup


def _post_meta(post_id: int) -> dict[str, str]:
    rows = fetch_all(
        "SELECT meta_key, meta_value FROM wp_postmeta WHERE post_id=%s", (post_id,)
    )
    return {r["meta_key"]: r["meta_value"] for r in rows}


def _post_terms(post_id: int) -> list[dict]:
    return fetch_all(
        """
        SELECT t.term_id AS wp_id, t.name, t.slug, tt.taxonomy
        FROM wp_term_relationships tr
        JOIN wp_term_taxonomy tt ON tt.term_taxonomy_id = tr.term_taxonomy_id
        JOIN wp_terms t ON t.term_id = tt.term_id
        WHERE tr.object_id = %s
        """,
        (post_id,),
    )


class Command(BaseCommand):
    help = "WP posts → Wagtail BlogPostPage import"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="0=전체")
        parser.add_argument("--force", action="store_true", help="기존 페이지 갱신")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        run = MigrationRun.objects.create(command="wp_import_posts")
        counters = {"created": 0, "updated": 0, "skipped": 0, "errors": 0,
                    "missing_index": 0, "missing_image": 0}
        start = time.monotonic()

        index = BlogIndexPage.objects.live().first()
        if index is None:
            self.stderr.write(self.style.ERROR("BlogIndexPage가 없습니다. init_site 먼저 실행하세요."))
            return
        # treebeard 트리 보정 (numchild stale 방지)
        from wagtail.models import Page as WagtailPage
        WagtailPage.fix_tree()
        index.refresh_from_db()

        sql = """
            SELECT ID AS wp_id, post_title AS title, post_name AS slug,
                   post_content AS content, post_excerpt AS excerpt,
                   post_date_gmt AS date_gmt, post_modified_gmt AS modified_gmt,
                   post_author AS author_id
            FROM wp_posts
            WHERE post_type='post' AND post_status='publish'
            ORDER BY post_date
        """
        if options["limit"] > 0:
            sql += f" LIMIT {int(options['limit'])}"
        rows = fetch_all(sql)
        self.stdout.write(f"WP posts {len(rows)}건 처리 시작…")

        image_mapper = _image_mapper_factory()

        for row in rows:
            wp_id = row["wp_id"]
            try:
                meta = _post_meta(wp_id)
                terms = _post_terms(wp_id)

                stream = to_streamfield(row["content"] or "", image_mapper)

                cover_pk = None
                thumb_id = meta.get("_thumbnail_id")
                if thumb_id:
                    cover_pk = image_mapper(int(thumb_id))
                    if cover_pk is None:
                        counters["missing_image"] += 1

                # 카테고리: Rank Math primary 우선
                primary_cat_wp = meta.get("rank_math_primary_category")
                category_pk = None
                if primary_cat_wp:
                    cm = MigrationMap.objects.filter(kind="category", wp_id=int(primary_cat_wp)).first()
                    if cm:
                        category_pk = cm.wagtail_pk
                if category_pk is None:
                    for t in terms:
                        if t["taxonomy"] == "category":
                            cm = MigrationMap.objects.filter(kind="category", wp_id=t["wp_id"]).first()
                            if cm:
                                category_pk = cm.wagtail_pk
                                break

                # 태그들
                tag_pks = []
                for t in terms:
                    if t["taxonomy"] == "post_tag":
                        tm = MigrationMap.objects.filter(kind="tag", wp_id=t["wp_id"]).first()
                        if tm:
                            tag_pks.append(tm.wagtail_pk)

                # SEO 메타 (Rank Math)
                seo_desc = (meta.get("rank_math_description") or "")[:300]
                seo_title = (meta.get("rank_math_title") or "")[:200]

                first_published = None
                if row["date_gmt"]:
                    first_published = row["date_gmt"]
                    if first_published.tzinfo is None:
                        first_published = first_published.replace(tzinfo=dt.timezone.utc)

                if options["dry_run"]:
                    self.stdout.write(f"[dry] {row['title']} (slug={row['slug']}) blocks={len(stream)} cat={category_pk} tags={len(tag_pks)}")
                    continue

                with transaction.atomic():
                    existing = MigrationMap.objects.filter(kind="post", wp_id=wp_id).first()
                    if existing and not options["force"]:
                        counters["skipped"] += 1
                        continue

                    if existing:
                        page = BlogPostPage.objects.filter(pk=existing.wagtail_pk).first()
                        if page is None:
                            existing.delete()
                            existing = None

                    if existing is None:
                        page = BlogPostPage(
                            title=row["title"][:255],
                            slug=row["slug"][:255],
                            intro=(row["excerpt"] or "")[:240],
                            body=json.dumps(stream),
                            cover_image_id=cover_pk,
                            category_id=category_pk,
                            seo_title=seo_title,
                            search_description=seo_desc,
                            first_published_at=first_published,
                        )
                        # 매 루프마다 부모 fresh fetch (numchild stale 회피)
                        parent = BlogIndexPage.objects.get(pk=index.pk)
                        parent.add_child(instance=page)
                    else:
                        page.title = row["title"][:255]
                        page.intro = (row["excerpt"] or "")[:240]
                        page.body = json.dumps(stream)
                        page.cover_image_id = cover_pk
                        page.category_id = category_pk
                        page.seo_title = seo_title
                        page.search_description = seo_desc
                        page.save()

                    if first_published:
                        page.first_published_at = first_published
                        page.last_published_at = first_published
                        page.save()

                    # 태그
                    if tag_pks:
                        tags = list(Tag.objects.filter(pk__in=tag_pks))
                        page.tags.set([t.name for t in tags])
                        page.save()

                    page.save_revision().publish()

                    if existing is None:
                        MigrationMap.objects.create(
                            wp_id=wp_id, kind="post",
                            wagtail_pk=page.pk, wagtail_model="blog.BlogPostPage",
                            extra={"slug": row["slug"], "n_blocks": len(stream)},
                        )
                        counters["created"] += 1
                    else:
                        counters["updated"] += 1

            except Exception as e:
                counters["errors"] += 1
                log.exception("post import 실패 wp_id=%s: %s", wp_id, e)

        elapsed = time.monotonic() - start
        run.finished_at = timezone.now()
        run.success = counters["errors"] == 0
        run.counters = counters
        run.notes = f"elapsed={elapsed:.1f}s"
        run.save()
        self.stdout.write(self.style.SUCCESS(f"완료: {counters} ({elapsed:.1f}s)"))
