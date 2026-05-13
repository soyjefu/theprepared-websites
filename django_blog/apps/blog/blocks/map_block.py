"""주소 → 인라인 지도 (네이버 기본 / 구글 옵션) StreamField 블록."""
from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from wagtail import blocks


class MapBlock(blocks.StructBlock):
    address = blocks.CharBlock(
        max_length=200, required=True,
        help_text="예: 서울 강남구 테헤란로 152",
    )
    label = blocks.CharBlock(
        required=False, max_length=80,
        help_text="지도 위 표시명 (장소 이름 등)",
    )
    provider = blocks.ChoiceBlock(
        choices=[("naver", "네이버 지도"), ("google", "구글 지도")],
        default="naver",
        help_text="지도 제공자",
    )
    zoom = blocks.IntegerBlock(default=16, min_value=1, max_value=20)
    height = blocks.IntegerBlock(default=360, min_value=180, max_value=720)
    show_link = blocks.BooleanBlock(
        default=True, required=False,
        help_text="‘지도에서 열기’ 버튼 표시",
    )

    class Meta:
        icon = "site"
        template = "blog/blocks/map.html"
        preview_template = "blog/blocks/map.html"
        preview_value = {"address": "서울 강남구 테헤란로 152", "provider": "naver"}
        label = "지도"

    def get_context(self, value, parent_context=None):
        from apps.core.geocoding import geocode
        ctx = super().get_context(value, parent_context)
        addr = value.get("address", "")
        provider = value.get("provider", "naver")
        lat, lng = geocode(addr, provider="naver")  # geocoding은 항상 NCP (정확도 우선)
        ctx["lat"] = lat
        ctx["lng"] = lng
        ctx["addr_quoted"] = quote(addr)
        ctx["external_url"] = (
            f"https://map.naver.com/p/search/{quote(addr)}"
            if provider == "naver"
            else f"https://www.google.com/maps/search/?api=1&query={quote(addr)}"
        )
        ctx["google_embed_key"] = settings.GOOGLE_MAPS_API_KEY
        ctx["naver_client_id"] = settings.NAVER_MAP_NCP_CLIENT_ID
        return ctx
