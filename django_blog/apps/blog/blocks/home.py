"""HomePage 전용 섹션 블록 — admin에서 자유롭게 추가·정렬·편집.

워드프레스 홈의 "생각할 거리 / 영상 기록 / 관심 분야" 패턴을 일반화.
"""
from __future__ import annotations

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.snippets.blocks import SnippetChooserBlock


# ---------------------------------------------------------------- #
# 1. HeroBlock — 큰 제목 + 부제 + 옵션 액션
# ---------------------------------------------------------------- #
class HeroBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=120)
    subtitle = blocks.CharBlock(required=False, max_length=240)
    image = ImageChooserBlock(required=False)
    link_label = blocks.CharBlock(required=False, max_length=40)
    link_url = blocks.CharBlock(required=False, max_length=240,
                                help_text="내부 경로 또는 외부 URL")

    class Meta:
        icon = "title"
        template = "blog/blocks/home/hero.html"
        label = "히어로"
        preview_value = {"title": "the prepared:", "subtitle": "지금까지의 경험, 편협한 시각으로 보는 세상"}


# ---------------------------------------------------------------- #
# 2. CategoryFeedBlock — "생각할 거리" 스타일 (제목+날짜 라인)
# ---------------------------------------------------------------- #
def _category_index_base(cat):
    """카테고리가 속한 인덱스 페이지의 URL ('/blog/' 또는 '/project/')."""
    from apps.blog.models import BlogIndexPage, ProjectIndexPage
    if not cat.parent_id:
        return None
    for IndexModel in (BlogIndexPage, ProjectIndexPage):
        ip = IndexModel.objects.filter(
            category_group_id=cat.parent_id
        ).live().first()
        if ip:
            return ip.url  # 끝에 '/' 포함
    return None


def _paged_context(value, parent_context, default_key: str):
    """공통: ?<section_key>=N 으로 페이징한 글 쿼리 + 페이저 메타."""
    from apps.blog.models import BlogPostPage
    request = parent_context.get("request") if parent_context else None
    key = value.get("section_key") or default_key
    try:
        page_num = max(1, int((request.GET.get(key) if request else "1") or 1))
    except (ValueError, TypeError):
        page_num = 1
    cats = value.get("categories") or []
    count = value.get("count", 4)
    qs = BlogPostPage.objects.live().order_by("-first_published_at")
    if cats:
        qs = qs.filter(category__in=cats)
    total = qs.count()
    start = (page_num - 1) * count

    # 더 보기 URL:
    #   · 단일 카테고리 → 그 카테고리 페이지 (/blog/<slug>/ 또는 /project/<slug>/)
    #   · 다중 카테고리 → 첫 카테고리가 속한 인덱스에서 ?cats= 다중 필터
    #   · 없음 → /blog/
    if cats:
        first = cats[0]
        base = _category_index_base(first) or "/blog/"
        if len(cats) == 1:
            more_url = f"{base}{first.slug}/"
        else:
            more_url = f"{base}?cats=" + ",".join(c.slug for c in cats)
    else:
        more_url = "/blog/"

    return {
        "posts": list(qs[start: start + count]),
        "first_cat": cats[0] if cats else None,
        "more_url": more_url,
        "section_key": key,
        "page_num": page_num,
        "has_prev": page_num > 1,
        "has_next": (start + count) < total,
        "max_page": max(1, (total + count - 1) // count),
    }


class CategoryFeedBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=80)
    subtitle = blocks.CharBlock(required=False, max_length=200)
    categories = blocks.ListBlock(
        SnippetChooserBlock("blog.Category"),
        label="포함할 카테고리",
        help_text="비워두면 전체 카테고리",
        default=[],
    )
    count = blocks.IntegerBlock(default=4, min_value=1, max_value=20,
                                help_text="페이지당 글 개수")
    section_key = blocks.CharBlock(
        required=True, max_length=30, default="thoughts",
        help_text="페이지 번호 URL 파라미터 키 (?thoughts=2). 페이지 내 다른 섹션과 겹치지 않게.",
    )
    show_more_link = blocks.BooleanBlock(default=True, required=False,
                                         help_text="첫 카테고리 페이지로 가는 ‘더 보기’ 링크")

    class Meta:
        icon = "list-ul"
        template = "blog/blocks/home/category_feed.html"
        label = "글 리스트 (라인형, 생각할 거리)"
        preview_value = {"title": "생각할 거리", "subtitle": "스쳐간 생각에 대한 기록.", "count": 4, "section_key": "thoughts"}

    def get_context(self, value, parent_context=None):
        ctx = super().get_context(value, parent_context)
        ctx.update(_paged_context(value, parent_context, "thoughts"))
        return ctx


