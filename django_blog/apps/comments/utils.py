"""댓글 관련 헬퍼 — IP 해시, visitor token, time-trap, sanitize."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Optional

import bleach
from django.conf import settings
from django.core.signing import BadSignature, TimestampSigner

URL_RE = re.compile(r"https?://", re.IGNORECASE)
HANGUL_RE = re.compile(r"[가-힣]")


def hmac_hash(value: str, salt: str = "") -> str:
    key = (settings.VISITOR_TOKEN_SECRET + salt).encode()
    return hmac.new(key, (value or "").encode(), hashlib.sha256).hexdigest()


def ip_hash(ip: str) -> str:
    return hmac_hash(ip or "", salt="ip")


def ua_hash(ua: str) -> str:
    return hmac_hash(ua or "", salt="ua")


def make_visitor_token() -> tuple[str, str]:
    """(원본 토큰, 해시) — 원본은 쿠키, 해시는 DB."""
    raw = secrets.token_urlsafe(32)
    return raw, hmac_hash(raw, salt="visitor")


def visitor_token_hash(raw_token: str) -> str:
    return hmac_hash(raw_token or "", salt="visitor")


# ----- time-trap (폼 렌더 시각 서명) -----
def make_form_token() -> str:
    return TimestampSigner(salt=settings.COMMENT_FORM_TIMETRAP_SECRET).sign("form")


def verify_form_token(token: str, min_seconds: int = 3, max_seconds: int = 60 * 60 * 24) -> Optional[float]:
    """검증 OK면 elapsed 초, 너무 빠르거나 만료면 None."""
    if not token:
        return None
    try:
        signer = TimestampSigner(salt=settings.COMMENT_FORM_TIMETRAP_SECRET)
        # unsign은 토큰의 timestamp 만료(max_age)를 함께 검사
        signer.unsign(token, max_age=max_seconds)
        # 추가로 너무 빠른 제출 차단
        parts = token.split(":")
        if len(parts) < 3:
            return None
        from django.core.signing import b62_decode
        ts = b62_decode(parts[1])
        from time import time
        elapsed = time() - ts
        if elapsed < min_seconds:
            return None
        return elapsed
    except BadSignature:
        return None
    except Exception:
        return None


# ----- sanitize -----
def sanitize_body(text: str) -> tuple[str, str]:
    """반환: (plain_for_db, html_for_render)"""
    plain = bleach.clean(text or "", tags=[], attributes={}, strip=True)
    plain = (plain or "").strip()
    # autolink
    html = bleach.linkify(
        bleach.clean(plain, tags=["br"], attributes={}, strip=True).replace("\n", "<br>"),
        callbacks=[
            lambda attrs, new=False: {**attrs, (None, "rel"): "nofollow ugc noopener", (None, "target"): "_blank"},
        ],
    )
    return plain, html


def heuristic_spam_score(plain: str) -> tuple[float, str]:
    """본문 휴리스틱 → (score 0~1, reason)."""
    if not plain:
        return 1.0, "empty"
    n_url = len(URL_RE.findall(plain))
    n_hangul = len(HANGUL_RE.findall(plain))
    n_chars = max(len(plain), 1)

    score = 0.0
    reasons = []
    if n_url >= 5:
        score += 0.6; reasons.append(f"url_high={n_url}")
    elif n_url >= 3:
        score += 0.35; reasons.append(f"url_mid={n_url}")
    if n_hangul / n_chars < 0.20 and n_url >= 1:
        score += 0.5; reasons.append("low_hangul_ratio_with_url")
    if len(plain) < 3:
        score += 0.6; reasons.append("too_short")
    if len(plain) > 5000:
        score += 0.5; reasons.append("too_long")
    return min(score, 1.0), ",".join(reasons)


def get_client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
