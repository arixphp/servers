FROM php:8.4-fpm@sha256:212c3c9fc09d58f6b1a12b0b4a6a90fd44a209299a67633c2bccbc1dd53c55e0

RUN apt-get update && apt-get install -y --no-install-recommends nginx libonig-dev \
    && docker-php-ext-install mbstring \
    && rm -rf /var/lib/apt/lists/*
COPY docker/nginx/default.conf /etc/nginx/sites-available/default
COPY docker/nginx/start.sh /usr/local/bin/arix-start
COPY .work/app/ /var/www/html/
RUN chown -R www-data:www-data /var/www/html/storage && chmod +x /usr/local/bin/arix-start
CMD ["/usr/local/bin/arix-start"]
