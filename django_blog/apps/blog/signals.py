"""BlogPostPage post-save → Gemini 자동 SEO 메타 + IndexNow 자동 통보.

apps.ready()에서 명시적으로 connect한다.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def on_blog_post_save(sender, instance, created, **kwargs):
    if instance.seo_auto_locked:
        return
    if not instance.live:
        return

    if instance.seo_auto_generated_at:
        from django.utils import timezone
        if (timezone.now() - instance.seo_auto_generated_at).total_seconds() < 300:
            return

    try:
        from apps.ai.tasks import generate_seo_meta
        generate_seo_meta.delay(instance.pk)
    except Exception as e:
        log.warning("SEO meta enqueue 실패 page=%s: %s", instance.pk, e)


def on_blog_post_published(sender, instance, **kwargs):
    """글 publish 시 IndexNow로 Bing/Yandex에 즉시 통보."""
    if not instance.live:
        return
    try:
        from apps.ai.tasks import notify_indexnow
        url = f"https://theprepared.kr{instance.url}"
        notify_indexnow.delay(url)
    except Exception as e:
        log.warning("IndexNow enqueue 실패 page=%s: %s", instance.pk, e)
