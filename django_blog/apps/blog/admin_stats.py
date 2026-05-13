"""블로그 통계 대시보드 — Wagtail admin '통계' 메뉴."""
from __future__ import annotations

from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone


@staff_member_required
def stats_dashboard(request):
    from apps.blog.models import BlogPostPage, Category
    from apps.comments.models import Comment, PageView, PostLike

    now = timezone.now()
    today = now.date()
    d1_ago = now - timedelta(days=1)
    d7_ago = now - timedelta(days=7)

    # 전체 카운트
    total_posts = BlogPostPage.objects.live().count()
    total_views = PageView.objects.count()
    total_likes = PostLike.objects.count()
    total_comments_all = Comment.objects.count()
    total_comments_approved = Comment.objects.filter(status=Comment.STATUS_APPROVED).count()
    pending_comments = Comment.objects.filter(status=Comment.STATUS_PENDING).count()
    spam_comments = Comment.objects.filter(status=Comment.STATUS_SPAM).count()

    # 최근 24h / 7일
    views_24h = PageView.objects.filter(created_at__gte=d1_ago).count()
    views_7d = PageView.objects.filter(created_at__gte=d7_ago).count()
    likes_24h = PostLike.objects.filter(created_at__gte=d1_ago).count()
    likes_7d = PostLike.objects.filter(created_at__gte=d7_ago).count()
    comments_24h = Comment.objects.filter(created_at__gte=d1_ago,
                                          status=Comment.STATUS_APPROVED).count()
    comments_7d = Comment.objects.filter(created_at__gte=d7_ago,
                                         status=Comment.STATUS_APPROVED).count()

    # 인기 글 (조회수/공감/댓글 top 5)
    top_views = (
        BlogPostPage.objects.live()
        .annotate(n=Count("page_views"))
        .order_by("-n")[:5]
    )
    top_views_data = [{
        "title": p.title, "url": p.url, "count": p.n
    } for p in top_views]

    top_likes = (
        BlogPostPage.objects.live()
        .annotate(n=Count("likes"))
        .filter(n__gt=0)
        .order_by("-n")[:5]
    )
    top_likes_data = [{
        "title": p.title, "url": p.url, "count": p.n
    } for p in top_likes]

    top_comments = (
        BlogPostPage.objects.live()
        .annotate(n=Count("comments", filter=Q(comments__status=Comment.STATUS_APPROVED)))
        .filter(n__gt=0)
        .order_by("-n")[:5]
    )
    top_comments_data = [{
        "title": p.title, "url": p.url, "count": p.n
    } for p in top_comments]

    # 카테고리별 글 수
    categories = (
        Category.objects.filter(parent__isnull=False)
        .annotate(n=Count("posts", filter=Q(posts__live=True)))
        .order_by("parent__order", "parent__name", "order", "name")
    )
    cat_data = [{
        "name": c.name,
        "parent": c.parent.name if c.parent else "",
        "n": c.n,
    } for c in categories]

    # 일별 추세 14일
    daily = []
    max_views = 1
    for i in range(14):
        d = today - timedelta(days=13 - i)
        v = PageView.objects.filter(date=d).count()
        c = Comment.objects.filter(created_at__date=d,
                                   status=Comment.STATUS_APPROVED).count()
        l = PostLike.objects.filter(created_at__date=d).count()
        daily.append({"date": d, "views": v, "comments": c, "likes": l})
        max_views = max(max_views, v)
    # 막대 그래프용 max
    for d in daily:
        d["views_pct"] = int(d["views"] / max_views * 100) if max_views else 0
        d["comments_pct"] = int(d["comments"] / max_views * 100) if max_views else 0
        d["likes_pct"] = int(d["likes"] / max_views * 100) if max_views else 0

    # 최근 댓글 (10건)
    recent_comments = (
        Comment.objects.filter(status=Comment.STATUS_APPROVED)
        .select_related("page", "visitor")
        .order_by("-created_at")[:10]
    )

    # GA4 측정 ID + 대시보드 URL (있으면 상단 카드에 표시)
    try:
        from apps.blog.site_settings import NavSettings
        from wagtail.models import Site
        site = Site.find_for_request(request) or Site.objects.filter(is_default_site=True).first()
        nav = NavSettings.for_site(site) if site else None
    except Exception:
        nav = None

    return render(request, "blog/admin/stats.html", {
        "ga_measurement_id": getattr(nav, "ga4_measurement_id", "") if nav else "",
        "ga_dashboard_url": getattr(nav, "ga4_dashboard_url", "") if nav else "",
        "totals": {
            "posts": total_posts,
            "views": total_views,
            "likes": total_likes,
            "comments": total_comments_approved,
            "comments_all": total_comments_all,
            "pending": pending_comments,
            "spam": spam_comments,
        },
        "recent": {
            "views_24h": views_24h, "views_7d": views_7d,
            "likes_24h": likes_24h, "likes_7d": likes_7d,
            "comments_24h": comments_24h, "comments_7d": comments_7d,
        },
        "top_views": top_views_data,
        "top_likes": top_likes_data,
        "top_comments": top_comments_data,
        "categories": cat_data,
        "daily": daily,
        "max_views": max_views,
        "recent_comments": recent_comments,
    })
