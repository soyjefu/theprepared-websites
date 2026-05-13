"""기본 Wagtail Collection 시드. admin에서 추가/리네임/자식 폴더 가능."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from wagtail.models import Collection


DEFAULT_COLLECTIONS = ["사진", "스크린샷", "일러스트", "인포그래픽", "썸네일"]


class Command(BaseCommand):
    help = "기본 Collection 시드"

    def handle(self, *args, **options):
        root = Collection.get_first_root_node()
        created, skipped = [], []
        for name in DEFAULT_COLLECTIONS:
            if Collection.objects.filter(name=name).exists():
                skipped.append(name); continue
            root.add_child(name=name)
            created.append(name)
        self.stdout.write(self.style.SUCCESS(f"생성: {created}, 스킵: {skipped}"))
