# Dockerfile for websites-wordpress_app

# 1. 베이스 이미지 설정 (PHP 8.3 FPM Alpine 버전)
# 히스토리의 PHP_VERSION=8.3.25와 CMD ["php-fpm"]을 기반으로 유추
FROM php:8.3-fpm-alpine

# 2. 시스템 의존성 패키지 설치 (mysql 클라이언트 등)
# 히스토리의 apk add --no-cache mysql-client ...를 기반으로 작성
RUN apk add --no-cache mysql-client

# 3. phpMyAdmin 및 WordPress 디렉토리 생성 및 권한 설정
# 히스토리의 mkdir, chown 명령어들을 논리적으로 재구성
RUN mkdir -p /var/www/html /var/www/phpmyadmin && \
    chown -R www-data:www-data /var/www/html /var/www/phpmyadmin

# 4. 애플리케이션 파일 복사
# 이 부분은 추측입니다. 로컬의 wordpress/와 phpmyadmin/ 폴더를 복사하는 것으로 가정
# COPY ./wordpress/ /var/www/html/
# COPY ./phpmyadmin/ /var/www/phpmyadmin/

# 5. 작업 디렉토리 설정
WORKDIR /var/www/html

# 6. 컨테이너 실행 명령어 (베이스 이미지에 이미 포함되어 있지만 명시)
CMD ["php-fpm"]