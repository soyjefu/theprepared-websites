"""SEO 자동 생성 — Gemini로 description/keywords/summary/alt 생성 → 페이지에 반영."""
from __future__ import annotations

import json
import logging

from celery import shared_task
from django.utils import timezone

from .gemini_client import call_gemini
from .quota import consume

log = logging.getLogger(__name__)

PROMPT_TPL = """당신은 원문 글쓴이 본인입니다.
SNS·검색결과 미리보기에 노출될 description을 본인 글의 도입부 어조 그대로 한 문장으로 다시 씁니다.

== 절대 금지 표현 ==
- "...담았습니다" / "...담은 글입니다"
- "...소개합니다" / "...소개하는 글"
- "...기록입니다" / "...기록한 글"
- "...다룬 글" / "...다룹니다"
- "이 글은 ...", "...에 대한 이야기"
- "...에세이입니다", "...일기입니다", "...단상입니다"
- 모든 "~습니다", "~합니다", "~입니다", "~예요", "~네요" 합쇼체·해요체 어미
→ 외부 화자의 요약 톤이거나 본문 톤과 어긋남.

== 어미 (필수) ==
- 평서 반말 종결: "~다", "~했다", "~였다", "~해졌다", "~던 날", "~한 순간".
- 또는 명사형 종결로 마무리.
- 합쇼체·해요체 절대 금지.

== 톤 ==
- 작가 본인이 본문 도입부를 한 문장으로 압축한 톤.
- 본문에서 실제로 등장한 단어·이미지·정서만 사용.
- 한 문장, 70~140자.
- 따옴표·이모지·markdown·해시태그 금지.

== 예시 ==
원문: "달 밝은 밤이었다. 오랜만에 기분이 좋아서 술 한 잔 하고 들어왔다."
좋은: "달 밝은 밤, 오랜만에 기분이 좋아 술 한 잔 걸치고 돌아왔다."
나쁜: "달 밝은 밤에 느낀 감상을 담았습니다." ← "담았습니다" 금지

원문: "12월의 상하이는 차가운 바람과 따뜻한 음식이 공존하는 도시였다."
좋은: "12월의 상하이, 차가운 바람과 따뜻한 음식이 함께 있던 닷새가 그렇게 흘러갔다."
나쁜: "12월 상하이 여행을 기록한 글입니다." ← 금지

원문: "겨울 산은 늘 새벽보다 더 조용하다."
좋은: "겨울 산은 늘 새벽보다 더 조용했다."
나쁜: "겨울 산의 적막함을 담은 글입니다." ← 금지

== 입력 ==
제목: {title}

원문 본문 + 이미지 캡션:
{body}

== 출력 (JSON만) ==
{{
  "description": "...(평서 반말 한 문장, 70~140자)",
  "keywords": ["...", "..."],
  "summary": "...(150~250자, 평서 반말, 같은 금지)",
  "suggested_tags": ["...", "..."]
}}
"""


def _plaintext_from_streamfield(body) -> str:
    """StreamField → plaintext (앞 4000자). 이미지 캡션도 포함."""
    parts = []
    try:
        raw = body.raw_data if hasattr(body, "raw_data") else json.loads(str(body) or "[]")
    except Exception:
        return ""
    for item in raw or []:
        t = item.get("type")
        if t == "paragraph":
            parts.append(_strip_html(item.get("value", "")))
        elif t == "heading":
            parts.append((item.get("value") or {}).get("text", ""))
        elif t == "quote":
            parts.append((item.get("value") or {}).get("text", ""))
        elif t == "image":
            cap = (item.get("value") or {}).get("caption") or ""
            if cap:
                parts.append(cap)
    return " ".join(p for p in parts if p)[:4000]


def _strip_html(html: str) -> str:
    from bs4 import BeautifulSoup
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


