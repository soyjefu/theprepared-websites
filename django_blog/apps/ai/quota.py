"""Gemini 무료 티어 보호 — 일일/분당 호출 카운터 (Redis)."""
from __future__ import annotations

from datetime import datetime

from django.core.cache import cache

DAILY_LIMIT = 200       # 일일 호출 상한 (조정)
PER_MINUTE_LIMIT = 5    # 분당 호출 상한


def _today() -> str:
    return datetime.utcnow().strftime("%Y%m%d")


def _now_minute() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M")


def consume(slot: str = "seo") -> bool:
    """quota 소비 시도. 가능하면 True, 한도 초과면 False."""
    day_key = f"gemini:{slot}:day:{_today()}"
    min_key = f"gemini:{slot}:min:{_now_minute()}"

    # atomic incr
    day_cnt = cache.get(day_key, 0)
    if day_cnt >= DAILY_LIMIT:
        return False
    min_cnt = cache.get(min_key, 0)
    if min_cnt >= PER_MINUTE_LIMIT:
        return False

    try:
        cache.incr(day_key)
    except ValueError:
        cache.set(day_key, 1, 60 * 60 * 26)
    try:
        cache.incr(min_key)
    except ValueError:
        cache.set(min_key, 1, 90)
    return True
