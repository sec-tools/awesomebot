#!/usr/bin/env bash
set -e

# AwesomeBot Full Reset Script
# Tears down everything and rebuilds from scratch, as if freshly cloned.
# Usage: ./reset.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

MODEL="${DEFAULT_MODEL:-qwen2.5:7b}"

echo "=== AwesomeBot Full Reset ==="
echo ""
echo "This will destroy ALL data (database, uploaded files, downloaded models)"
echo "and rebuild everything from scratch."
echo ""
read -r -p "Are you sure? (y/N) " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "[1/5] Stopping containers and removing volumes..."
docker compose down --volumes --remove-orphans 2>/dev/null || true

echo ""
echo "[2/5] Removing built images..."
docker compose down --rmi all 2>/dev/null || true

echo ""
echo "[3/5] Rebuilding and starting services..."
docker compose up -d --build

echo ""
echo "[4/5] Waiting for services to be healthy..."
echo "       (this may take up to 2 minutes on first build)"
TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    HEALTHY=$(docker compose ps --format json 2>/dev/null | grep -c '"healthy"' || true)
    if [ "$HEALTHY" -ge 3 ]; then
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo "       ...waiting ($ELAPSED seconds)"
done

if [ "$HEALTHY" -lt 3 ]; then
    echo ""
    echo "WARNING: Not all services are healthy after ${TIMEOUT}s."
    echo "         Check status with: docker compose ps"
    echo "         Check logs with:   docker logs awesomebot-backend"
    echo ""
    echo "         The model pull below may still work -- Ollama just needs to be running."
fi

echo ""
echo "[5/5] Pulling AI model ($MODEL)..."
echo "       (this is a one-time download, ~4.7 GB for qwen2.5:7b)"
docker exec awesomebot-ollama ollama pull "$MODEL"

echo ""
echo "=== Reset Complete ==="
echo ""
echo "Services:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps
echo ""
echo "Open http://localhost:3000 in your browser."
echo "Login: admin / Password1"
echo ""
