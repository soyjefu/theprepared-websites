"""댓글 알림 — 관리자 이메일만. Discord/외부 webhook 제거 (admin 대시보드에서 확인)."""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Comment

log = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def notify_new_comment(self, comment_id: int):
    try:
        c = Comment.objects.select_related("page").get(pk=comment_id)
    except Comment.DoesNotExist:
        return
    if c.status != Comment.STATUS_APPROVED:
        return

    page = c.page
    page_url = f"{settings.WAGTAILADMIN_BASE_URL.rstrip('/')}{page.url}"

    if settings.ADMIN_EMAIL:
        try:
            send_mail(
                subject=f"[The Prepared] 새 댓글: {page.title}",
                message=(
                    f"{c.nickname_snapshot} 님이 댓글을 남겼습니다.\n\n"
                    f"{c.body[:500]}\n\n"
                    f"--\n글: {page.title}\n링크: {page_url}#comment-{c.pk}\n"
                    f"통계 대시보드: {settings.WAGTAILADMIN_BASE_URL.rstrip('/')}/{settings.WAGTAIL_ADMIN_URL_PATH.rstrip('/')}/blog-stats/"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True,
            )
        except Exception as e:
            log.warning("comment email 실패: %s", e)
