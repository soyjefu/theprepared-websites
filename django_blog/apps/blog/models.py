from django.db import models
from django.utils import timezone

from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase

from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet
from wagtailseo.models import SeoMixin, SeoType, TwitterCard

from .blocks import ContentStreamBlock, HomeStreamBlock
from .site_settings import NavSettings  # noqa: F401


# ---------------------------------------------------------------- #
# Snippets
# ---------------------------------------------------------------- #
@register_snippet
class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.CharField(max_length=240, blank=True,
                                   help_text="카테고리 페이지 상단의 짧은 부제목")
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        verbose_name="상위 카테고리",
        help_text="없으면 최상위 (그룹). 있으면 그 그룹의 하위 카테고리",
    )
    cover_image = models.ForeignKey(
        "blog_images.CustomImage",
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    intro_body = StreamField(
        HomeStreamBlock(),
        use_json_field=True, blank=True,
        help_text="카테고리 페이지 상단의 자유 편집 블록",
    )
    order = models.IntegerField(default=0, help_text="정렬 순서 (작을수록 먼저)")

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("parent"),
        FieldPanel("description"),
        FieldPanel("order"),
        FieldPanel("cover_image"),
        FieldPanel("intro_body"),
    ]

    class Meta:
        verbose_name = "카테고리"
        verbose_name_plural = "카테고리"
        ordering = ["parent__order", "parent__name", "order", "name"]

    def __str__(self) -> str:
        if self.parent_id:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    def descendant_slugs(self) -> list[str]:
        """자기 자신 + 자식들의 slug. ?cats= 다중 필터에 사용."""
        slugs = [self.slug]
        for c in self.children.all():
            slugs.append(c.slug)
        return slugs


