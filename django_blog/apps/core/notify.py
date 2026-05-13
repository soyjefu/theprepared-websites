"""Discord webhook 알림 헬퍼 — 5xx/장애/관리자 이벤트용.

webhook URL은 settings.DISCORD_WEBHOOK_URL 또는 인자로 전달.
"""
from __future__ import annotations

import logging
import socket
import threading
import time

log = logging.getLogger(__name__)

# 같은 메시지 폭주 방지 — 1분 내 동일 fingerprint 재발송 차단
_recent_lock = threading.Lock()
_recent: dict[str, float] = {}
_THROTTLE_SEC = 60


def send_discord(
    message: str,
    *,
    title: str | None = None,
    color: int = 0xE74C3C,
    username: str = "The Prepared 알림",
    fingerprint: str | None = None,
    webhook_url: str | None = None,
) -> bool:
    """Discord webhook으로 메시지 발송.

    fingerprint가 주어지면 같은 fingerprint를 60초 내 재발송 안 함 (로그 폭주 방어).
    """
    import requests
    from django.conf import settings

    url = webhook_url or getattr(settings, "DISCORD_WEBHOOK_URL", "")
    if not url:
        return False

    # throttle
    if fingerprint:
        now = time.monotonic()
        with _recent_lock:
            # 만료된 항목 정리
            for k in [k for k, t in _recent.items() if now - t > _THROTTLE_SEC]:
                _recent.pop(k, None)
            if fingerprint in _recent:
                return False
            _recent[fingerprint] = now

    host = socket.gethostname()
    payload: dict = {"username": username}
    if title:
        payload["embeds"] = [{
            "title": title[:256],
            "description": message[:3500],
            "color": color,
            "footer": {"text": host},
        }]
    else:
        payload["content"] = f"[{host}] {message}"[:1900]

    try:
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code in (200, 204):
            return True
        log.warning("Discord webhook HTTP %s: %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        log.warning("Discord webhook 실패: %s", e)
        return False
