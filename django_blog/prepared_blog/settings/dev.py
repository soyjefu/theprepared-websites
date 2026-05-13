"""개발용 settings — DEBUG ON, 보안 완화."""
from .base import *  # noqa: F401,F403
from .base import CONTENT_SECURITY_POLICY  # noqa: F401

DEBUG = True
ALLOWED_HOSTS = ["*"]

# 개발 환경: HTTPS 미강제
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# 이메일은 콘솔로
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Wagtail draft 미리보기 편의
WAGTAIL_USAGE_COUNT_ENABLED = True
