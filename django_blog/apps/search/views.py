from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.blog.models import BlogPostPage


@require_GET
def search(request):
    q = (request.GET.get("q") or "").strip()
    results = []
    if q:
        # 1) Wagtail search (DB backend)
        from wagtail.search.backends import get_search_backend
        backend = get_search_backend()
        try:
            results = list(backend.search(q, BlogPostPage.objects.live())[:50])
        except Exception:
            results = []

        # 2) trigram fallback (한글 형태소 없을 때 보완)
        if not results:
            results = (
                BlogPostPage.objects.live()
                .annotate(sim=TrigramSimilarity("title", q) + TrigramSimilarity("intro", q))
                .filter(Q(title__icontains=q) | Q(intro__icontains=q) | Q(sim__gt=0.1))
                .order_by("-sim", "-first_published_at")[:50]
            )

    return render(request, "search/search.html", {"query": q, "results": results})
