# OpenLiteSpeed test configuration

The image pins OpenLiteSpeed 1.9.4 with LSAPI PHP 8.4. It serves the generated
application at `/usr/local/lsws/Example/html` through the built-in Example
listener on port 8088. The virtual host loads the application's `.htaccess`
and adds explicit private-directory rewrite rules; this is not assumed to be
equivalent to Apache.

Local repeated HTTP tests have shown intermittent 301 responses for `/core`,
so this configuration is not yet considered verified. CI must fail on those
responses rather than following them. Container tests do not certify any
particular hosting provider's OpenLiteSpeed configuration.
