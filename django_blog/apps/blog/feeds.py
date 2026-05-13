"""RSS / Atom 피드 — Django syndication framework."""
from __future__ import annotations

from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.urls import reverse_lazy

from .models import BlogIndexPage, BlogPostPage


class LatestPostsFeed(Feed):
    title = "The Prepared"
    link = "/blog/"
    description = "최신 글 RSS"
    feed_size = 30

    def items(self):
        return BlogPostPage.objects.live().order_by("-first_published_at")[: self.feed_size]

    def item_title(self, item: BlogPostPage):
        return item.title

    def item_description(self, item: BlogPostPage):
        return item.intro or item.search_description or ""

    def item_link(self, item: BlogPostPage):
        return item.url or "/"

    def item_pubdate(self, item: BlogPostPage):
        return item.first_published_at

    def item_updateddate(self, item: BlogPostPage):
        return item.last_published_at

    def item_categories(self, item: BlogPostPage):
        cats = []
        if item.category:
            cats.append(item.category.name)
        cats.extend(t.name for t in item.tags.all())
        return cats


class LatestPostsAtomFeed(LatestPostsFeed):
    feed_type = Atom1Feed
    subtitle = LatestPostsFeed.description
