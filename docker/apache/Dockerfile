FROM php:8.4-apache@sha256:884f64b47174de2c0e813270fe7b24a18605729fcebe201302d98c38805530d0

RUN apt-get update && apt-get install -y --no-install-recommends libonig-dev \
    && docker-php-ext-install mbstring \
    && a2enmod rewrite headers \
    && rm -rf /var/lib/apt/lists/*

COPY docker/apache/site.conf /etc/apache2/sites-available/000-default.conf
COPY .work/app/ /var/www/html/
RUN chown -R www-data:www-data /var/www/html/storage
