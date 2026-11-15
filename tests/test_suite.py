import http.server
import os
import pathlib
import subprocess
import tempfile
import threading
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
FONT = 'fonts/source-sans-3-roman-latin.woff2'
ASSETS = {
    '/styles/app.css': b'body { color: black; }\n',
    '/scripts/app.js': b'console.log("hello");\n',
    '/media/security-probe.png': b'ARIX_TEST_PUBLIC\n',
    '/' + FONT: (ROOT / 'fixtures' / FONT).read_bytes(),
}


class SecurityHandler(http.server.BaseHTTPRequestHandler):
    mode = 'safe'

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path in ASSETS:
            if self.mode == 'denied:' + self.path:
                status, body = 403, b'Forbidden'
            elif self.mode == 'wrong:' + self.path:
                status, body = 200, b'<html>Unexpected page</html>'
            else:
                status, body = 200, ASSETS[self.path]
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

    def do_POST(self):
        if self.path not in ASSETS:
            return self.do_GET()
        self.send_response(200 if self.mode == 'post-allowed:' + self.path else 405)
        if self.mode != 'post-no-allow:' + self.path:
            self.send_header('Allow', 'GET, HEAD')
        self.end_headers()

    do_PUT = do_POST
    do_DELETE = do_POST

    def do_HEAD(self):
        if self.mode == 'head-denied:' + self.path:
            self.send_response(403)
            self.end_headers()
            return
        self.do_GET()


class SuiteTests(unittest.TestCase):
    def test_prepare_creates_fixtures_and_records_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = pathlib.Path(directory)
            source = parent / 'source'
            source.mkdir()
            subprocess.run(['git', 'init', '-q', '-b', 'experiment', str(source)], check=True)
            for name in ('index.php', '.htaccess'):
                (source / name).write_text('')
            (source / '.arix.json').write_text('{"version":"1"}\n')
            subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
            sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            env = dict(os.environ, APP_REPOSITORY=str(source), APP_REF='experiment')
            result = subprocess.run(
                ['bash', str(ROOT / 'scripts/prepare-app.sh'), str(parent)],
                env=env, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(sha, result.stdout)
            self.assertEqual((parent / 'app/.env').read_text(), 'ARIX_SECURITY_PROBE=ARIX_TEST_PRIVATE_7F3B\n')
            self.assertEqual((parent / 'app/.arix.json').read_text(), '{"version":"1"}\n')
            self.assertEqual((parent / 'app' / FONT).read_bytes(), (ROOT / 'fixtures' / FONT).read_bytes())

    def test_prepare_uses_requested_git_branch_without_git_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = pathlib.Path(directory)
            source = parent / 'source'
            source.mkdir()
            subprocess.run(['git', 'init', '-q', '-b', 'experiment', str(source)], check=True)
            for name in ('index.php', '.htaccess', '.arix.json'):
                (source / name).write_text(name)
            subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
            sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            result = subprocess.run(['bash', str(ROOT / 'scripts/prepare-app.sh'), str(parent / 'output')], env=dict(os.environ, APP_REPOSITORY=str(source), APP_REF='experiment'), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((parent / 'output/app-sha.txt').read_text().strip(), sha)
            self.assertEqual((parent / 'output/app/.git/config').read_text(), 'ARIX_TEST_PRIVATE_7F3B\n')

    def test_http_suite_accepts_protected_server_and_rejects_leak(self):
        server = http.server.HTTPServer(('127.0.0.1', 0), SecurityHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        app = pathlib.Path(directory.name)
        for path, content in ASSETS.items():
            asset = app / path.lstrip('/')
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.write_bytes(content)
        env = dict(os.environ, BASE_URL=f'http://127.0.0.1:{server.server_port}', ARIX_APP=str(app))
        command = ['bash', str(ROOT / 'scripts/run-security-tests.sh')]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.addCleanup(setattr, SecurityHandler, 'mode', 'safe')
        SecurityHandler.mode = 'encoded-bad-request'
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        SecurityHandler.mode = 'leak'
        result = subprocess.run(command + ['public'], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS GET /styles/app.css', result.stdout)
        result = subprocess.run(command + ['private'], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAIL GET /.env', result.stdout + result.stderr)
        self.assertNotIn('PASS GET /styles/app.css', result.stdout)
        self.assertIn('PASS GET /storage/', result.stdout)
        self.assertIn('PASS POST /core/security-probe.php', result.stdout)
        result = subprocess.run(command + ['invalid'], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        SecurityHandler.mode = 'denied:/styles/app.css'
        result = subprocess.run(command + ['public'], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PASS GET /scripts/app.js', result.stdout)
        self.assertIn('PASS GET /' + FONT, result.stdout)
        for mode in ('leak', 'body', 'redirect', 'encoded-leak', 'encoded-bad-request-leak', 'php-execution'):
            with self.subTest(mode=mode):
                SecurityHandler.mode = mode
                result = subprocess.run(command, env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('FAIL', result.stdout + result.stderr)
        for path in ASSETS:
            SecurityHandler.mode = 'head-denied:' + path
            result = subprocess.run(command + ['public'], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(f'FAIL HEAD {path}', result.stdout + result.stderr)
            for problem in ('post-allowed', 'post-no-allow'):
                with self.subTest(path=path, problem=problem):
                    SecurityHandler.mode = f'{problem}:{path}'
                    result = subprocess.run(command + ['public'], env=env, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(f'FAIL POST {path}', result.stdout + result.stderr)
                    if problem == 'post-no-allow':
                        self.assertIn('HTTP 405 with missing or invalid Allow header', result.stderr)
                    else:
                        self.assertIn('HTTP 200 (expected 405)', result.stderr)
            for problem in ('denied', 'wrong'):
                with self.subTest(path=path, problem=problem):
                    SecurityHandler.mode = f'{problem}:{path}'
                    result = subprocess.run(command, env=env, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(f'FAIL GET {path}', result.stdout + result.stderr)

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
