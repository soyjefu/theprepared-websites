from django.db import models


class GeocodeCache(models.Model):
    """주소 → 좌표 영속 캐시. 페이지 로드 시 외부 API 재호출 방지."""

    address_norm = models.CharField(max_length=240, unique=True)
    lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    provider = models.CharField(max_length=10, default="naver")  # naver/google
    failed = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["updated_at"])]

    def __str__(self) -> str:
        return f"{self.address_norm} → {self.lat},{self.lng} ({self.provider})"
