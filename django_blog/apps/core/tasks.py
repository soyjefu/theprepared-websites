"""Celery 주기 작업 — 셀프 모니터링.

ping 주기마다 사이트 /healthz/ 호출하여 down/up 상태 추적.
상태 전환(up→down, down→up) 시에만 Discord 알림 → 알림 폭주 없이 명확.
"""
from __future__ import annotations

import logging

from celery import shared_task

log = logging.getLogger(__name__)

STATE_KEY = "monitor:health:state"
DETAIL_KEY = "monitor:health:last_detail"
STATE_TTL = 86400 * 7  # 7일 (cache redis 재시작 시에도 일정 기간 유지)


def _check() -> tuple[str, str]:
    """현재 상태 측정. ('up' | 'down', detail) 반환."""
    import requests
    url = "https://theprepared.kr/healthz/"
    try:
        r = requests.get(url, timeout=10, allow_redirects=False)
    except requests.RequestException as e:
        return "down", f"네트워크 에러 — **{type(e).__name__}**: `{e}`"

    if r.status_code != 200:
        return "down", f"HTTP **{r.status_code}**\nbody: ```\n{r.text[:300]}\n```"

    # /healthz/ JSON에서 DB ping 결과 확인
    try:
        data = r.json()
        if not data.get("ok"):
            return "down", f"healthz ok=false ```\n{r.text[:300]}\n```"
    except Exception:
        pass

    return "up", "정상"


@shared_task
def self_ping_healthz() -> dict:
    """주기 ping. 상태 전환(up↔down) 시에만 Discord 알림."""
    from django.core.cache import cache
    from .notify import send_discord

    new_state, detail = _check()
    prev_state = cache.get(STATE_KEY)

    cache.set(STATE_KEY, new_state, STATE_TTL)
    cache.set(DETAIL_KEY, detail, STATE_TTL)

    # 첫 ping 또는 동일 상태 → 알림 없음
    if prev_state is None or prev_state == new_state:
        return {"state": new_state, "changed": False, "detail": detail[:200]}

    # 상태 전환
    if new_state == "down":
        send_discord(
            f"{detail}\n\nURL: https://theprepared.kr/healthz/",
            title="🔴 사이트 응답 끊김",
            color=0xE74C3C,
        )
    else:  # up
        last = cache.get(DETAIL_KEY + ":down") or ""
        send_discord(
            f"정상 응답으로 복귀했다.{(' 직전 상태: ' + last) if last else ''}",
            title="🟢 사이트 복구됨",
            color=0x2ECC71,
        )

    # down 직전 detail은 별도 키로 보존 (복구 알림에 포함)
    if new_state == "down":
        cache.set(DETAIL_KEY + ":down", detail, STATE_TTL)

    return {"state": new_state, "changed": True, "prev": prev_state, "detail": detail[:200]}
