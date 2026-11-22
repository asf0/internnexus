#!/usr/bin/env bash
set -euo pipefail

BENCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${BENCH_OUT_DIR:-$BENCH_ROOT/out}"
FRONTEND_CONTAINER="${FRONTEND_CONTAINER:-jobs-frontend}"

mkdir -p "$OUT_DIR"

metric() { printf '%s\t%s\n' "$1" "$2"; }

frontend_status() {
  docker exec "$FRONTEND_CONTAINER" node -e "const fs=require('fs'); const s=fs.readFileSync('/proc/1/status','utf8'); for (const k of ['VmRSS','VmHWM']) { const m=s.match(new RegExp('^'+k+':\\\\s+(\\\\d+)\\\\s+kB','m')); console.log(k+'='+ (m ? m[1] : '')); }"
}