# ---------------------------------------------------------------- #
# 3. CategoryGridBlock — "영상 기록" 스타일 (썸네일+제목 그리드)
# ---------------------------------------------------------------- #
class CategoryGridBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=80)
    subtitle = blocks.CharBlock(required=False, max_length=200)
    categories = blocks.ListBlock(
        SnippetChooserBlock("blog.Category"),
        label="포함할 카테고리",
        default=[],
    )
    count = blocks.IntegerBlock(default=4, min_value=1, max_value=20)
    columns = blocks.ChoiceBlock(
        choices=[("2", "2열"), ("3", "3열")],
        default="2",
    )
    section_key = blocks.CharBlock(
        required=True, max_length=30, default="videos",
        help_text="페이지 번호 URL 파라미터 키",
    )
    show_more_link = blocks.BooleanBlock(default=True, required=False)

    class Meta:
        icon = "image"
        template = "blog/blocks/home/category_grid.html"
        label = "글 카드 그리드 (영상 기록)"
        preview_value = {"title": "영상 기록", "count": 4, "columns": "2", "section_key": "videos"}

    def get_context(self, value, parent_context=None):
        ctx = super().get_context(value, parent_context)
        ctx.update(_paged_context(value, parent_context, "videos"))
        return ctx


# ---------------------------------------------------------------- #
# 4. CategoryShowcaseBlock — "관심 분야" (카테고리 카드 묶음)
# ---------------------------------------------------------------- #
class _ShowcaseItem(blocks.StructBlock):
    category = SnippetChooserBlock("blog.Category", required=True)
    preview_count = blocks.IntegerBlock(default=3, min_value=1, max_value=10,
                                        help_text="카드 안에 미리 보일 글 개수")
    description_override = blocks.CharBlock(required=False, max_length=240,
                                            help_text="비워두면 카테고리 자체 description 사용")


class CategoryShowcaseBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=80, default="관심 분야")
    items = blocks.ListBlock(_ShowcaseItem(), label="카테고리 카드")
    columns = blocks.ChoiceBlock(
        choices=[("2", "2열"), ("3", "3열")],
        default="2",
    )

    class Meta:
        icon = "folder-inverse"
        template = "blog/blocks/home/category_showcase.html"
        label = "카테고리 쇼케이스 (관심 분야)"

    def get_context(self, value, parent_context=None):
        from apps.blog.models import BlogPostPage
        ctx = super().get_context(value, parent_context)
        items = []
        for item in value.get("items") or []:
            cat = item.get("category")
            n = item.get("preview_count", 3)
            posts = []
            if cat:
                posts = list(
                    BlogPostPage.objects.live()
                    .filter(category=cat)
                    .order_by("-first_published_at")[:n]
                )
            items.append({"item": item, "posts": posts})
        ctx["showcase_items"] = items
        return ctx


# ---------------------------------------------------------------- #
# 5. TextBlock (RichText) + 6. SpacerBlock + 7. ImageFullBlock
# ---------------------------------------------------------------- #
class TextBlock(blocks.RichTextBlock):
    class Meta:
        icon = "pilcrow"
        template = "blog/blocks/home/text.html"
        features = ["bold", "italic", "link", "h2", "h3", "ol", "ul", "hr"]
        label = "자유 텍스트"


class SpacerBlock(blocks.StructBlock):
    height = blocks.ChoiceBlock(
        choices=[("20", "Tiny"), ("30", "X-Small"), ("40", "Small"),
                 ("50", "Regular"), ("60", "Large"), ("70", "X-Large")],
        default="50",
    )

    class Meta:
        icon = "horizontalrule"
        template = "blog/blocks/home/spacer.html"
        label = "간격"


class ImageFullBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True)
    caption = blocks.CharBlock(required=False, max_length=200)
    align = blocks.ChoiceBlock(
        choices=[("default", "기본"), ("wide", "넓게"), ("full", "전체 너비")],
        default="default",
    )

    class Meta:
        icon = "image"
        template = "blog/blocks/home/image_full.html"
        label = "큰 이미지"


# ---------------------------------------------------------------- #
# HomePage용 StreamBlock
# ---------------------------------------------------------------- #
class HomeStreamBlock(blocks.StreamBlock):
    hero = HeroBlock()
    category_feed = CategoryFeedBlock()
    category_grid = CategoryGridBlock()
    category_showcase = CategoryShowcaseBlock()
    text = TextBlock()
    image = ImageFullBlock()
    spacer = SpacerBlock()

    class Meta:
        block_counts = {"hero": {"max_num": 2}}
