"""WordPress Gutenberg 블록 파서 → Wagtail StreamField JSON 변환기.

블록 토큰 형식:
    <!-- wp:TYPE {JSON_ATTRS}? -->
        INNER_HTML
    <!-- /wp:TYPE -->
또는 self-closing:
    <!-- wp:TYPE {JSON_ATTRS}? /-->

매칭 안 되거나 알 수 없는 블록은 paragraph(RichText)로 폴백.
이미지/임베드 등 본문에 등장하는 wp_id 는 별도 매퍼(callable)로 Wagtail PK 변환.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# 블록 토큰: 그룹 = (type, attrs_json, self_closing_slash)
BLOCK_RE = re.compile(
    r"<!--\s*wp:([a-z0-9/_-]+)\s*(\{.*?\})?\s*(/)?\s*-->",
    re.DOTALL,
)
# 닫기 토큰
CLOSE_RE = re.compile(r"<!--\s*/wp:([a-z0-9/_-]+)\s*-->")

# RichText 안전 태그 화이트리스트 (Wagtail 기본 + 우리 features)
ALLOWED_RICH_TAGS = {
    "p", "br", "strong", "em", "b", "i", "u", "a", "ul", "ol", "li",
    "blockquote", "code", "pre", "hr", "h2", "h3", "h4",
}


@dataclass
class ParsedBlock:
    type: str
    attrs: dict = field(default_factory=dict)
    inner_html: str = ""
    children: List["ParsedBlock"] = field(default_factory=list)
    self_closing: bool = False


def parse(content: str) -> List[ParsedBlock]:
    """본문 HTML을 ParsedBlock 트리로 변환."""
    blocks: List[ParsedBlock] = []
    pos = 0
    while pos < len(content):
        m = BLOCK_RE.search(content, pos)
        if not m:
            tail = content[pos:].strip()
            if tail:
                blocks.append(ParsedBlock(type="__raw_html__", inner_html=tail))
            break
        # 토큰 앞 잔여 텍스트
        if m.start() > pos:
            chunk = content[pos:m.start()].strip()
            if chunk:
                blocks.append(ParsedBlock(type="__raw_html__", inner_html=chunk))

        btype, attrs_json, slash = m.group(1), m.group(2), m.group(3)
        attrs = {}
        if attrs_json:
            try:
                attrs = json.loads(attrs_json)
            except json.JSONDecodeError as e:
                log.warning("attrs JSON 파싱 실패 (%s): %s", btype, e)
                attrs = {}

        if slash:
            blocks.append(ParsedBlock(type=btype, attrs=attrs, self_closing=True))
            pos = m.end()
            continue

        # 매칭 닫기 토큰 찾기 (중첩 같은 type 허용)
        depth = 1
        scan = m.end()
        end_close = None
        while scan < len(content):
            nm = BLOCK_RE.search(content, scan)
            cm = CLOSE_RE.search(content, scan)
            if not cm:
                break
            if nm and nm.start() < cm.start() and not nm.group(3):
                if nm.group(1) == btype:
                    depth += 1
                scan = nm.end()
            else:
                if cm.group(1) == btype:
                    depth -= 1
                    if depth == 0:
                        end_close = cm
                        break
                scan = cm.end()
        if end_close is None:
            log.warning("닫기 토큰 못 찾음: wp:%s", btype)
            blocks.append(ParsedBlock(type=btype, attrs=attrs, inner_html=content[m.end():]))
            break

        inner = content[m.end():end_close.start()].strip()
        # 안에 nested wp 블록이 있으면 재귀
        nested = parse(inner) if "<!-- wp:" in inner else []
        blocks.append(ParsedBlock(
            type=btype,
            attrs=attrs,
            inner_html=inner,
            children=nested,
        ))
        pos = end_close.end()
    return blocks


# ---------------------------------------------------------------- #
# 블록 → StreamField item 변환
# ---------------------------------------------------------------- #
ImageMapper = Callable[[int], Optional[int]]  # wp_attachment_id -> CustomImage pk


def _slug_anchor(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text or "").strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    return s[:80]


def _safe_richtext(html: str) -> str:
    """HTML 잔여물을 RichText 안전 형태로. 알 수 없는 태그는 strip."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in ALLOWED_RICH_TAGS:
            tag.unwrap()
        else:
            # 위험 속성 제거
            for attr in list(tag.attrs):
                if attr in ("style", "onclick", "onerror", "onload"):
                    del tag.attrs[attr]
                if tag.name == "a" and attr not in ("href", "target", "rel"):
                    del tag.attrs[attr]
    return str(soup)


def _convert_paragraph(b: ParsedBlock) -> Optional[dict]:
    html = _safe_richtext(b.inner_html)
    if not html.strip():
        return None
    return {"type": "paragraph", "value": html}


