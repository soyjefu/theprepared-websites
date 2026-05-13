"""네이버 TV/블로그 영상 oEmbed Finder.

네이버는 oEmbed를 공식 제공하지 않으므로 URL 패턴 매칭 + OG 메타 fetch로 대체.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import socket
import urllib.parse
from typing import Optional

import requests
from bs4 import BeautifulSoup
from wagtail.embeds.finders.base import EmbedFinder
from wagtail.embeds.exceptions import EmbedNotFoundException

log = logging.getLogger(__name__)

_NAVER_TV = re.compile(r"^https?://(?:m\.)?tv\.naver\.com/v/(?P<vid>\d+)")
_NAVER_BLOG = re.compile(
    r"^https?://blog\.naver\.com/(?P<bid>[^/]+)/(?P<post_id>\d+)"
)

_ALLOWED_HOSTS = {
    "tv.naver.com", "m.tv.naver.com", "blog.naver.com", "m.blog.naver.com",
}


def _is_safe_host(url: str) -> bool:
    """SSRF 방어: 정규 네이버 호스트만, 그리고 사설 IP 차단."""
    try:
        host = urllib.parse.urlparse(url).hostname or ""
        if host.lower() not in _ALLOWED_HOSTS:
            return False
        ip = socket.gethostbyname(host)
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            return False
        return True
    except Exception:
        return False


def _fetch_og(url: str, timeout: float = 5.0) -> dict:
    if not _is_safe_host(url):
        raise EmbedNotFoundException("unsafe host")
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PreparedBlog/1.0; +https://theprepared.local)",
        "Accept-Language": "ko",
    }
    resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    og = {}
    for tag in soup.find_all("meta"):
        prop = tag.get("property") or tag.get("name") or ""
        if prop.startswith(("og:", "twitter:")):
            og[prop] = tag.get("content", "")
    return og


class NaverVideoEmbedFinder(EmbedFinder):
    def __init__(self, **options):
        self.options = options

    def accept(self, url: str) -> bool:
        return bool(_NAVER_TV.match(url) or _NAVER_BLOG.match(url))

    def find_embed(self, url: str, max_width: Optional[int] = None,
                   max_height: Optional[int] = None) -> dict:
        m = _NAVER_TV.match(url)
        if m:
            vid = m.group("vid")
            try:
                og = _fetch_og(url)
            except Exception as e:
                log.warning("naver og fetch failed for %s: %s", url, e)
                og = {}
            title = og.get("og:title", "네이버 TV 영상")
            thumb = og.get("og:image", "")
            iframe = (
                f'<iframe src="https://tv.naver.com/embed/{vid}" '
                'width="640" height="360" frameborder="0" allowfullscreen '
                'loading="lazy" referrerpolicy="no-referrer-when-downgrade" '
                'sandbox="allow-scripts allow-same-origin allow-popups"></iframe>'
            )
            return {
                "title": title,
                "author_name": "네이버 TV",
                "provider_name": "Naver",
                "type": "video",
                "thumbnail_url": thumb,
                "width": 640,
                "height": 360,
                "html": iframe,
            }
        m = _NAVER_BLOG.match(url)
        if m:
            try:
                og = _fetch_og(url)
            except Exception as e:
                log.warning("naver blog og fetch failed for %s: %s", url, e)
                raise EmbedNotFoundException(str(e))
            return {
                "title": og.get("og:title", ""),
                "author_name": og.get("og:site_name", "네이버 블로그"),
                "provider_name": "Naver",
                "type": "link",
                "thumbnail_url": og.get("og:image", ""),
                "width": 600,
                "height": 0,
                "html": (
                    f'<a class="naver-blog-card" href="{url}" target="_blank" '
                    f'rel="noopener noreferrer">{og.get("og:title", url)}</a>'
                ),
            }
        raise EmbedNotFoundException(f"unsupported url: {url}")
