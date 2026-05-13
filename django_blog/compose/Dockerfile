FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=prepared_blog.settings.prod \
    TZ=Asia/Seoul

WORKDIR /app

# 시스템 패키지: PIL/AVIF/HEIF 인코딩, psycopg3 빌드, locales
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
        libheif-dev \
        libde265-dev \
        libavif-dev \
        libwebp-dev \
        libxml2-dev \
        libxslt1-dev \
        gettext \
        curl \
        ca-certificates \
        tzdata \
    && ln -sf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Python deps (변경 빈도 낮으므로 먼저 캐시)
COPY requirements /tmp/requirements
RUN pip install -r /tmp/requirements/base.txt

# 앱 코드 복사 (compose에서 bind mount 할 때는 무관)
COPY . /app/

# 비루트 유저 (호스트 UID/GID와 매칭)
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} app 2>/dev/null || true \
    && useradd -m -u ${UID} -g ${GID} -s /bin/bash app 2>/dev/null || true \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R ${UID}:${GID} /app

USER app

COPY --chown=${UID}:${GID} compose/entrypoint.sh /usr/local/bin/entrypoint.sh
# entrypoint.sh 는 호스트에서 chmod +x 되어 있어야 함

ENTRYPOINT ["/bin/bash", "/usr/local/bin/entrypoint.sh"]
CMD ["web"]

EXPOSE 8000
