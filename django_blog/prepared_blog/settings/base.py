"""
공통 settings. dev/prod에서 override 한다.

환경변수는 .env (django-environ) 로 주입한다.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    EMAIL_USE_TLS=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")


# ------------------------------------------------------------------ #
# Core
# ------------------------------------------------------------------ #
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

WSGI_APPLICATION = "prepared_blog.wsgi.application"
ASGI_APPLICATION = "prepared_blog.asgi.application"
ROOT_URLCONF = "prepared_blog.urls"

WAGTAIL_SITE_NAME = env("WAGTAIL_SITE_NAME", default="The Prepared")
WAGTAILADMIN_BASE_URL = env("WAGTAILADMIN_BASE_URL", default="http://localhost:8000")
WAGTAIL_ADMIN_URL_PATH = env("WAGTAIL_ADMIN_URL_PATH", default="cms-admin/")
SITE_TAGLINE = env("SITE_TAGLINE", default="")
INDEXNOW_KEY = env("INDEXNOW_KEY", default="")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------ #
# Applications
# ------------------------------------------------------------------ #
INSTALLED_APPS = [
    # 사용자 앱 (먼저 로드해서 마이그레이션 순서 보장)
    "apps.core",
    "apps.images",
    "apps.blog",
    "apps.seo",
    "apps.comments",
    "apps.search",
    "apps.ai",
    "apps.migration",

    # Wagtail
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.contrib.routable_page",
    "wagtail.contrib.sitemaps",
    "wagtail.contrib.search_promotions",
    "wagtail.contrib.settings",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",

    "modelcluster",
    "taggit",

    # Wagtail SEO
    "wagtailseo",

    # Async
    "django_celery_beat",

    # Security
    "axes",
    "wagtail_2fa",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "django_recaptcha",

    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "axes.middleware.AxesMiddleware",  # 마지막
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
                "apps.core.context_processors.site_meta",
            ],
        },
    },
]

# ------------------------------------------------------------------ #
# Database (PostgreSQL 16 — postgres_db 컨테이너 재사용)
# ------------------------------------------------------------------ #
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("PG_DB", default="prepared_blog"),
        "USER": env("PG_USER", default="theprepared"),
        "PASSWORD": env("PG_PASSWORD"),
        "HOST": env("PG_HOST", default="postgres_db"),
        "PORT": env("PG_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}

# ------------------------------------------------------------------ #
# Cache (Redis DB=2, invest와 분리)
# ------------------------------------------------------------------ #
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL_CACHE", default="redis://redis:6379/2"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": 300,
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# ------------------------------------------------------------------ #
# Celery (broker=3, result=4)
# ------------------------------------------------------------------ #
CELERY_BROKER_URL = env("REDIS_URL_BROKER", default="redis://redis:6379/3")
CELERY_RESULT_BACKEND = env("REDIS_URL_RESULT", default="redis://redis:6379/4")
CELERY_TIMEZONE = "Asia/Seoul"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 5 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 4 * 60
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ------------------------------------------------------------------ #
# Auth / 비밀번호
# ------------------------------------------------------------------ #
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
LOGIN_URL = "wagtailadmin_login"
LOGIN_REDIRECT_URL = "wagtailadmin_home"

# ------------------------------------------------------------------ #
# Wagtail
# ------------------------------------------------------------------ #
WAGTAILIMAGES_IMAGE_MODEL = "blog_images.CustomImage"
WAGTAILIMAGES_FORMAT_CONVERSIONS = {"bmp": "jpeg"}
WAGTAILIMAGES_MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB
WAGTAILDOCS_DOCUMENT_MODEL = "wagtaildocs.Document"
WAGTAILEMBEDS_FINDERS = [
    {"class": "apps.core.embeds.naver.NaverVideoEmbedFinder"},
    {"class": "wagtail.embeds.finders.oembed"},
]
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
        "SEARCH_CONFIG": "simple",
    }
}
TAGGIT_CASE_INSENSITIVE = True

# ------------------------------------------------------------------ #
# i18n / tz
# ------------------------------------------------------------------ #
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------ #
# Static / Media
# ------------------------------------------------------------------ #
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ------------------------------------------------------------------ #
# Security 기본 (prod에서 강화)
# ------------------------------------------------------------------ #
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # 폼 토큰 접근 필요
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "SAMEORIGIN"  # Wagtail admin preview iframe 허용 (외부 임베드는 여전히 차단)
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# django-axes
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5  # hours = 30분
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True

# django-csp
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": [
            "'self'",
            "'unsafe-inline'",  # Wagtail admin 호환
            "https://oapi.map.naver.com",
            "https://www.google.com",
            "https://www.gstatic.com",
            "https://www.googletagmanager.com",  # GA4
        ],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": [
            "'self'", "data:", "blob:",
            "https://*.naver.net", "https://*.pstatic.net",
            "https://maps.googleapis.com", "https://*.gstatic.com",
            "https://www.google-analytics.com",  # GA 픽셀
            "https://www.googletagmanager.com",
        ],
        "font-src": ["'self'", "data:"],
        "frame-src": [
            "'self'",  # Wagtail admin이 같은 도메인 frontend를 preview iframe으로 임베드
            "https://www.youtube.com", "https://www.youtube-nocookie.com",
            "https://player.vimeo.com",
            "https://tv.naver.com",
            "https://www.google.com",
        ],
        "connect-src": [
            "'self'",
            "https://naveropenapi.apigw.ntruss.com",
            "https://maps.googleapis.com",
            "https://www.google-analytics.com",  # GA event 전송
            "https://*.analytics.google.com",
            "https://www.googletagmanager.com",
        ],
        "object-src": ["'none'"],
        # 같은 도메인의 Wagtail admin preview iframe만 허용. 외부 사이트 임베드는 차단.
        "frame-ancestors": ["'self'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    }
}

# reCAPTCHA
RECAPTCHA_PUBLIC_KEY = env("RECAPTCHA_PUBLIC_KEY", default="")
RECAPTCHA_PRIVATE_KEY = env("RECAPTCHA_PRIVATE_KEY", default="")
RECAPTCHA_REQUIRED_SCORE = env.float("RECAPTCHA_REQUIRED_SCORE", default=0.5)
SILENCED_SYSTEM_CHECKS = ["django_recaptcha.recaptcha_test_key_error"]

# ------------------------------------------------------------------ #
# Email
# ------------------------------------------------------------------ #
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@localhost")
ADMIN_EMAIL = env("ADMIN_EMAIL", default="")
ADMINS = [("Admin", ADMIN_EMAIL)] if ADMIN_EMAIL else []
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ------------------------------------------------------------------ #
# External integrations
# ------------------------------------------------------------------ #
DISCORD_WEBHOOK_URL = env("DISCORD_WEBHOOK_URL", default="")

GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-3.1-flash-lite")

NAVER_MAP_NCP_CLIENT_ID = env("NAVER_MAP_NCP_CLIENT_ID", default="")
NAVER_MAP_NCP_CLIENT_SECRET = env("NAVER_MAP_NCP_CLIENT_SECRET", default="")
GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY", default="")

GOOGLE_SITE_VERIFICATION = env("GOOGLE_SITE_VERIFICATION", default="")
NAVER_SITE_VERIFICATION = env("NAVER_SITE_VERIFICATION", default="")

# 보안 secrets
VISITOR_TOKEN_SECRET = env("VISITOR_TOKEN_SECRET")
COMMENT_FORM_TIMETRAP_SECRET = env("COMMENT_FORM_TIMETRAP_SECRET")

# Sentry
SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_ENV = env("SENTRY_ENV", default="dev")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENV,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.05,
        send_default_pii=False,
    )

# ------------------------------------------------------------------ #
# Logging
# ------------------------------------------------------------------ #
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "discord": {
            "level": "ERROR",
            "class": "apps.core.log_handler.DiscordHandler",
            "formatter": "simple",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console", "discord"], "level": "WARNING", "propagate": False},
        "django.request": {"handlers": ["console", "discord"], "level": "ERROR", "propagate": False},
        "axes": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # 5xx / unhandled exception 자동 알림 (django.request 채널이 자동 emit)
    },
}
