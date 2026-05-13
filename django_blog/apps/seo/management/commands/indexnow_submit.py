"""IndexNow 일괄 통보 — Bing/Yandex에 URL 목록을 즉시 알린다.

sitemap.xml에서 URL을 끌어오거나 `--urls` 인자로 직접 줄 수 있다.
1회 호출당 최대 10000 URL. 우리는 사이트 규모상 1회로 충분.

Naver는 IndexNow 미참여 (2026년 5월 기준). 별도로 서치어드바이저
사이트맵 제출이 필요하다.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


SITEMAP_URL = "https://theprepared.kr/sitemap.xml"
INDEXNOW_ENDPOINTS = [
    "https://api.indexnow.org/IndexNow",   # 모든 참여 엔진에 fan-out
    # 개별 엔진 직접 호출도 가능하지만 위 한 곳이면 Bing/Yandex 모두 커버됨
]


class Command(BaseCommand):
    help = "IndexNow로 모든 사이트 URL 색인 통보 (Bing/Yandex)"

    def add_arguments(self, parser):
        parser.add_argument("--sitemap", default=SITEMAP_URL,
                            help="URL 추출에 사용할 sitemap.xml")
        parser.add_argument("--urls", nargs="*", default=None,
                            help="직접 URL 지정 (sitemap 무시)")
        parser.add_argument("--dry-run", action="store_true",
                            help="전송하지 않고 출력만")

    def handle(self, *args, **opts):
        key = getattr(settings, "INDEXNOW_KEY", "")
        if not key:
            raise CommandError("INDEXNOW_KEY 가 .env 에 없습니다.")

        # 1) URL 수집
        if opts["urls"]:
            urls = opts["urls"]
        else:
            urls = self._fetch_sitemap_urls(opts["sitemap"])

        urls = [u for u in urls if u.startswith("https://theprepared.kr/")]
        if not urls:
            raise CommandError("통보할 URL이 없습니다.")

        host = "theprepared.kr"
        key_location = f"https://{host}/{key}.txt"

        self.stdout.write(f"host={host}, key={key[:8]}..., urls={len(urls)}")
        for u in urls[:3]:
            self.stdout.write(f"  · {u}")
        if len(urls) > 3:
            self.stdout.write(f"  ... +{len(urls)-3}건")

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("--dry-run: 전송 생략"))
            return

        payload = {
            "host": host,
            "key": key,
            "keyLocation": key_location,
            "urlList": urls,
        }

        for ep in INDEXNOW_ENDPOINTS:
            try:
                r = requests.post(ep, json=payload, timeout=15,
                                  headers={"Content-Type": "application/json; charset=utf-8"})
                # IndexNow 응답: 200(ok), 202(accepted), 400(잘못된 요청),
                # 403(키 파일 미확인), 422(URL이 host에 안 맞음), 429(rate limit)
                msg = f"{ep} → HTTP {r.status_code}"
                if r.status_code in (200, 202):
                    self.stdout.write(self.style.SUCCESS(msg))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"{msg} body={r.text[:200]!r}"
                    ))
            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f"{ep} → {e}"))

    @staticmethod
    def _fetch_sitemap_urls(url: str) -> list[str]:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        return [loc.text.strip() for loc in root.findall(".//sm:loc", ns) if loc.text]
