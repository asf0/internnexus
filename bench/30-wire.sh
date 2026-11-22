#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
base_url="${BENCH_BASE_URL:-http://127.0.0.1:3000}"
bytes="$(curl --silent --show-error --compressed -H 'Accept-Encoding: gzip' -o /dev/null -w '%{size_download}' "$base_url/")"
metric home_gzip_bytes "$bytes"
