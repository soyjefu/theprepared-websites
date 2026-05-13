"""사이트 헤더/푸터 설정 — Wagtail admin '설정' 메뉴에서 편집."""
from __future__ import annotations

from django.db import models
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import StreamField
from wagtail.images import get_image_model_string


class _MenuItem(blocks.StructBlock):
    label = blocks.CharBlock(max_length=40, required=True)
    url = blocks.CharBlock(max_length=240, required=True,
                           help_text="내부 경로(/blog/society/) 또는 외부 URL")


class _DropdownMenu(blocks.StructBlock):
    label = blocks.CharBlock(max_length=40, required=True, help_text="드롭다운 버튼 텍스트 (예: Blog)")
    items = blocks.ListBlock(_MenuItem(), label="하위 메뉴")

    class Meta:
        icon = "list-ul"


class _LinkBlock(blocks.StructBlock):
    label = blocks.CharBlock(max_length=40, required=True)
    url = blocks.CharBlock(max_length=240, required=True)

    class Meta:
        icon = "link"


class _NavStream(blocks.StreamBlock):
    dropdown = _DropdownMenu()
    link = _LinkBlock()


@register_setting(icon="cogs")
class NavSettings(BaseSiteSetting):
    """헤더/푸터 네비게이션 + 사이트 메타."""

    site_name_override = models.CharField(
        max_length=80, blank=True,
        help_text="(선택) 사이트 제목 덮어쓰기. 비워두면 WAGTAIL_SITE_NAME 사용",
    )
    tagline_override = models.CharField(
        max_length=240, blank=True,
        help_text="(선택) 푸터 태그라인 덮어쓰기",
    )
    default_og_image = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="글 없는 페이지에 공유될 기본 OG/소셜 썸네일",
    )
    header_menu = StreamField(
        _NavStream(), use_json_field=True, blank=True,
        help_text="헤더 메뉴 항목 (드롭다운/단일 링크)",
    )
    footer_menu = StreamField(
        _NavStream(), use_json_field=True, blank=True,
        help_text="푸터 메뉴 항목",
    )
    footer_extra = models.CharField(
        max_length=240, blank=True,
        help_text="푸터 하단 한 줄 (예: © 2026 …)",
    )
    ga4_measurement_id = models.CharField(
        max_length=20, blank=True,
        help_text="Google Analytics 4 측정 ID (예: G-XXXXXXXXXX). "
                  "비워두면 GA 태그 미삽입.",
    )
    ga4_dashboard_url = models.URLField(
        max_length=500, blank=True,
        help_text="GA4 대시보드 URL (통계 페이지 ‘GA 열기’ 버튼에 사용). "
                  "GA4 admin → 속성 → URL 복사.",
    )

    panels = [
        FieldPanel("site_name_override"),
        FieldPanel("tagline_override"),
        FieldPanel("default_og_image"),
        FieldPanel("header_menu"),
        FieldPanel("footer_menu"),
        FieldPanel("footer_extra"),
        FieldPanel("ga4_measurement_id"),
        FieldPanel("ga4_dashboard_url"),
    ]

    class Meta:
        verbose_name = "사이트 네비게이션"
