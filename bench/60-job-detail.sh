#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"

: "${BENCH_JOB_ID:?BENCH_JOB_ID must be set to a public job UUID}"
base_url="${BENCH_BASE_URL:-http://127.0.0.1:3000}"
url="$base_url/jobs/$BENCH_JOB_ID"
warm_requests="${BENCH_WARM_REQUESTS:-10}"
response_file="$(mktemp)"
trap 'rm -f "$response_file"' EXIT

pg_stat_snapshot() {
  docker exec "${BENCH_DB_CONTAINER:-jobs-db}" sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F "\t" -c "SELECT coalesce(sum(calls), 0), coalesce(sum(total_exec_time), 0) FROM pg_stat_statements;"' \
    2>/dev/null || true
}

pg_before="$(pg_stat_snapshot)"

request_metric() {
  local phase="$1"
  local result
  result="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}\t%{size_download}\t%{time_total}' "$url")"
  IFS=$'\t' read -r status bytes elapsed <<< "$result"
  metric "job_detail_${phase}_status" "$status"
  metric "job_detail_${phase}_html_bytes" "$bytes"
  metric "job_detail_${phase}_seconds" "$elapsed"
}

# The first request is the workload's cold request. Restart the frontend before
# a run when a truly empty persistent Data Cache is required.
request_metric cold
for ((i = 1; i <= warm_requests; i++)); do
  request_metric "warm_${i}"
done
frontend_status | awk -F= '$1 == "VmHWM" { print "frontend_VmHWM_kB\t" $2 }'
pg_after="$(pg_stat_snapshot)"
if [[ -n "$pg_before" && -n "$pg_after" ]]; then
  IFS=$'\t' read -r pg_before_calls pg_before_time <<< "$pg_before"
  IFS=$'\t' read -r pg_after_calls pg_after_time <<< "$pg_after"
  metric pg_stat_statements_calls_before "$pg_before_calls"
  metric pg_stat_statements_calls_after "$pg_after_calls"
  metric pg_stat_statements_calls_delta "$(awk -v before="$pg_before_calls" -v after="$pg_after_calls" 'BEGIN { print after - before }')"
  metric pg_stat_statements_total_exec_ms_before "$pg_before_time"
  metric pg_stat_statements_total_exec_ms_after "$pg_after_time"
  metric pg_stat_statements_total_exec_ms_delta "$(awk -v before="$pg_before_time" -v after="$pg_after_time" 'BEGIN { print after - before }')"
fi

if docker exec "$FRONTEND_CONTAINER" true >/dev/null 2>&1; then
  metric job_detail_workload_warm_requests "$warm_requests"
fi
