#!/usr/bin/env bash
#
# Run a dependency audit, retrying transient failure of the advisory registry.
#
# The advisory endpoints (npmjs bulk advisories, PyPI/OSV) are slow and
# intermittently unreachable. A registry outage says nothing about the code
# under test, so by default an exhausted retry is reported as a warning rather
# than failing the build. Tunables:
#
#   AUDIT_MAX_ATTEMPTS  attempts before giving up            (default 3)
#   AUDIT_TIMEOUT       seconds allowed per attempt          (default 180)
#   AUDIT_STRICT        1 = an unreachable registry fails the job (default 0)
#
# A non-transient failure (i.e. real advisories) always fails the job.
#
# Usage: audit-with-retry.sh <label> <command> [args...]

set -uo pipefail

label="${1:?usage: audit-with-retry.sh <label> <command> [args...]}"
shift

max_attempts="${AUDIT_MAX_ATTEMPTS:-3}"
attempt_timeout="${AUDIT_TIMEOUT:-180}"
strict="${AUDIT_STRICT:-0}"

# Markers meaning "the registry never answered", not "the lockfile is bad".
# Kept specific so an advisory's package version cannot look like an HTTP status.
transient_re='ERR_PNPM_AUDIT_BAD_RESPONSE|operation timed out|timed out|ETIMEDOUT|ECONNRESET|EAI_AGAIN|ENOTFOUND|ECONNREFUSED|socket hang up|Connection reset|HTTP[ /]1\.[01]?"? 50[234]|HTTP 50[234]'

attempt=1
while :; do
    echo "::group::${label} (attempt ${attempt}/${max_attempts})"
    output="$(timeout -k 10 "${attempt_timeout}" "$@" 2>&1)"
    status=$?
    printf '%s\n' "${output}"
    echo "::endgroup::"

    if [ "${status}" -eq 0 ]; then
        exit 0
    fi

    transient=0
    if [ "${status}" -eq 124 ] || [ "${status}" -eq 137 ]; then
        transient=1
    elif printf '%s\n' "${output}" | grep -qiE "${transient_re}"; then
        transient=1
    fi

    if [ "${transient}" -eq 0 ]; then
        echo "::error::${label} failed with exit ${status} and did not look like a registry outage; treat this as a real finding."
        exit "${status}"
    fi

    if [ "${attempt}" -ge "${max_attempts}" ]; then
        if [ "${strict}" = "1" ]; then
            echo "::error::${label} could not reach the advisory registry after ${max_attempts} attempts (exit ${status})."
            exit "${status}"
        fi
        echo "::warning::${label} skipped: the advisory registry was unreachable after ${max_attempts} attempts (exit ${status}). This is infrastructure, not a finding. Re-run the job to get a real audit, or set AUDIT_STRICT=1 to make this fatal."
        exit 0
    fi

    backoff=$((attempt * 20))
    echo "::warning::${label} could not reach the advisory registry (exit ${status}); retrying in ${backoff}s."
    sleep "${backoff}"
    attempt=$((attempt + 1))
done
