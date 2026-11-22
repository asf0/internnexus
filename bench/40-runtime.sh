#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
frontend_status | tr '=' '\t'
