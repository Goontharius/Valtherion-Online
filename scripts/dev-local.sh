#!/usr/bin/env bash
# ============================================================================
# Valtherion Online — LOCAL DEV + LAN TEST harness
# ============================================================================
# Boots the full backend stack (Postgres + Redis + API) in Docker, then starts
# the React Native Metro bundler so a phone on the same Wi-Fi can load the app.
#
#   ./scripts/dev-local.sh            # boot backend + metro
#   ./scripts/dev-local.sh backend     # only the backend stack
#   ./scripts/dev-local.sh stop        # tear it all down
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

action="${1:-all}"

gethostip() {
  # Best-effort LAN IP for the phone-connect hint.
  ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1"
}

backend_up() {
  echo "=== [1/3] Docker engine check ==="
  docker info >/dev/null 2>&1 || { echo "[!] Docker is not running. Start Docker Desktop first."; exit 1; }

  echo "=== [2/3] Building + starting backend stack (Postgres, Redis, API) ==="
  if [ ! -f backend/.env ]; then
    echo "[!] backend/.env missing. Creating from example."
    cp backend/.env.example backend/.env
  fi
  docker compose up -d db redis backend
  echo "[+] Waiting for API ..."
  for i in $(seq 1 30); do
    if curl -fsS http://localhost:8000/ >/dev/null 2>&1; then
      echo "[+] API is live: http://localhost:8000  (docs at /docs)"
      return 0
    fi
    sleep 1
  done
  echo "[!] API did not become ready. Check: docker compose logs backend"
  exit 1
}

metro() {
  echo "=== [3/3] Starting React Native Metro (LAN mode) ==="
  local ip
  ip="$(gethostip)"
  echo ""
  echo "  ┌──────────────────────────────────────────────────────────────┐"
  echo "  │  ON YOUR PHONE (same Wi-Fi as this Mac):                     │"
  echo "  │  1. Open the Expo Go / dev build.                            │"
  echo "  │  2. Connect to:  exp://${ip}:8081                              │"
  echo "  │  3. In api.js, set the base URL to http://${ip}:8000           │"
  echo "  └──────────────────────────────────────────────────────────────┘"
  echo ""
  cd mobile
  npx react-native start
}

stopall() {
  echo "=== Stopping backend stack ==="
  docker compose down
  echo "[+] Done."
}

case "$action" in
  all)     backend_up && metro ;;
  backend) backend_up ;;
  stop)    stopall ;;
  *) echo "Usage: $0 [all|backend|stop]"; exit 1 ;;
esac
