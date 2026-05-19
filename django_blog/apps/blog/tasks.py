"""BlogPostPage 이미지 rendition prewarm — Celery 비동기.

글 publish 시 본문·표지 이미지의 rendition을 미리 생성해
콜드 캐시 첫 방문자의 Pillow 변환 대기(최대 ~60초)를 제거한다.
on_blog_post_published 시그널에서 enqueue한다.
"""
from __future__ import annotations

import json
import logging

from celery import shared_task

log = logging.getLogger(__name__)

# 템플릿이 실제로 요청하는 rendition 전부 — picture 태그 srcset(400/800/1200) 포함.
# prewarm_renditions 관리 커맨드도 이 목록을 import해서 사용한다 (단일 출처).
SPECS = [
    # picture 태그 width 계열 + srcset (400/800/1200/1920)
    "width-400", "width-400|format-avif", "width-400|format-webp",
    "width-800", "width-800|format-avif", "width-800|format-webp",
    "width-1200", "width-1200|format-avif", "width-1200|format-webp",
    "width-1920", "width-1920|format-avif", "width-1920|format-webp",  # lightbox 고화질
    # 카드 썸네일 fill 계열
    "fill-600x600", "fill-600x600|format-avif", "fill-600x600|format-webp",
    "fill-200x200", "fill-200x200|format-avif", "fill-200x200|format-webp",
    # OG/Twitter 카드 (원본 포맷만 — SNS 크롤러는 avif/webp 미지원)
    "fill-1200x630",
]


def collect_image_ids(page) -> set[int]:
    """BlogPostPage의 표지 + 본문 StreamField 이미지 블록에서 이미지 PK 수집."""
    ids: set[int] = set()
    if getattr(page, "cover_image_id", None):
        ids.add(page.cover_image_id)
    try:
        raw = page.body.raw_data if hasattr(page.body, "raw_data") else json.loads(str(page.body) or "[]")
    except Exception:
        raw = []
    for item in raw or []:
        if item.get("type") == "image":
            iid = (item.get("value") or {}).get("image")
            if iid:
                ids.add(int(iid))
        # 추후 gallery 등 블록 추가 시 여기에 확장
    return ids


def warm_image(img, specs=None) -> tuple[int, int]:
    """단일 이미지의 rendition 생성. (성공 수, 실패 수) 반환."""
    total = errors = 0
    for spec in specs or SPECS:
        try:
            img.get_rendition(spec)
            total += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log.warning("prewarm rendition 실패 image=%s spec=%s: %s", img.pk, spec, e)
    return total, errors


@shared_task(name="blog.prewarm_post_renditions", ignore_result=True)
def prewarm_post_renditions(page_id: int):
    """단일 BlogPostPage의 본문·표지 이미지 rendition 사전 생성."""
    from apps.blog.models import BlogPostPage
    from apps.images.models import CustomImage

    page = BlogPostPage.objects.filter(pk=page_id).first()
    if page is None:
        log.warning("prewarm_post_renditions: page=%s 없음", page_id)
        return

    img_ids = collect_image_ids(page)
    total = errors = 0
    for iid in img_ids:
        img = CustomImage.objects.filter(pk=iid).first()
        if img is None:
            continue
        t, e = warm_image(img)
        total += t
        errors += e

    log.info("prewarm_post_renditions page=%s: %s images / %s renditions / errors=%s",
             page_id, len(img_ids), total, errors)
