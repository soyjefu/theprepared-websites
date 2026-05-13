"""카테고리 계층 구조 시드.

부모 2개 (블로그, 프로젝트) 생성 + 기존 7개 카테고리에 parent 지정.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

PARENTS = [
    {"name": "블로그", "slug": "blog-cat", "description": "에세이 · 사회 · 문화 · 영상 기록 · 초안", "order": 1},
    {"name": "프로젝트", "slug": "project-cat", "description": "코드 스케치 · 예담 · 고지도 벡터화", "order": 2},
]

CHILDREN = {
    "blog-cat": ["society", "culture", "drafts", "image-records"],
    "project-cat": ["code_sketch", "artistic-stories", "old-map-vectorization"],
}


class Command(BaseCommand):
    help = "카테고리 계층 시드: 블로그/프로젝트 부모 + 7개 자식 연결"

    def handle(self, *args, **options):
        from apps.blog.models import Category
        # 1) 부모 생성/업데이트
        parents = {}
        for spec in PARENTS:
            cat, created = Category.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "name": spec["name"],
                    "description": spec["description"],
                    "order": spec["order"],
                    "parent": None,
                },
            )
            parents[spec["slug"]] = cat
            self.stdout.write(self.style.SUCCESS(
                f"{'생성' if created else '갱신'} 부모: {cat.name} ({cat.slug})"
            ))

        # 2) 자식 parent 지정
        for parent_slug, child_slugs in CHILDREN.items():
            parent = parents[parent_slug]
            for i, cslug in enumerate(child_slugs):
                child = Category.objects.filter(slug=cslug).first()
                if child is None:
                    self.stderr.write(self.style.WARNING(f"  자식 미발견: {cslug}"))
                    continue
                child.parent = parent
                child.order = i
                child.save(update_fields=["parent", "order"])
                self.stdout.write(f"  → {child.name} → {parent.name}")
