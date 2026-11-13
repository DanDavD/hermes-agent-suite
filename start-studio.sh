#!/usr/bin/env bash
# ==============================================================================
# Hermes Studio v2 - Unified Full-Stack Launcher (macOS / POSIX)
# Starts:
#   1. FastAPI Backend + SQLite Engine + Workspace Scanner -> http://127.0.0.1:8765
#   2. Next.js 16 Dark IDE Frontend                        -> http://localhost:3000
# ==============================================================================

set -euo pipefail

# Ensure Homebrew binaries (node, npm, python3) are on PATH on Apple Silicon & Intel Macs
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "[SHUTDOWN] Stopping Hermes Studio v2..."
    if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
        echo "   -> Stopping Next.js frontend (PID ${FRONTEND_PID})..."
        kill -TERM "${FRONTEND_PID}" 2>/dev/null || true
    fi
    if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
        echo "   -> Stopping FastAPI backend (PID ${BACKEND_PID})..."
        kill -TERM "${BACKEND_PID}" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "[OK] All Hermes Studio services stopped cleanly."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "=================================================================="
echo "HERMES STUDIO v2 - Autonomous AI Engineering Workbench"
echo "=================================================================="

# 1. Verify .env exists (bootstrap from .env.example if missing)
if [[ ! -f "$ROOT_DIR/.env" ]]; then
    if [[ -f "$ROOT_DIR/.env.example" ]]; then
        cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
        echo "[INFO] Created .env from .env.example."
        echo "[INFO] Tip: Add your OPENROUTER_API_KEY in .env or configure it live in the Studio UI Settings modal."
    else
        touch "$ROOT_DIR/.env"
        echo "OPENROUTER_API_KEY=" > "$ROOT_DIR/.env"
        echo "[INFO] Created empty .env file."
    fi
fi

# 2. Activate Python virtual environment & launch FastAPI Backend
if [[ ! -f "$ROOT_DIR/.venv/bin/activate" ]]; then
    echo "[ERROR] Python virtual environment (.venv) not found at $ROOT_DIR/.venv"
    echo "   Run: python3 -m venv .venv && source .venv/bin/activate && pip install fastapi uvicorn openai pydantic python-dotenv ddgs"
    exit 1
fi

# shellcheck disable=SC1091
source "$ROOT_DIR/.venv/bin/activate"

# Free up any previous Hermes Studio uvicorn instance on port 8765
pkill -f "uvicorn backend.main:app" 2>/dev/null || true
sleep 0.3

echo "[1/2] Starting FastAPI Backend on http://127.0.0.1:8765 ..."
uvicorn backend.main:app --host 127.0.0.1 --port 8765 &
BACKEND_PID=$!

# Wait briefly for FastAPI health check
for _ in {1..15}; do
    if curl -s http://127.0.0.1:8765/api/health >/dev/null 2>&1; then
        echo "[OK] FastAPI Backend online (Swagger Docs: http://127.0.0.1:8765/docs)"
        break
    fi
    sleep 0.4
done

# 3. Launch Next.js Frontend
echo "[2/2] Starting Next.js Frontend on http://localhost:3000 ..."
echo "------------------------------------------------------------------"
echo "Open Hermes Studio in your browser: http://localhost:3000"
echo "Press Ctrl+C at any time to stop both servers."
echo "------------------------------------------------------------------"

cd "$ROOT_DIR/frontend"
npm run dev -- --port 3000 &
FRONTEND_PID=$!

# Keep script alive until either process exits or user hits Ctrl+C
wait "$BACKEND_PID" "$FRONTEND_PID"
