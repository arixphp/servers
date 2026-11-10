FROM litespeedtech/openlitespeed:1.9.4-lsphp84@sha256:84b5a648789f0c4ba1da9ffe3cb3ba79ae30a9c5c95f1e6a7f9302f8b273f2f8

COPY docker/openlitespeed/vhconf.conf /usr/local/lsws/conf/vhosts/Example/vhconf.conf
COPY .work/app/ /usr/local/lsws/Example/html/
RUN chown -R nobody:nogroup /usr/local/lsws/Example/html/storage
