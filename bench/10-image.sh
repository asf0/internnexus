#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
docker image inspect "${FRONTEND_IMAGE:-jobs-frontend:latest}" --format '{{.Size}}' | awk '{print "image_bytes\t" $1}'
/