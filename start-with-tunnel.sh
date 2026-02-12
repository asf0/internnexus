#!/bin/bash

# Start script with Cloudflare Tunnel URL Watcher
# Usage: ./start-with-tunnel.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting InternNexus with Cloudflare Tunnel..."
echo ""

# Start all services
echo "📦 Starting Docker services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 5

# Start the URL watcher in background
echo "🔍 Starting tunnel URL watcher..."
"$SCRIPT_DIR/scripts/update-tunnel-url.sh" &
WATCHER_PID=$!

echo ""
echo "✅ All services started!"
echo "📝 The tunnel URL will be displayed automatically once ready"
echo ""
echo "To view logs: docker compose logs -f"
echo "To stop: docker compose down"
echo ""

# Wait for user interrupt
trap 'echo ""; echo "🛑 Stopping URL watcher (containers keep running)..."; kill $WATCHER_PID 2>/dev/null; echo "✅ Containers are still running. Use docker compose down to stop them."; exit 0' INT
wait
