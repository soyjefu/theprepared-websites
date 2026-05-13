"""Wagtail admin 사이드바: 글 listing + 통계 메뉴 + Pages explorer 글 숨김."""
from __future__ import annotations

import django_filters
from django.contrib.contenttypes.models import ContentType
from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.menu import MenuItem
from wagtail.admin.site_summary import SummaryItem
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.viewsets.pages import PageListingViewSet

from .admin_stats import stats_dashboard
from .models import BlogPostPage, Author, Category


class BlogPostFilterSet(WagtailFilterSet):
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(), label="카테고리",
    )
    author = django_filters.ModelChoiceFilter(
        queryset=Author.objects.all(), label="작성자",
    )
    first_published_year = django_filters.NumberFilter(
        field_name="first_published_at", lookup_expr="year", label="발행연도",
    )

    class Meta:
        model = BlogPostPage
        fields = ["category", "author", "first_published_year"]


class CountColumn(Column):
    def get_value(self, instance):
        target = instance.specific if hasattr(instance, "specific") else instance
        return getattr(target, self.accessor, 0)


class BlogPostListingViewSet(PageListingViewSet):
    model = BlogPostPage
    icon = "doc-full"
    menu_label = "글"
    menu_name = "blog_posts"
    menu_order = 110
    add_to_admin_menu = True
    name = "blog_posts"
    filterset_class = BlogPostFilterSet

    columns = PageListingViewSet.columns + [
        Column("category", label="카테고리"),
        DateColumn("first_published_at", label="발행일", sort_key="first_published_at"),
        CountColumn("view_count", label="조회"),
        CountColumn("likes_count", label="공감"),
        CountColumn("comments_count", label="댓글"),
    ]


blogpost_listing_viewset = BlogPostListingViewSet("blog_posts")


@hooks.register("register_admin_viewset")
def register_blogpost_listing():
    return blogpost_listing_viewset


@hooks.register("register_admin_urls")
def register_stats_url():
    return [path("blog-stats/", stats_dashboard, name="blog_stats")]


@hooks.register("register_admin_menu_item")
def register_stats_menu():
    return MenuItem(
        "통계",
        reverse("blog_stats"),
        icon_name="time",
        order=200,
    )


@hooks.register("construct_explorer_page_queryset")
def hide_blogposts_from_explorer(parent_page, pages, request):
    try:
        ct = ContentType.objects.get_for_model(BlogPostPage)
    except ContentType.DoesNotExist:
        return pages
    return pages.exclude(content_type=ct)


class CommentsSummaryItem(SummaryItem):
    """Admin 홈에 댓글 요약 카드 — 승인됨/검토 대기."""
    order = 300
    template_name = "wagtailadmin/home/site_summary_comments.html"

    def get_context_data(self, parent_context):
        from apps.comments.models import Comment
        return {
            "approved": Comment.objects.filter(status=Comment.STATUS_APPROVED).count(),
            "pending": Comment.objects.filter(status=Comment.STATUS_PENDING).count(),
            "url": reverse("blog_stats"),
        }

    def is_shown(self):
        return self.request.user.is_staff


@hooks.register("construct_homepage_summary_items")
def add_comments_summary(request, items):
    items.append(CommentsSummaryItem(request))


@hooks.register("construct_main_menu")
def add_pending_badge_to_stats(request, menu_items):
    """'통계' 메뉴 항목에 검토 대기 카운트 뱃지."""
    from apps.comments.models import Comment
    pending = Comment.objects.filter(status=Comment.STATUS_PENDING).count()
    if not pending:
        return
    for item in menu_items:
        if getattr(item, "name", None) == "통계" or item.label == "통계":
            item.label = f"통계 ({pending})"
            item.classname = (getattr(item, "classname", "") + " w-text-warning-100").strip()
            break
