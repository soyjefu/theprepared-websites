"""Gemini API 호출 헬퍼 — invest의 패턴 차용 (429 backoff, JSON mode)."""
from __future__ import annotations

import logging
import time

from django.conf import settings

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SEC = 60
QUOTA_BACKOFF_SEC = 60
MAX_RETRIES = 2


def call_gemini(prompt: str, json_mode: bool = False, model: str | None = None) -> str:
    """Gemini 호출. 429 자동 재시도. 실패 시 raise."""
    from google import genai
    from google.genai import types

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 미설정")

    model = model or settings.GEMINI_MODEL
    client = genai.Client(api_key=api_key)

    cfg_kw = {}
    if json_mode:
        cfg_kw["response_mime_type"] = "application/json"
    config = types.GenerateContentConfig(**cfg_kw) if cfg_kw else None

    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            return resp.text
        except Exception as e:
            last_exc = e
            m = str(e).lower()
            transient = (
                "429" in m or "quota" in m or "rate limit" in m
                or "resource_exhausted" in m
                or "503" in m or "unavailable" in m or "overloaded" in m
            )
            if transient and attempt < MAX_RETRIES:
                wait = QUOTA_BACKOFF_SEC if "429" in m or "quota" in m else 15
                log.warning("[Gemini] transient(%s), %ss 대기 후 재시도 (%s/%s)",
                            m[:60], wait, attempt + 1, MAX_RETRIES)
                time.sleep(wait)
                continue
            raise
    raise last_exc or RuntimeError("Gemini 호출 실패")


def call_gemini_vision(prompt: str, image_bytes: bytes, mime_type: str = "image/jpeg",
                      model: str | None = None) -> str:
    """이미지 + 텍스트 multimodal 호출. alt 텍스트 생성 등에 사용."""
    from google import genai
    from google.genai import types

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 미설정")

    model = model or settings.GEMINI_MODEL
    client = genai.Client(api_key=api_key)

    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
            )
            return (resp.text or "").strip()
        except Exception as e:
            last_exc = e
            m = str(e).lower()
            transient = (
                "429" in m or "quota" in m or "rate limit" in m
                or "resource_exhausted" in m
                or "503" in m or "unavailable" in m or "overloaded" in m
            )
            if transient and attempt < MAX_RETRIES:
                wait = QUOTA_BACKOFF_SEC if "429" in m or "quota" in m else 15
                log.warning("[Gemini Vision] transient(%s), %ss 대기 후 재시도 (%s/%s)",
                            m[:60], wait, attempt + 1, MAX_RETRIES)
                time.sleep(wait)
                continue
            raise
    raise last_exc or RuntimeError("Gemini Vision 호출 실패")
