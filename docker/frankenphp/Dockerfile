FROM dunglas/frankenphp:1-php8.4@sha256:08af88488ce218936d530b80f6f55dc2afe4d0d91f13f9e6ae350a9e7752128e

COPY docker/frankenphp/Caddyfile /etc/frankenphp/Caddyfile
COPY .work/app/ /app/
RUN chown -R www-data:www-data /app/storage
