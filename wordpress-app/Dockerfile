# PHP-FPM 베이스 이미지 사용
FROM php:8.3-fpm-alpine 

# 필요한 PHP 확장 설치 (WordPress 및 phpMyAdmin 요구사항에 따라 추가)
# 예: mysqli, gd, opcache, pdo_mysql 등
# gd 확장 설치 및 freetype, jpeg, png, webp, zlib, avif 지원 추가
RUN apk add --no-cache \
    mysql-client \
    mariadb-client \
    libjpeg-turbo-dev \
    libpng-dev \
    freetype-dev \
    libwebp-dev \
    zlib-dev \
    exiftool \
    libzip-dev \
    icu-dev \
    imagemagick-dev \
    autoconf \
    libavif-dev \
    gcc \ 
    g++ \
    make \
    pkgconf \
    # 다른 필요한 패키지들 (필요시)
    && docker-php-ext-install pdo_mysql mysqli \
    && docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp --with-avif \
    && docker-php-ext-install gd \
    # 추가할 PHP 확장 모듈 설치
    && docker-php-ext-install exif \
    && docker-php-ext-install zip \
    && docker-php-ext-install intl \
    && pecl install imagick \
    && docker-php-ext-enable imagick \
    # 빌드 도구는 확장이 설치된 후에는 필요 없으므로 제거하여 이미지 크기 최적화 (선택 사항이지만 권장)
    && apk del gcc g++ make pkgconf autoconf \
    && rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

# phpMyAdmin 다운로드 및 설치 (선택 사항: 이미 파일이 있다면 이 부분은 불필요)
COPY --from=phpmyadmin/phpmyadmin:latest /var/www/html/ /var/www/phpmyadmin/
RUN chown -R www-data:www-data /var/www/phpmyadmin

# WordPress 파일들을 위한 디렉토리 생성 및 권한 설정
RUN mkdir -p /var/www/html
RUN chown -R www-data:www-data /var/www/html

# phpMyAdmin 파일들을 위한 디렉토리 생성 및 권한 설정
RUN mkdir -p /var/www/phpmyadmin
RUN chown -R www-data:www-data /var/www/phpmyadmin

# 작업 디렉토리 설정 (WordPress 파일이 위치할 곳)
WORKDIR /var/www/html

# PHP-FPM 설정 복사 (필요시)
# COPY php-fpm.conf /etc/php8/php-fpm.d/www.conf

# 컨테이너 시작 시 PHP-FPM 실행
CMD ["php-fpm"]