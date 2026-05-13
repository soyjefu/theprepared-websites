"""주소 → 위/경도 변환 (NCP geocoding API). 영속 캐시 + 메모리 캐시."""
from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

import requests
from django.conf import settings
from django.core.cache import cache

from .models import GeocodeCache

log = logging.getLogger(__name__)

NCP_GEOCODE_URL = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"


def _normalize(address: str) -> str:
    return re.sub(r"\s+", " ", (address or "")).strip()[:240]


def geocode(address: str, provider: str = "naver") -> Tuple[Optional[float], Optional[float]]:
    """주소 → (lat, lng). 실패 시 (None, None)."""
    norm = _normalize(address)
    if not norm:
        return None, None

    # 1) Redis 짧은 캐시 (1h)
    redis_key = f"geocode:{provider}:{hash(norm)}"
    hit = cache.get(redis_key)
    if hit is not None:
        return hit

    # 2) DB 캐시
    rec = GeocodeCache.objects.filter(address_norm=norm, provider=provider).first()
    if rec:
        if rec.failed:
            cache.set(redis_key, (None, None), 60 * 60)
            return None, None
        if rec.lat is not None and rec.lng is not None:
            res = (float(rec.lat), float(rec.lng))
            cache.set(redis_key, res, 60 * 60)
            return res

    # 3) NCP API 호출
    if provider != "naver":
        log.warning("provider=%s 미지원, naver로 진행", provider)
    cid = settings.NAVER_MAP_NCP_CLIENT_ID
    csec = settings.NAVER_MAP_NCP_CLIENT_SECRET
    if not (cid and csec):
        log.info("NCP 키 미설정 — geocoding skip")
        # 키 없으면 실패 캐시(짧게)만
        cache.set(redis_key, (None, None), 60 * 60)
        return None, None

    try:
        resp = requests.get(
            NCP_GEOCODE_URL,
            params={"query": norm},
            headers={
                "X-NCP-APIGW-API-KEY-ID": cid,
                "X-NCP-APIGW-API-KEY": csec,
            },
            timeout=4.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning("NCP geocode 실패: %s", e)
        GeocodeCache.objects.update_or_create(
            address_norm=norm, provider=provider,
            defaults={"failed": True, "failure_reason": str(e)[:200]},
        )
        cache.set(redis_key, (None, None), 60 * 60)
        return None, None

    addrs = data.get("addresses") or []
    if not addrs:
        GeocodeCache.objects.update_or_create(
            address_norm=norm, provider=provider,
            defaults={"failed": True, "failure_reason": "no result"},
        )
        cache.set(redis_key, (None, None), 60 * 60)
        return None, None

    lat = float(addrs[0]["y"])
    lng = float(addrs[0]["x"])
    GeocodeCache.objects.update_or_create(
        address_norm=norm, provider=provider,
        defaults={"lat": lat, "lng": lng, "failed": False, "failure_reason": ""},
    )
    cache.set(redis_key, (lat, lng), 60 * 60)
    return lat, lng
