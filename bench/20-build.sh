#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"

docker compose build frontend
docker image inspect "${FRONTEND_IMAGE:-jobs-frontend:latest}" --format '{{.Size}}' | awk '{print "frontend_build_image_bytes\t" $1}'
