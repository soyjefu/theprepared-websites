"""Django logging → Discord webhook handler.

Django의 'django.request' 같은 채널에서 ERROR/CRITICAL 발생 시 Discord로 전달.
스레드 격리 + 60초 동일 메시지 throttle (notify.send_discord가 처리).
"""
from __future__ import annotations

import logging
import threading

log = logging.getLogger(__name__)


class DiscordHandler(logging.Handler):
    """logging.Handler → Discord webhook. 동기 발송이지만 짧음 (5s timeout)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # 자신의 로그를 다시 보내지 않음 (재귀 방지)
            if record.name.startswith("apps.core.notify") or record.name.startswith("urllib3"):
                return

            # 컨텍스트 추출
            path = getattr(record, "request", None)
            url = path.path if path is not None and hasattr(path, "path") else ""
            status = getattr(record, "status_code", "")

            title = f"🚨 {record.levelname} · {record.name}"
            if status:
                title = f"🚨 HTTP {status} · {record.name}"

            body_lines = []
            if url:
                body_lines.append(f"**URL**: `{url}`")
            body_lines.append(f"```\n{self.format(record)[:1500]}\n```")

            # 같은 path+exception 60초 내 중복 차단
            fp = f"{record.name}:{record.levelno}:{url}:{getattr(record, 'exc_text', '') or record.getMessage()[:80]}"

            # 동기 발송 (request 컨텍스트 보존)
            threading.Thread(
                target=self._send_safe,
                args=(title, "\n".join(body_lines), fp),
                daemon=True,
            ).start()
        except Exception:
            # logging handler는 절대 raise하면 안 됨
            self.handleError(record)

    @staticmethod
    def _send_safe(title: str, body: str, fingerprint: str) -> None:
        try:
            from .notify import send_discord
            send_discord(body, title=title, fingerprint=fingerprint)
        except Exception as e:
            log.warning("DiscordHandler send 실패: %s", e)