@register_snippet
class Author(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    bio = models.TextField(blank=True)
    avatar = models.ForeignKey(
        "blog_images.CustomImage",
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    website = models.URLField(blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("bio"),
        FieldPanel("avatar"),
        FieldPanel("website"),
    ]

    class Meta:
        verbose_name = "작성자"
        verbose_name_plural = "작성자"

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------- #
# Tag through-model
# ---------------------------------------------------------------- #
class BlogPostTag(TaggedItemBase):
    content_object = ParentalKey(
        "blog.BlogPostPage",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


# ---------------------------------------------------------------- #
# Pages
# ---------------------------------------------------------------- #
class HomePage(Page):
    intro = models.CharField(max_length=240, blank=True,
                             help_text="(선택) 페이지 상단 짧은 소개")
    body = StreamField(
        HomeStreamBlock(),
        use_json_field=True,
        blank=True,
        help_text="홈에 표시할 섹션들을 자유롭게 추가하세요. "
                  "히어로 / 글 리스트(라인) / 글 그리드(영상) / 카테고리 쇼케이스 / 자유 텍스트 / 큰 이미지 / 간격.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    parent_page_types = ["wagtailcore.Page"]
    subpage_types = [
        "blog.BlogIndexPage",
        "blog.ProjectIndexPage",
        "blog.TagIndexPage",
        "blog.SearchIndexPage",
    ]

    class Meta:
        verbose_name = "홈"


class _CategoryGroupIndexMixin:
    """BlogIndexPage / ProjectIndexPage 공통 카테고리 그룹 필터링.

    `category_group` 필드(부모 카테고리)를 가지며,
    그 부모 + 모든 자식 카테고리의 글을 listing.
    """

    def _group_category_ids(self):
        if not getattr(self, "category_group_id", None):
            return None
        ids = list(self.category_group.children.values_list("pk", flat=True))
        ids.append(self.category_group_id)
        return ids

    def _filtered_posts(self):
        qs = BlogPostPage.objects.live().order_by("-first_published_at")
        ids = self._group_category_ids()
        if ids is not None:
            qs = qs.filter(category_id__in=ids)
        return qs


class BlogIndexPage(_CategoryGroupIndexMixin, RoutablePageMixin, Page):
    intro = models.CharField(max_length=240, blank=True)
    intro_body = StreamField(
        HomeStreamBlock(),
        use_json_field=True, blank=True,
        help_text="글 목록 위에 노출할 블록들 (홈과 동일하게 자유 편집)",
    )
    category_group = models.ForeignKey(
        "blog.Category", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="카테고리 그룹 (부모)",
        help_text="이 그룹의 자식 카테고리 글만 표시. 비워두면 모든 글.",
    )
    posts_per_page = models.IntegerField(default=5, help_text="페이지당 글 개수")

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("category_group"),
        FieldPanel("intro_body"),
        FieldPanel("posts_per_page"),
    ]

    parent_page_types = ["blog.HomePage"]
    subpage_types = ["blog.BlogPostPage"]

    class Meta:
        verbose_name = "블로그 목록"

    def _paginate(self, request, qs):
        from django.core.paginator import Paginator, EmptyPage
        page_num = request.GET.get("page", 1)
        paginator = Paginator(qs, self.posts_per_page)
        try:
            return paginator.page(page_num)
        except EmptyPage:
            return paginator.page(paginator.num_pages)

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        posts = self._filtered_posts()  # category_group 자동 한정
        # ?cats= 추가 필터 (그룹 내 특정 카테고리)
        cats_param = (request.GET.get("cats") or "").strip()
        current_categories = []
        if cats_param:
            slugs = [s.strip() for s in cats_param.split(",") if s.strip()]
            input_cats = list(Category.objects.filter(slug__in=slugs))
            expanded_ids = set()
            for c in input_cats:
                expanded_ids.add(c.pk)
                if c.parent_id is None:
                    for child in c.children.all():
                        expanded_ids.add(child.pk)
            if expanded_ids:
                current_categories = input_cats
                posts = posts.filter(category_id__in=expanded_ids)
        # 카테고리 메뉴: 이 그룹의 자식 카테고리만
        if self.category_group_id:
            ctx["all_categories"] = self.category_group.children.all().order_by("order", "name")
        else:
            ctx["all_categories"] = Category.objects.filter(parent__isnull=True).order_by("order", "name")
        ctx["posts"] = self._paginate(request, posts)
        ctx["current_category"] = None
        ctx["current_categories"] = current_categories
        return ctx

    @path("<slug:category_slug>/", name="by_category")
    def by_category(self, request, category_slug):
        cat = Category.objects.filter(slug=category_slug).first()
        if cat is None:
            from django.http import Http404
            raise Http404("카테고리 없음")
        if cat.parent_id is None:
            cat_ids = list(cat.children.values_list("pk", flat=True)) + [cat.pk]
        else:
            cat_ids = [cat.pk]
        posts = (
            BlogPostPage.objects.live()
            .filter(category_id__in=cat_ids)
            .order_by("-first_published_at")
        )
        return self.render(
            request,
            context_overrides={
                "current_category": cat,
                "posts": self._paginate(request, posts),
                "all_categories": Category.objects.filter(parent__isnull=False),
            },
        )

    def route(self, request, path_components):
        """자식 페이지(BlogPostPage)를 카테고리 라우트보다 먼저 매칭."""
        from django.http import Http404
        if path_components:
            try:
                return super(RoutablePageMixin, self).route(request, path_components)
            except Http404:
                pass
        return super().route(request, path_components)


# ---------------------------------------------------------------- #
# 프로젝트 인덱스 페이지 — BlogIndexPage와 같은 listing 패턴,
# 글은 자체적으로 안 갖고 category_group 기반으로 필터링.
# ---------------------------------------------------------------- #
class ProjectIndexPage(_CategoryGroupIndexMixin, RoutablePageMixin, Page):
    intro = models.CharField(max_length=240, blank=True)
    intro_body = StreamField(
        HomeStreamBlock(), use_json_field=True, blank=True,
        help_text="프로젝트 페이지 상단 자유 편집 블록",
    )
    category_group = models.ForeignKey(
        "blog.Category", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
        verbose_name="카테고리 그룹 (부모)",
        help_text="이 그룹의 자식 카테고리 글만 표시 (예: '프로젝트').",
    )
    posts_per_page = models.IntegerField(default=10)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("category_group"),
        FieldPanel("intro_body"),
        FieldPanel("posts_per_page"),
    ]

    parent_page_types = ["blog.HomePage"]
    subpage_types = []

    class Meta:
        verbose_name = "프로젝트 목록"

    def _paginate(self, request, qs):
        from django.core.paginator import Paginator, EmptyPage
        paginator = Paginator(qs, self.posts_per_page)
        try:
            return paginator.page(request.GET.get("page", 1))
        except EmptyPage:
            return paginator.page(paginator.num_pages)

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        posts = self._filtered_posts()
        if self.category_group_id:
            ctx["all_categories"] = self.category_group.children.all().order_by("order", "name")
        else:
            ctx["all_categories"] = []
        ctx["posts"] = self._paginate(request, posts)
        ctx["current_category"] = None
        ctx["current_categories"] = []
        return ctx

    @path("<slug:category_slug>/", name="by_category")
    def by_category(self, request, category_slug):
        cat = Category.objects.filter(slug=category_slug).first()
        if cat is None:
            from django.http import Http404
            raise Http404("카테고리 없음")
        if cat.parent_id is None:
            cat_ids = list(cat.children.values_list("pk", flat=True)) + [cat.pk]
        else:
            cat_ids = [cat.pk]
        posts = (
            BlogPostPage.objects.live()
            .filter(category_id__in=cat_ids)
            .order_by("-first_published_at")
        )
        return self.render(
            request,
            context_overrides={
                "current_category": cat,
                "posts": self._paginate(request, posts),
                "all_categories": (
                    self.category_group.children.all() if self.category_group_id
                    else Category.objects.filter(parent__isnull=False)
                ),
            },
        )


# ---------------------------------------------------------------- #
# 태그 인덱스 페이지
# ---------------------------------------------------------------- #
class TagIndexPage(RoutablePageMixin, Page):
    intro = models.CharField(max_length=240, blank=True)
    intro_body = StreamField(
        HomeStreamBlock(),
        use_json_field=True, blank=True,
        help_text="태그 페이지 상단 안내 블록",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("intro_body"),
    ]

    parent_page_types = ["blog.HomePage"]
    subpage_types = []

    class Meta:
        verbose_name = "태그 페이지"

    def get_context(self, request, *args, **kwargs):
        from taggit.models import Tag
        ctx = super().get_context(request, *args, **kwargs)
        ctx["all_tags"] = Tag.objects.all().order_by("name")
        ctx["current_tag"] = None
        ctx["posts"] = []
        return ctx

    @path("<str:tag_slug>/", name="by_tag")
    def by_tag(self, request, tag_slug):
        from taggit.models import Tag
        tag = Tag.objects.filter(slug=tag_slug).first()
        if tag is None:
            from django.http import Http404
            raise Http404("태그 없음")
        posts = (
            BlogPostPage.objects.live()
            .filter(tags__slug=tag_slug)
            .distinct()
            .order_by("-first_published_at")
        )
        return self.render(
            request,
            context_overrides={
                "current_tag": tag,
                "posts": posts,
                "all_tags": Tag.objects.all().order_by("name"),
            },
        )


# ---------------------------------------------------------------- #
# 검색 페이지
# ---------------------------------------------------------------- #
class SearchIndexPage(Page):
    intro = models.CharField(max_length=240, blank=True)
    intro_body = StreamField(
        HomeStreamBlock(),
        use_json_field=True, blank=True,
        help_text="검색 페이지 상단 안내 블록",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("intro_body"),
    ]

    parent_page_types = ["blog.HomePage"]
    subpage_types = []

    class Meta:
        verbose_name = "검색 페이지"

    def get_context(self, request, *args, **kwargs):
        from django.contrib.postgres.search import TrigramSimilarity
        from django.core.paginator import Paginator, EmptyPage
        from django.db.models import Q
        ctx = super().get_context(request, *args, **kwargs)
        q = (request.GET.get("q") or "").strip()
        results = []
        if q:
            from wagtail.search.backends import get_search_backend
            backend = get_search_backend()
            try:
                results = list(backend.search(q, BlogPostPage.objects.live())[:200])
            except Exception:
                results = []
            if not results:
                results = list(
                    BlogPostPage.objects.live()
                    .annotate(sim=TrigramSimilarity("title", q) + TrigramSimilarity("intro", q))
                    .filter(Q(title__icontains=q) | Q(intro__icontains=q) | Q(sim__gt=0.1))
                    .order_by("-sim", "-first_published_at")[:200]
                )
        paginator = Paginator(results, 5)
        page_num = request.GET.get("page", 1)
        try:
            page_obj = paginator.page(page_num)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages) if paginator.num_pages else None
        ctx["query"] = q
        ctx["results"] = page_obj
        return ctx


class BlogPostPage(SeoMixin, Page):
    intro = models.CharField(max_length=240, blank=True,
                             help_text="목록·SEO description fallback")
    body = StreamField(ContentStreamBlock(), use_json_field=True, blank=True)
    cover_image = models.ForeignKey(
        "blog_images.CustomImage",
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts",
    )
    author = models.ForeignKey(
        Author, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts",
    )
    tags = ClusterTaggableManager(through=BlogPostTag, blank=True)

    # AI 자동 SEO 잠금
    seo_auto_generated_at = models.DateTimeField(null=True, blank=True)
    seo_auto_locked = models.BooleanField(
        default=False,
        help_text="잠그면 Gemini 자동 메타 갱신이 이 페이지를 건너뜁니다.",
    )

    # wagtail-seo 메타 타입 기본값
    seo_content_type = SeoType.ARTICLE
    seo_twitter_card = TwitterCard.LARGE

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("cover_image"),
        FieldPanel("category"),
        FieldPanel("author"),
        FieldPanel("tags"),
        FieldPanel("body"),
    ]

    promote_panels = Page.promote_panels + SeoMixin.seo_panels + [
        MultiFieldPanel(
            [FieldPanel("seo_auto_locked"), FieldPanel("seo_auto_generated_at")],
            heading="AI 자동 SEO",
        ),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
        index.FilterField("category"),
        index.RelatedFields("category", [index.SearchField("name")]),
        index.RelatedFields("tags", [index.SearchField("name")]),
    ]

    parent_page_types = ["blog.BlogIndexPage", "blog.ProjectIndexPage"]
    subpage_types = []

    class Meta:
        verbose_name = "블로그 글"
        ordering = ["-first_published_at"]

    @property
    def likes_count(self) -> int:
        return self.likes.count() if hasattr(self, "likes") else 0

    @property
    def comments_count(self) -> int:
        from apps.comments.models import Comment
        return Comment.objects.filter(page_id=self.pk, status=Comment.STATUS_APPROVED).count()

    @property
    def view_count(self) -> int:
        from apps.comments.models import PageView
        return PageView.objects.filter(page_id=self.pk).count()

    @property
    def auto_description(self) -> str:
        """SEO description 자동 생성: search_description > intro > 본문 첫 paragraph > 첫 image caption."""
        import json as _json
        from bs4 import BeautifulSoup
        if self.search_description:
            return self.search_description
        if self.intro:
            return self.intro
        # body StreamField 안에서 첫 paragraph plain text
        try:
            raw = self.body.raw_data if hasattr(self.body, "raw_data") else _json.loads(str(self.body) or "[]")
        except Exception:
            raw = []
        for item in raw or []:
            t = item.get("type")
            if t == "paragraph":
                txt = BeautifulSoup(item.get("value") or "", "html.parser").get_text(" ", strip=True)
                if txt:
                    return txt[:200]
        # 본문 paragraph 없으면 첫 image caption
        for item in raw or []:
            if item.get("type") == "image":
                cap = (item.get("value") or {}).get("caption") or ""
                if cap:
                    return cap[:200]
        return ""

    def serve(self, request, *args, **kwargs):
        """글 조회 시 PageView 기록 (IP+date UNIQUE — 같은 IP는 1일 1회)."""
        try:
            from apps.comments.models import PageView
            from apps.comments.utils import get_client_ip, ip_hash
            from django.utils import timezone
            PageView.objects.get_or_create(
                page_id=self.pk,
                ip_hash=ip_hash(get_client_ip(request)),
                date=timezone.now().date(),
            )
        except Exception:
            pass
        return super().serve(request, *args, **kwargs)

    def get_related_posts(self, n: int = 4) -> list["BlogPostPage"]:
        """함께 보면 좋은 글 N개. 1순위 같은 태그, 2순위 같은 카테고리, 3순위 최신순."""
        out: list[BlogPostPage] = []
        seen = {self.pk}

        # 1) 같은 태그
        tag_names = list(self.tags.values_list("name", flat=True))
        if tag_names:
            qs = (
                BlogPostPage.objects.live()
                .filter(tags__name__in=tag_names)
                .exclude(pk__in=seen)
                .order_by("-first_published_at")
                .distinct()
            )
            for p in qs:
                if p.pk in seen:
                    continue
                out.append(p); seen.add(p.pk)
                if len(out) >= n:
                    return out

        # 2) 같은 카테고리
        if self.category_id and len(out) < n:
            qs = (
                BlogPostPage.objects.live()
                .filter(category_id=self.category_id)
                .exclude(pk__in=seen)
                .order_by("-first_published_at")
            )
            for p in qs:
                out.append(p); seen.add(p.pk)
                if len(out) >= n:
                    return out

        # 3) 최신 글로 보충
        if len(out) < n:
            qs = (
                BlogPostPage.objects.live()
                .exclude(pk__in=seen)
                .order_by("-first_published_at")
            )
            for p in qs:
                out.append(p); seen.add(p.pk)
                if len(out) >= n:
                    return out
        return out

    def get_context(self, request, *args, **kwargs):
        from apps.comments.models import PostLike
        from apps.comments.utils import get_client_ip, ip_hash
        ctx = super().get_context(request, *args, **kwargs)
        ctx["related_posts"] = self.get_related_posts(4)
        iph = ip_hash(get_client_ip(request))
        ctx["user_has_liked"] = PostLike.objects.filter(page=self, ip_hash=iph).exists()
        return ctx
