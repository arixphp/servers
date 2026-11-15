#!/usr/bin/env bash
set -euo pipefail

base="${BASE_URL:-http://127.0.0.1:8080}"
root="$(cd "$(dirname "$0")/.." && pwd)"
app="${ARIX_APP:-$root/.work/app}"
scope="${1:-all}"
if [[ "$scope" != all && "$scope" != public && "$scope" != private ]] || (( $# > 1 )); then
  echo 'Usage: run-security-tests.sh [all|public|private]' >&2
  exit 2
fi
body="$(mktemp)"
trap 'rm -f "$body"' EXIT

request() {
  local method="$1" path="$2" status
  if ! status="$(curl --path-as-is --silent --show-error --max-time 10 --request "$method" --output "$body" --write-out '%{http_code}' "$base$path")"; then
    echo "FAIL $method $path: connection error" >&2
    return 1
  fi
  printf '%s' "$status"
}

public_asset() {
  local path="$1" status
  status="$(request GET "$path")" || return 1
  if [[ "$status" != 200 ]] || ! cmp -s "$body" "$app$path"; then
    echo "FAIL GET $path: HTTP $status or unexpected content" >&2
    return 1
  fi
  echo "PASS GET $path ($status)"
}

private() {
  local method="$1" path="$2" allow_bad_request="${3:-no}" status
  status="$(request "$method" "$path")" || return 1
  if [[ "$status" != 403 && "$status" != 404 && ! ( "$allow_bad_request" == yes && "$status" == 400 ) ]]; then
    echo "FAIL $method $path: HTTP $status (expected 403/404)" >&2
    return 1
  fi
  if grep -Eiq 'ARIX_TEST_PRIVATE_7F3B|ARIX_TEST_PHP_EXECUTED_7F3B|<\?php|stack trace|fatal error|uncaught exception' "$body"; then
    echo "FAIL $method $path: sensitive content" >&2
    return 1
  fi
  echo "PASS $method $path ($status)"
}

public() {
  local path="$1" expected="$2" status
  status="$(request GET "$path")" || return 1
  if [[ "$status" != 200 ]] || ! grep -Fq "$expected" "$body"; then
    echo "FAIL GET $path: HTTP $status or unexpected content" >&2
    return 1
  fi
  echo "PASS GET $path ($status)"
}

if [[ "$scope" != public ]]; then
for path in '/.env' '/.arix.json' '/.git/config' '/app/config/security-probe.txt' '/core/security-probe.txt' '/core/security-probe.php' '/storage/security-probe.txt' '/app/routes.php' '/core/functions.php' '/security-probe.bak' '/security-probe.old' '/security-probe.php~' '/security-probe.swp' '/app/' '/core' '/storage/' '/%2eenv' '/app//config/security-probe.txt' '/app/./config/security-probe.txt' '/media/../core/security-probe.txt' '/APP/config/security-probe.txt'; do
  private GET "$path"
done
# Some servers reject encoded slashes before routing; a 400 is safe only for
# this specific request and is still inspected for leaked content.
private GET '/app%2fconfig/security-probe.txt' yes
private POST '/core/security-probe.php'
# curl -I handles HEAD without waiting for a body from a compliant server.
status="$(curl --path-as-is --silent --show-error --max-time 10 --head --output /dev/null --write-out '%{http_code}' "$base/.env")"
if [[ "$status" != 403 && "$status" != 404 ]]; then
  echo "FAIL HEAD /.env: HTTP $status" >&2
  exit 1
fi
echo "PASS HEAD /.env ($status)"
fi
if [[ "$scope" != private ]]; then
failed=0
public '/' '<html' || failed=1
public '/about' '<html' || failed=1
for path in '/styles/app.css' '/scripts/app.js' '/media/security-probe.png' '/fonts/source-sans-3-roman-latin.woff2'; do
  public_asset "$path" || failed=1
done
exit "$failed"
fi
