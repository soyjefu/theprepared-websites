"""WP MariaDB 접속 헬퍼 (read-only)."""
from __future__ import annotations

import contextlib

import pymysql

# 환경변수에서 받지 않고 고정 (mariadb_db는 같은 네트워크 내부, 자격증명도 .env로 분리할 수 있으나 PoC)
_DEFAULT_KW = dict(
    host="mariadb_db",
    user="theprepared",
    password="dnflxksdir1!",
    database="php_db",
    charset="utf8mb4",
)


@contextlib.contextmanager
def wp_connection(**overrides):
    kw = {**_DEFAULT_KW, **overrides}
    conn = pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **kw)
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(sql: str, params=()) -> list[dict]:
    with wp_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_one(sql: str, params=()) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None
