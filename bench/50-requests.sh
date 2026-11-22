#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
base_url="${BENCH_BASE_URL:-http://127.0.0.1:3000}"
curl --silent --show-error -o /dev/null -w 'home_ttfb_seconds\t%{time_starttransfer}\n' "$base_url/"