def _convert_heading(b: ParsedBlock) -> Optional[dict]:
    soup = BeautifulSoup(b.inner_html, "html.parser")
    level = b.attrs.get("level", 2)
    h = soup.find(["h1", "h2", "h3", "h4", "h5", "h6"])
    text = (h.get_text(strip=True) if h else soup.get_text(strip=True))[:200]
    if not text:
        return None
    lvl_str = {1: "h2", 2: "h2", 3: "h3", 4: "h4", 5: "h4", 6: "h4"}.get(int(level), "h2")
    return {
        "type": "heading",
        "value": {"text": text, "level": lvl_str, "anchor": _slug_anchor(text)},
    }


def _convert_image(b: ParsedBlock, image_mapper: ImageMapper) -> Optional[dict]:
    wp_id = b.attrs.get("id")
    pk = image_mapper(int(wp_id)) if wp_id else None
    if not pk:
        return None
    soup = BeautifulSoup(b.inner_html, "html.parser")
    img = soup.find("img")
    cap = soup.find("figcaption")
    alt = (img.get("alt") if img else "") or ""
    link_el = soup.find("a")
    link = (link_el.get("href") if link_el else "") or ""
    # linkDestination "none" 이면 링크 없는 것으로
    if b.attrs.get("linkDestination") in ("none", None) and (not link or "wp-content" in link):
        link = ""
    return {
        "type": "image",
        "value": {
            "image": pk,
            "caption": (cap.get_text(strip=True) if cap else "")[:200],
            "alt_override": alt[:200],
            "link": link,
        },
    }


def _convert_quote(b: ParsedBlock) -> Optional[dict]:
    soup = BeautifulSoup(b.inner_html, "html.parser")
    cite = soup.find("cite")
    text = soup.get_text("\n", strip=True)
    if cite:
        text = text.replace(cite.get_text(strip=True), "").strip()
    if not text:
        return None
    return {
        "type": "quote",
        "value": {"text": text[:5000], "attribution": (cite.get_text(strip=True) if cite else "")[:200]},
    }


def _convert_code(b: ParsedBlock) -> Optional[dict]:
    soup = BeautifulSoup(b.inner_html, "html.parser")
    code = soup.find("code") or soup.find("pre")
    code_text = code.get_text() if code else b.inner_html
    return {"type": "code", "value": {"language": "plain", "code": code_text}}


def _convert_embed(b: ParsedBlock) -> Optional[dict]:
    url = b.attrs.get("url") or ""
    if not url:
        soup = BeautifulSoup(b.inner_html, "html.parser")
        link = soup.find("a")
        url = (link.get("href") if link else "") or ""
    if not url:
        return None
    return {"type": "embed", "value": url}


def _convert_list(b: ParsedBlock) -> Optional[dict]:
    return _convert_paragraph(b)  # <ul>/<ol>는 RichText에서 허용


def _convert_separator(b: ParsedBlock) -> Optional[dict]:
    return {"type": "paragraph", "value": "<hr>"}


def _convert_html(b: ParsedBlock) -> Optional[dict]:
    # 보안: raw HTML 차단 — 태그 strip 후 텍스트만
    text = BeautifulSoup(b.inner_html, "html.parser").get_text(" ", strip=True)
    if not text:
        return None
    return {"type": "paragraph", "value": _safe_richtext(f"<p>{text}</p>")}


def _convert_raw(b: ParsedBlock) -> Optional[dict]:
    html = _safe_richtext(b.inner_html)
    if not html.strip():
        return None
    return {"type": "paragraph", "value": html}


CONVERTERS = {
    "paragraph": _convert_paragraph,
    "heading": _convert_heading,
    "image": _convert_image,
    "quote": _convert_quote,
    "pullquote": _convert_quote,
    "code": _convert_code,
    "preformatted": _convert_code,
    "embed": _convert_embed,
    "list": _convert_list,
    "list-item": _convert_list,
    "separator": _convert_separator,
    "spacer": _convert_separator,
    "html": _convert_html,
    "__raw_html__": _convert_raw,
}


def to_streamfield(content: str, image_mapper: ImageMapper) -> List[dict]:
    """본문 HTML → StreamField item 리스트.

    image_mapper(wp_attachment_id) -> CustomImage.pk (없으면 None)
    """
    blocks = parse(content)
    items: List[dict] = []
    for b in blocks:
        # core-embed/youtube 같은 변형: prefix 제거
        btype = b.type.split("/")[-1].split("-embed-")[-1] if "embed" in b.type else b.type
        if btype.startswith("core/"):
            btype = btype[len("core/"):]
        # core-embed/* 처리
        if b.type.startswith("core-embed/"):
            btype = "embed"
            if not b.attrs.get("url"):
                # innerHTML에서 URL 추출
                soup = BeautifulSoup(b.inner_html, "html.parser")
                link = soup.find("a")
                if link:
                    b.attrs["url"] = link.get("href", "")

        conv = CONVERTERS.get(btype)
        if conv is None:
            # gallery: children이 image들이면 풀어서 image 블록 여럿
            if btype == "gallery":
                for child in b.children:
                    if child.type == "image":
                        item = _convert_image(child, image_mapper)
                        if item:
                            items.append(item)
                continue
            # 알 수 없는 블록 → 안전 RichText 폴백
            item = _convert_raw(b)
        else:
            item = conv(b, image_mapper) if btype == "image" else conv(b)

        if item:
            items.append(item)
    return items
