#!/usr/bin/env bash
set -euo pipefail

label="${1:?usage: bench/run.sh <baseline|optimized>}"
case "$label" in baseline|optimized) ;; *) echo "label must be baseline or optimized" >&2; exit 2;; esac
script_dir="$(cd "$(dirname "$0")" && pwd)"
export BENCH_OUT_DIR="$script_dir/out/$label"
mkdir -p "$BENCH_OUT_DIR"
: > "$BENCH_OUT_DIR/metrics.tsv"
for script in 10-image.sh 30-wire.sh 40-runtime.sh 50-requests.sh; do
  "$script_dir/$script" >> "$BENCH_OUT_DIR/metrics.tsv"
done
if [[ -n "${BENCH_JOB_ID:-}" ]]; then
  "$script_dir/60-job-detail.sh" >> "$BENCH_OUT_DIR/metrics.tsv"
fi
echo "Wrote $BENCH_OUT_DIR/metrics.tsv"
