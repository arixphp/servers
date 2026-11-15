#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
parent="${1:-$root/.work}"
repository="${APP_REPOSITORY:-https://github.com/arixphp/app.git}"
ref="${APP_REF:-bugfix/experiment-litespeed-assets}"
mkdir -p "$parent"
parent="$(cd "$parent" && pwd -P)"
if [[ -e "$parent/app" || -L "$parent/app" ]]; then
  echo "Refusing to overwrite $parent/app" >&2
  exit 1
fi

source_dir="$(mktemp -d "${TMPDIR:-/tmp}/arix-source.XXXXXXXX")"
trap 'rm -rf "$source_dir"' EXIT
git clone --quiet --no-checkout --branch "$ref" -- "$repository" "$source_dir/repo"
sha="$(git -C "$source_dir/repo" rev-parse HEAD)"
if [[ ! "$sha" =~ ^[a-f0-9]{40}$ ]]; then
  echo 'Cannot identify skeleton commit' >&2
  exit 1
fi
app="$parent/app"
mkdir "$app"
git -C "$source_dir/repo" archive "$sha" | tar -x -C "$app"
echo "Skeleton $repository ref $ref commit $sha"
for required in index.php .arix.json .htaccess; do
  if [[ ! -f "$app/$required" ]]; then
    echo "Missing required application file: $required" >&2
    exit 1
  fi
done
for dir in app/config core storage media fonts; do
  mkdir -p "$app/$dir"
done
for file in .env .git/config app/config/security-probe.txt core/security-probe.txt storage/security-probe.txt core/security-probe.php security-probe.bak security-probe.old security-probe.php~ security-probe.swp media/security-probe.png fonts/source-sans-3-roman-latin.woff2; do
  if [[ -e "$app/$file" || -L "$app/$file" ]]; then
    echo "Fixture collision: $file" >&2
    exit 1
  fi
done
mkdir -p "$app/.git"
printf '%s\n' 'ARIX_SECURITY_PROBE=ARIX_TEST_PRIVATE_7F3B' > "$app/.env"
for file in .git/config app/config/security-probe.txt core/security-probe.txt storage/security-probe.txt security-probe.bak security-probe.old security-probe.php~ security-probe.swp; do
  printf '%s\n' 'ARIX_TEST_PRIVATE_7F3B' > "$app/$file"
done
printf '%s\n' "<?php echo 'ARIX_TEST_PHP_EXECUTED_7F3B';" > "$app/core/security-probe.php"
printf '%s\n' 'ARIX_TEST_PUBLIC' > "$app/media/security-probe.png"
cp "$root/fixtures/fonts/source-sans-3-roman-latin.woff2" "$app/fonts/source-sans-3-roman-latin.woff2"
printf '%s\n' "$sha" > "$parent/app-sha.txt"
