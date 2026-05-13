from django.conf import settings


def site_meta(request):
    """공통 템플릿 변수: 사이트명, 인증 메타, 외부 키 (공개 안전 키만)."""
    return {
        "SITE_NAME": settings.WAGTAIL_SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "GOOGLE_SITE_VERIFICATION": settings.GOOGLE_SITE_VERIFICATION,
        "NAVER_SITE_VERIFICATION": settings.NAVER_SITE_VERIFICATION,
        "NAVER_MAP_NCP_CLIENT_ID": settings.NAVER_MAP_NCP_CLIENT_ID,
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY,
    }
