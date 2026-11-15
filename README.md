# Arix deployment security tests

This independent suite creates an application using the Arix CLI and checks it
over HTTP with its application directory as the document root. It never copies
these tests or server configurations into `arixphp/app`.

## Current state

The Linux matrix contains Apache 2.4, Nginx + PHP-FPM 8.4, OpenLiteSpeed and
LiteSpeed Enterprise with PHP 8.4, and Caddy with FrankenPHP. IIS is not
implemented yet. Enterprise uses the official container's automatically
requested trial license; availability and repeated CI activation are not yet
verified. Neither LiteSpeed configuration reproduces a particular host's setup.

In local HTTP tests with skeleton commit `8c7c9146454f3f8710909b70188459f051b314b5`,
Nginx and FrankenPHP passed the current battery. Apache returned HTTP 500
because its distributed `.htaccess` has a `Header` directive rejected by the
tested Apache version. OpenLiteSpeed intermittently returned HTTP 301 for
`/core` instead of the required 403/404. Both remain failing candidates; the
workflow intentionally reports those failures. These lab results do not
establish compatibility with any particular hosting provider.

## Local use

Install the official Arix CLI (CI pins 0.4.5), Docker, curl, Bash and Python 3.
Run from this directory:

```sh
python3 -m unittest discover -s tests -v
bash scripts/prepare-app.sh
docker build -f docker/frankenphp/Dockerfile -t arix-security:frankenphp .
docker run -d --name arix-test -p 127.0.0.1:8080:80 arix-security:frankenphp
bash scripts/wait-http.sh http://127.0.0.1:8080/
bash scripts/run-security-tests.sh
docker logs arix-test
docker rm -f arix-test
```

Replace `frankenphp` in the build path and image name with `apache`, `nginx`,
`litespeed` or `openlitespeed` to test another server. OpenLiteSpeed listens on container
port 8088, so its port mapping is `127.0.0.1:8080:8088`. Nginx runs PHP-FPM
and Nginx in one test container; FrankenPHP integrates PHP with Caddy. These are
laboratory configurations, not production installation instructions.

Preparation refuses to overwrite `.work/app`; remove or relocate that specific
directory yourself when you want to create another application. To use a
different workspace pass its parent directory as the first argument, but the
Docker build expects `.work/app`. The SHA printed by `arix new` is also stored in
`.work/app-sha.txt`. `ARIX_BIN` selects an installed CLI executable.

The CLI resolves the current `main` of `arixphp/app`; it does not accept a
specific commit. Recording its SHA identifies what was tested, but does not
allow this suite to recreate an arbitrary revision or test a particular app PR.
The CLI version and container base image are pinned; package repositories used
during the image build are not frozen, so the complete build is not bit-for-bit
reproducible.

The HTTP suite checks that representative CSS, JavaScript, image and font assets
return HTTP 200 with their exact contents. It also rejects private responses
other than 403/404, checks for synthetic markers, PHP source and common errors,
and does not follow redirects. It is a
starting point, not a complete security audit. Only the encoded-slash request
`/app%2fconfig/security-probe.txt` also permits HTTP 400, and its body is still
checked for leaks. CI runs on pull requests, pushes,
weekly and manually. A workflow in this repository does not automatically
become a required check on `arixphp/app`.

CI runs public and private checks separately, so a failure in either does not
hide the other. `run-security-tests.sh public` or `private` selects one group;
without arguments it runs both. Public checks report every asset even if another
public request fails. A passing run checks the generated skeleton, not the
historical configuration from a deployed application.
