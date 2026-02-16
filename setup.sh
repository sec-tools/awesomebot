#!/usr/bin/env bash
set -e

# AwesomeBot Setup Script
# Automates the Quick Start: builds containers, pulls the AI model, and verifies everything works.
# Usage: ./setup.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

MODEL="${DEFAULT_MODEL:-qwen2.5:7b}"

echo "=== AwesomeBot Setup ==="
echo ""

# --- Prerequisites check ---

echo "[*] Checking prerequisites..."

if ! command -v docker &>/dev/null; then
    echo "ERROR: docker is not installed."
    echo "       Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &>/dev/null; then
    echo "ERROR: docker compose is not available."
    echo "       Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running. Please start Docker and try again."
    exit 1
fi

echo "    docker:         $(docker --version | head -1)"
echo "    docker compose: $(docker compose version | head -1)"
echo ""

# --- Check if already running ---

RUNNING=$(docker compose ps --format json 2>/dev/null | grep -c '"running"' || true)
if [ "$RUNNING" -ge 3 ]; then
    echo "[*] AwesomeBot containers are already running."
    echo ""
    echo "    To start fresh, run:  ./reset.sh"
    echo "    To just verify:       curl -s http://localhost:8000/health"
    echo ""

    # Still check if model is pulled
    MODEL_PRESENT=$(docker exec awesomebot-ollama ollama list 2>/dev/null | grep -c "$MODEL" || true)
    if [ "$MODEL_PRESENT" -eq 0 ]; then
        echo "[*] Model $MODEL is not yet downloaded. Pulling now..."
        echo "    (this is a one-time download, ~4.7 GB for qwen2.5:7b)"
        echo ""
        docker exec awesomebot-ollama ollama pull "$MODEL"
        echo ""
    fi

    # Run verification
    echo "[*] Verifying..."
    HEALTH=$(curl -sf http://localhost:8000/health 2>/dev/null || echo "FAIL")
    if echo "$HEALTH" | grep -q '"healthy"'; then
        echo ""
        echo "    Health check:  PASSED"
        echo "$HEALTH" | python3 -m json.tool 2>/dev/null | sed 's/^/    /'
    else
        echo ""
        echo "    Health check:  FAILED"
        echo "    Try: docker logs awesomebot-backend"
    fi
    echo ""
    echo "Open http://localhost:3000 in your browser."
    echo "Login: admin / Password1"
    exit 0
fi

# --- Build and start ---

echo "[1/4] Building and starting services..."
echo "       (first build may take a few minutes)"
echo ""
docker compose up -d --build

# --- Wait for healthy ---

echo ""
echo "[2/4] Waiting for services to be healthy..."
echo "       (this may take up to 2 minutes)"

TIMEOUT=180
ELAPSED=0
ALL_HEALTHY=false

while [ $ELAPSED -lt $TIMEOUT ]; do
    HEALTHY=$(docker compose ps --format json 2>/dev/null | grep -c '"healthy"' || true)
    if [ "$HEALTHY" -ge 3 ]; then
        ALL_HEALTHY=true
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))

    # Show which services are healthy so far
    H_OLLAMA="waiting"
    H_BACKEND="waiting"
    H_FRONTEND="waiting"
    docker compose ps --format json 2>/dev/null | grep -q 'ollama.*healthy' && H_OLLAMA="healthy" || true
    docker compose ps --format json 2>/dev/null | grep -q 'backend.*healthy' && H_BACKEND="healthy" || true
    docker compose ps --format json 2>/dev/null | grep -q 'frontend.*healthy' && H_FRONTEND="healthy" || true
    echo "       ${ELAPSED}s -- ollama: $H_OLLAMA | backend: $H_BACKEND | frontend: $H_FRONTEND"
done

if [ "$ALL_HEALTHY" = false ]; then
    echo ""
    echo "WARNING: Not all services are healthy after ${TIMEOUT}s."
    echo ""
    docker compose ps
    echo ""
    echo "Check logs:"
    echo "  docker logs awesomebot-ollama"
    echo "  docker logs awesomebot-backend"
    echo "  docker logs awesomebot-frontend"
    echo ""
    echo "The model pull below may still work if Ollama is running."
fi

# --- Pull model ---

echo ""
echo "[3/4] Pulling AI model ($MODEL)..."
echo "       (one-time download, ~4.7 GB for qwen2.5:7b)"
echo ""
docker exec awesomebot-ollama ollama pull "$MODEL"

# --- Verify ---

echo ""
echo "[4/4] Verifying setup..."
echo ""

# Give the backend a moment to detect the model
sleep 3

HEALTH=$(curl -sf http://localhost:8000/health 2>/dev/null || echo "FAIL")
if echo "$HEALTH" | grep -q '"healthy"'; then
    echo "    Health check:  PASSED"
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null | sed 's/^/    /'
else
    echo "    Health check:  FAILED"
    echo "    Response: $HEALTH"
    echo ""
    echo "    The services may still be starting. Try again in 30 seconds:"
    echo "    curl -s http://localhost:8000/health"
fi

FRONTEND=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null || echo "000")
if [ "$FRONTEND" = "200" ]; then
    echo "    Frontend:      PASSED (http://localhost:3000)"
else
    echo "    Frontend:      FAILED (HTTP $FRONTEND)"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps
echo ""
echo "Open http://localhost:3000 in your browser."
echo "Login: admin / Password1"
echo ""