@shared_task(bind=True, max_retries=1, default_retry_delay=120)
def generate_seo_meta(self, page_id: int, force: bool = False) -> dict:
    """BlogPostPage SEO 메타 자동 생성/갱신."""
    from apps.blog.models import BlogPostPage

    page = BlogPostPage.objects.filter(pk=page_id).first()
    if page is None:
        return {"status": "missing"}
    if page.seo_auto_locked and not force:
        return {"status": "locked"}

    if not consume("seo"):
        log.warning("Gemini quota 한도 초과, page=%s skip", page_id)
        return {"status": "quota_exceeded"}

    body_text = _plaintext_from_streamfield(page.body)
    if len(body_text) < 50:
        # 본문이 너무 짧으면 Gemini 호출 대신 본문 텍스트를 그대로 description/intro로
        if body_text:
            changed = False
            if body_text != page.search_description:
                page.search_description = body_text[:300]
                changed = True
            if not page.intro:
                page.intro = body_text[:240]
                changed = True
            if changed:
                page.seo_auto_generated_at = timezone.now()
                page.save()
                page.save_revision().publish()
            return {"status": "too_short_used_body", "len": len(body_text), "changed": changed}
        return {"status": "too_short"}

    prompt = PROMPT_TPL.format(title=page.title, body=body_text)
    try:
        raw = call_gemini(prompt, json_mode=True)
    except Exception as e:
        log.warning("Gemini 호출 실패 page=%s: %s", page_id, e)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            pass
        return {"status": "error", "reason": str(e)[:200]}

    try:
        data = json.loads(raw)
    except Exception as e:
        log.warning("JSON 파싱 실패 page=%s: %s\n%s", page_id, e, raw[:300])
        return {"status": "parse_error"}

    desc = (data.get("description") or "")[:300]
    summary = (data.get("summary") or "")[:500]
    tags = data.get("suggested_tags") or []

    changed = False
    if desc and desc != page.search_description:
        page.search_description = desc
        changed = True
    if not page.intro and summary:
        page.intro = summary[:240]
        changed = True

    page.seo_auto_generated_at = timezone.now()
    page.save()

    # 태그 추가 (기존 + 새것 합집합)
    if tags:
        existing = {t.name for t in page.tags.all()}
        merged = sorted(existing | {str(t)[:40] for t in tags if t})
        if set(merged) != existing:
            page.tags.set(merged)
            page.save()
            changed = True

    if changed:
        page.save_revision().publish()

    return {"status": "ok", "changed": changed, "n_tags": len(tags)}


ALT_PROMPT = """이 이미지의 핵심 시각 정보를 한국어 한 문장으로 묘사해줘.
- 사용자가 이미지를 못 볼 때 무엇을 보고 있는지 알 수 있게.
- 사람·풍경·사물의 위치/색/분위기 위주. "~다" 평서 반말 종결.
- 60자 이내. 따옴표/이모지/markdown 금지.
- 로고/아이콘이면 "<브랜드명> 로고/아이콘"으로 간단히.
- 추측·해석은 빼고 보이는 것만.
출력: 문장 한 줄."""


@shared_task(bind=True, max_retries=1, default_retry_delay=120)
def generate_image_alt(self, image_id: int, force: bool = False) -> dict:
    """CustomImage의 alt_text를 Gemini Vision으로 자동 생성."""
    from apps.images.models import CustomImage
    from .gemini_client import call_gemini_vision

    img = CustomImage.objects.filter(pk=image_id).first()
    if img is None:
        return {"status": "missing"}
    if img.alt_text and not force:
        return {"status": "already_set"}

    if not consume("alt"):
        log.warning("Gemini alt quota 한도 초과, image=%s skip", image_id)
        return {"status": "quota_exceeded"}

    # 작은 rendition 사용 (quota·시간 절약). 실패 시 원본.
    try:
        r = img.get_rendition("width-800")
        with r.file.open("rb") as f:
            data = f.read()
        mime = "image/jpeg" if r.url.endswith((".jpg", ".jpeg")) else "image/png"
        if r.url.endswith(".webp"):
            mime = "image/webp"
    except Exception as e:
        log.warning("rendition 실패, 원본 사용 image=%s: %s", image_id, e)
        try:
            with img.file.open("rb") as f:
                data = f.read()
            mime = "image/jpeg"
        except Exception as e2:
            return {"status": "read_error", "reason": str(e2)[:100]}

    try:
        alt = call_gemini_vision(ALT_PROMPT, data, mime_type=mime)
    except Exception as e:
        log.warning("Gemini Vision 실패 image=%s: %s", image_id, e)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            pass
        return {"status": "error", "reason": str(e)[:200]}

    alt = (alt or "").strip().strip('"').strip("'").splitlines()[0][:200]
    if not alt:
        return {"status": "empty_response"}

    img.alt_text = alt
    img.ai_generated_alt = True
    img.save(update_fields=["alt_text", "ai_generated_alt"])
    return {"status": "ok", "alt": alt}


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def notify_indexnow(self, url: str) -> dict:
    """IndexNow로 단일 URL을 Bing/Yandex에 즉시 통보. publish signal에서 호출."""
    import requests
    from django.conf import settings

    key = getattr(settings, "INDEXNOW_KEY", "")
    if not key:
        return {"status": "no_key"}
    if not url.startswith("https://theprepared.kr/"):
        return {"status": "wrong_host"}

    payload = {
        "host": "theprepared.kr",
        "key": key,
        "keyLocation": f"https://theprepared.kr/{key}.txt",
        "urlList": [url],
    }
    try:
        r = requests.post(
            "https://api.indexnow.org/IndexNow",
            json=payload, timeout=10,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        if r.status_code in (200, 202):
            return {"status": "ok", "http": r.status_code, "url": url}
        log.warning("IndexNow HTTP %s for %s: %s", r.status_code, url, r.text[:200])
        if r.status_code in (429, 500, 502, 503, 504):
            try:
                self.retry()
            except self.MaxRetriesExceededError:
                pass
        return {"status": "http_error", "http": r.status_code}
    except requests.RequestException as e:
        log.warning("IndexNow network error for %s: %s", url, e)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            pass
        return {"status": "network_error", "reason": str(e)[:200]}
