"""CustomImage 업로드 시 alt 자동 생성 — Celery 비동기."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def on_image_save(sender, instance, created, **kwargs):
    """업로드된 이미지에 alt가 비어있으면 Gemini Vision으로 자동 생성."""
    if not created:
        return
    if instance.alt_text:
        # 사용자가 업로드 시 같이 입력했으면 그대로 존중
        return
    try:
        from apps.ai.tasks import generate_image_alt
        generate_image_alt.delay(instance.pk)
    except Exception as e:
        log.warning("image alt enqueue 실패 image=%s: %s", instance.pk, e)
