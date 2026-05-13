"""Celery beat PeriodicTask 등록 — self_ping_healthz 5분마다.

idempotent: 재실행해도 중복 등록 안 됨.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "5분마다 사이트 self-ping을 수행하는 PeriodicTask 등록"

    def handle(self, *args, **opts):
        from django_celery_beat.models import IntervalSchedule, PeriodicTask

        interval, _ = IntervalSchedule.objects.get_or_create(
            every=2, period=IntervalSchedule.MINUTES,
        )
        task, created = PeriodicTask.objects.update_or_create(
            name="self_ping_healthz",
            defaults={
                "task": "apps.core.tasks.self_ping_healthz",
                "interval": interval,
                "enabled": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"PeriodicTask {'created' if created else 'updated'}: {task.name} every 2m"
        ))

        # 옛 5분 IntervalSchedule이 안 쓰이면 정리 (orphan 방지)
        IntervalSchedule.objects.filter(
            every=5, period=IntervalSchedule.MINUTES, periodictask__isnull=True,
        ).delete()

        # cache 상태 초기화 — 다음 ping이 첫 ping으로 동작 (오작동 알림 방지)
        from django.core.cache import cache
        from apps.core.tasks import STATE_KEY, DETAIL_KEY
        cache.delete(STATE_KEY)
        cache.delete(DETAIL_KEY)
        cache.delete(DETAIL_KEY + ":down")

        # Discord 테스트 발송
        from apps.core.notify import send_discord
        ok = send_discord(
            "셀프 모니터링이 활성화됐다. 사이트 응답 이상 시 이 채널로 알림.",
            title="✅ 모니터링 활성화",
            color=0x2ECC71,
        )
        self.stdout.write(self.style.SUCCESS(
            f"Discord 테스트: {'발송 성공' if ok else '실패 (URL/네트워크 확인)'}"
        ))
