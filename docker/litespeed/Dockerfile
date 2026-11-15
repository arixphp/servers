FROM litespeedtech/litespeed:6.3.5-lsphp84@sha256:66015f92b7df767e5bd1d1b3383dbeb27229d3bb3d38d6745edb0e71b7bc1707

COPY .work/app/ /var/www/vhosts/localhost/html/
RUN chown -R 1000:1000 /var/www/vhosts/localhost/html/storage
