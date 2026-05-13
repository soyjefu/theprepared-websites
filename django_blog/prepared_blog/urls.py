from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import include, path, re_path
from django.views.decorators.cache import never_cache
from django.views.generic.base import RedirectView, TemplateView

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls

from apps.blog.feeds import LatestPostsAtomFeed, LatestPostsFeed


def indexnow_key_file(request, key):
    """IndexNow 검증용 키 파일 — `/<key>.txt` 에서 키 평문 반환."""
    if not settings.INDEXNOW_KEY or key != settings.INDEXNOW_KEY:
        raise Http404
    return HttpResponse(settings.INDEXNOW_KEY, content_type="text/plain")


@never_cache
def healthz(request):
    """외부 uptime 모니터링용 헬스체크. DB ping 포함."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return JsonResponse({"ok": True, "db": "ok"})
    except Exception as e:
        return JsonResponse({"ok": False, "db": str(e)[:200]}, status=503)


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path(settings.WAGTAIL_ADMIN_URL_PATH, include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),

    # SEO
    path("sitemap.xml", sitemap),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="seo/robots.txt", content_type="text/plain"),
        name="robots",
    ),
    # IndexNow 키 검증 (사이트 루트에 `<key>.txt` 호스팅)
    re_path(r"^(?P<key>[0-9a-fA-F]{8,128})\.txt$", indexnow_key_file, name="indexnow_key"),

    # Health check (외부 uptime 모니터 + 로드밸런서용) — slash 양쪽 다 받음
    path("healthz", healthz, name="healthz"),
    path("healthz/", healthz),

    # RSS / Atom
    path("feed/", LatestPostsFeed(), name="rss"),
    path("feed/atom/", LatestPostsAtomFeed(), name="atom"),

    # 댓글 (apps.comments에서 마운트)
    path("c/", include(("apps.comments.urls", "comments"), namespace="comments")),

    # /search/ 는 Wagtail SearchIndexPage(slug='search')가 처리

    # Wagtail 페이지 라우팅 (마지막)
    path("", include(wagtail_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
