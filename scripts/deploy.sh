#!/usr/bin/env bash
set -euo pipefail

echo "=== Valtherion Online Deploy Script ==="
echo ""

if [ ! -f "backend/.env" ]; then
    echo "[!] backend/.env not found. Creating from .env.prod template..."
    cp backend/.env.prod backend/.env
    echo "[!] Edit backend/.env with your production values before proceeding."
    echo "[!] Run: openssl rand -hex 32   to generate a SECRET_KEY."
    exit 1
fi

echo "[+] Pulling latest images..."
docker compose pull

echo "[+] Building and starting all services..."
docker compose up -d --build

echo "[+] Waiting for backend to be ready..."
sleep 5
if docker compose ps backend | grep -q "Up"; then
    echo "[+] Backend is running."
else
    echo "[!] Backend may not have started. Check: docker compose logs backend"
fi

echo ""
echo "=== Deployment Complete ==="
echo "HTTPS Proxy:   https://api.valtheriononline.com"
echo ""
echo "Run 'docker compose logs -f' to tail logs."
echo "Run 'docker compose ps' to check service status."
