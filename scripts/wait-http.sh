#!/usr/bin/env bash
set -euo pipefail
url="${1:?Usage: wait-http.sh URL}"
for ((attempt=0; attempt<30; attempt++)); do
  if curl --silent --output /dev/null --max-time 2 "$url"; then
    exit 0
  fi
  sleep 1
done
echo "Server did not respond: $url" >&2
exit 1
