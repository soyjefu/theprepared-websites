from django.db import models
from wagtail.images.models import AbstractImage, AbstractRendition, Image


class CustomImage(AbstractImage):
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="대체 텍스트. 비워두면 캡션 또는 파일명에서 채워집니다.",
    )
    ai_generated_alt = models.BooleanField(
        default=False,
        help_text="Gemini가 자동 생성한 alt 텍스트인지 표시",
    )
    note = models.TextField(
        blank=True,
        help_text="관리자 메모. 라이브러리에서 검색 가능.",
    )

    admin_form_fields = Image.admin_form_fields + ("alt_text", "note")


class CustomRendition(AbstractRendition):
    image = models.ForeignKey(
        CustomImage,
        on_delete=models.CASCADE,
        related_name="renditions",
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)
