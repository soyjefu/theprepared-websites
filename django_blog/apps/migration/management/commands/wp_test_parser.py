"""Gutenberg 파서 동작 검증 (mariadb_db에서 글 1건 가져와 변환)."""
from __future__ import annotations

import json

import pymysql
from django.core.management.base import BaseCommand

from apps.migration.gutenberg import to_streamfield


class Command(BaseCommand):
    help = "WP 글 1건을 Gutenberg 파서로 변환해 출력"

    def add_arguments(self, parser):
        parser.add_argument("--post-id", type=int, required=True)

    def handle(self, *args, **options):
        conn = pymysql.connect(
            host="mariadb_db", user="theprepared", password="dnflxksdir1!",
            database="php_db", charset="utf8mb4",
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT post_title, post_name, post_content FROM wp_posts WHERE ID=%s",
                    (options["post_id"],),
                )
                row = cur.fetchone()
                if not row:
                    self.stderr.write(f"post {options['post_id']} not found")
                    return
                title, slug, content = row
        finally:
            conn.close()

        self.stdout.write(f"=== {title} ({slug}) ===")
        items = to_streamfield(content, image_mapper=lambda wp_id: None)
        for i, item in enumerate(items, 1):
            self.stdout.write(f"[{i}] {item['type']}: {json.dumps(item['value'], ensure_ascii=False)[:200]}")
        self.stdout.write(f"--- total {len(items)} blocks ---")
