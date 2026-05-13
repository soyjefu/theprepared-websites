"""운영용 settings — Traefik 뒤, HTTPS 강제, HSTS, CSP 강화."""
from .base import *  # noqa: F401,F403

DEBUG = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365 * 2  # 2년
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 운영에서는 unsafe-inline 제거를 위해 nonce 도입을 추후 고려
# (현 단계에서는 Wagtail admin 호환 위해 base 그대로 유지)
