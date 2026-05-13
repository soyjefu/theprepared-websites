"""초기 사이트 셋업.

- Wagtail 기본 'Welcome to Wagtail' 페이지를 우리 HomePage로 교체
- BlogIndexPage('blog') 1개 생성
- Site.root_page 를 새 HomePage 로 설정
- 기본 카테고리/작성자 시드 (선택)
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Page, Site


class Command(BaseCommand):
    help = "초기 사이트 트리 셋업"

    def handle(self, *args, **options):
        from apps.blog.models import HomePage, BlogIndexPage, TagIndexPage, SearchIndexPage

        with transaction.atomic():
            root = Page.objects.get(id=1)  # 루트 (사이트 최상위)
            site = Site.objects.filter(is_default_site=True).first()
            if site is None:
                self.stdout.write(self.style.ERROR("기본 사이트가 없습니다."))
                return

            home = HomePage.objects.live().first()
            if home is None:
                # 기본 Welcome 페이지(보통 id=2, slug='home') 제거
                for old in Page.objects.filter(slug="home", depth=2).exclude(content_type__model="homepage"):
                    self.stdout.write(self.style.WARNING(f"기본 Welcome 페이지 제거: id={old.id}"))
                    old.delete()

                # 트리 메타데이터 복구 (삭제로 인한 numchild 불일치)
                Page.fix_tree()
                root = Page.objects.get(id=1)

                home = HomePage(title="The Prepared", slug="home", intro="블로그 홈")
                root.add_child(instance=home)
                home.save_revision().publish()
                self.stdout.write(self.style.SUCCESS(f"HomePage 생성: id={home.id}"))

            site.root_page = home
            site.save()

            blog = BlogIndexPage.objects.live().first()
            if blog is None:
                blog = BlogIndexPage(title="Blog", slug="blog", intro="글 목록")
                home.add_child(instance=blog)
                blog.save_revision().publish()
                self.stdout.write(self.style.SUCCESS(f"BlogIndexPage 생성: id={blog.id}"))

            # 태그 페이지
            tagidx = TagIndexPage.objects.live().first()
            if tagidx is None:
                Page.fix_tree()
                home = HomePage.objects.get(pk=home.pk)
                tagidx = TagIndexPage(title="Tags", slug="tags", intro="태그별 글 모음")
                home.add_child(instance=tagidx)
                tagidx.save_revision().publish()
                self.stdout.write(self.style.SUCCESS(f"TagIndexPage 생성: id={tagidx.id}"))

            # 검색 페이지
            searchidx = SearchIndexPage.objects.live().first()
            if searchidx is None:
                Page.fix_tree()
                home = HomePage.objects.get(pk=home.pk)
                searchidx = SearchIndexPage(title="Search", slug="search", intro="사이트 내 검색")
                home.add_child(instance=searchidx)
                searchidx.save_revision().publish()
                self.stdout.write(self.style.SUCCESS(f"SearchIndexPage 생성: id={searchidx.id}"))

            self.stdout.write(self.style.SUCCESS("초기 셋업 완료."))
