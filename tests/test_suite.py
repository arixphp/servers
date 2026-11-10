import http.server
import os
import pathlib
import subprocess
import tempfile
import threading
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class SecurityHandler(http.server.BaseHTTPRequestHandler):
    mode = 'safe'

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/media/security-probe.png':
            status, body = 200, b'ARIX_TEST_PUBLIC'
        elif self.path in ('/', '/about'):
            status, body = 200, b'<html>OK</html>'
        elif self.mode == 'leak' and self.path == '/.env':
            status, body = 200, b'ARIX_TEST_PRIVATE_7F3B'
        elif self.mode == 'body' and self.path == '/.env':
            status, body = 403, b'ARIX_TEST_PRIVATE_7F3B'
        elif self.mode == 'redirect' and self.path == '/.env':
            status, body = 302, b'Redirect'
        elif self.mode == 'encoded-leak' and self.path == '/app%2fconfig/security-probe.txt':
            status, body = 403, b'ARIX_TEST_PRIVATE_7F3B'
        elif self.mode == 'encoded-bad-request' and self.path == '/app%2fconfig/security-probe.txt':
            status, body = 400, b'Bad request'
        elif self.mode == 'encoded-bad-request-leak' and self.path == '/app%2fconfig/security-probe.txt':
            status, body = 400, b'ARIX_TEST_PRIVATE_7F3B'
        elif self.mode == 'php-execution' and self.path == '/core/security-probe.php':
            status, body = 403, b'ARIX_TEST_PHP_EXECUTED_7F3B'
        else:
            status, body = 403, b'Forbidden'
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body)

    do_POST = do_GET

    def do_HEAD(self):
        self.do_GET()


class SuiteTests(unittest.TestCase):
    def test_prepare_creates_fixtures_and_records_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = pathlib.Path(directory)
            cli = parent / 'arix'
            cli.write_text('''#!/bin/sh
if [ "$1" = "--version" ]; then echo "Arix 0.4.5"; exit; fi
mkdir -p "$3/$2/app/config" "$3/$2/core" "$3/$2/storage" "$3/$2/media"
touch "$3/$2/index.php" "$3/$2/.htaccess"
echo '{"version":"1"}' > "$3/$2/.arix.json"
echo "Skeleton arixphp/app commit 1234567890123456789012345678901234567890."
''')
            cli.chmod(0o755)
            env = dict(os.environ, ARIX_BIN=str(cli))
            result = subprocess.run(
                ['bash', str(ROOT / 'scripts/prepare-app.sh'), str(parent)],
                env=env, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('1234567890123456789012345678901234567890', result.stdout)
            self.assertEqual((parent / 'app/.env').read_text(), 'ARIX_SECURITY_PROBE=ARIX_TEST_PRIVATE_7F3B\n')
            self.assertEqual((parent / 'app/.arix.json').read_text(), '{"version":"1"}\n')

    def test_http_suite_accepts_protected_server_and_rejects_leak(self):
        server = http.server.HTTPServer(('127.0.0.1', 0), SecurityHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        env = dict(os.environ, BASE_URL=f'http://127.0.0.1:{server.server_port}')
        command = ['bash', str(ROOT / 'scripts/run-security-tests.sh')]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.addCleanup(setattr, SecurityHandler, 'mode', 'safe')
        SecurityHandler.mode = 'encoded-bad-request'
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for mode in ('leak', 'body', 'redirect', 'encoded-leak', 'encoded-bad-request-leak', 'php-execution'):
            with self.subTest(mode=mode):
                SecurityHandler.mode = mode
                result = subprocess.run(command, env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('FAIL', result.stdout + result.stderr)

    def test_prepare_rejects_existing_destination_without_deleting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = pathlib.Path(directory)
            (parent / 'app').mkdir()
            marker = parent / 'app' / 'keep'
            marker.write_text('keep')
            result = subprocess.run(
                ['bash', str(ROOT / 'scripts/prepare-app.sh'), str(parent)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
