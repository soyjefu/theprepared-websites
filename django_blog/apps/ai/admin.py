"""Wagtail admin에 SEO 메타 재생성 액션 등록."""
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from wagtail import hooks


def regenerate_seo_view(request, page_id: int):
    from apps.blog.models import BlogPostPage
    if not request.user.is_staff:
        return HttpResponseRedirect("/")
    page = get_object_or_404(BlogPostPage, pk=page_id)
    from apps.ai.tasks import generate_seo_meta
    generate_seo_meta.delay(page.pk, force=True)
    messages.success(request, f"SEO 메타 재생성 대기열에 등록: {page.title}")
    return HttpResponseRedirect(
        reverse("wagtailadmin_pages:edit", args=[page.pk])
    )


@hooks.register("register_admin_urls")
def register_seo_urls():
    return [
        path("ai/regenerate-seo/<int:page_id>/", regenerate_seo_view, name="ai_regenerate_seo"),
    ]


@hooks.register("register_page_action_menu_item")
def register_seo_button():
    from wagtail.admin.action_menu import ActionMenuItem

    class RegenerateSeoItem(ActionMenuItem):
        label = "AI 메타 재생성"
        name = "regenerate-seo"
        icon_name = "rotate"

        def is_shown(self, context):
            page = context.get("page")
            from apps.blog.models import BlogPostPage
            return isinstance(page, BlogPostPage)

        def get_url(self, context):
            page = context.get("page")
            return reverse("ai_regenerate_seo", args=[page.pk])

    return RegenerateSeoItem(order=900)
