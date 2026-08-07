# Valtherion Online — Deployment Guide

## Architecture

```
                     ┌──────────────────────────────────┐
  Users <-> HTTPS ──►│  Caddy (ports 80/443)            │
                     │  Auto-SSL via Let's Encrypt       │
                     │  Reverse proxies to backend:8000  │
                     └──────────┬───────────────────────┘
                                │
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                    ▼
    ┌─────────────┐   ┌──────────────┐    ┌────────────────┐
    │ backend:8000│   │ postgres:5432│    │  redis:6379    │
    │ FastAPI      │   │ PG 15-alpine │    │  Redis 7-alpine│
    └─────────────┘   └──────────────┘    └────────────────┘
                             │
                    ┌────────┴────────┐
                    │ valtherion_db_   │
                    │ data (volume)    │
                    └─────────────────┘

  Watchtower: Auto-restarts containers when new images are pushed
```

## Prerequisites

- Domain name pointed to server IP (A record: `api.valtheriononline.com` → server IP)
- Firewall open on ports 22, 80, 443

## Server Setup (Ubuntu 22.04/24.04)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose-v2 -y
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

## One-Time Configuration

```bash
git clone https://github.com/your-org/valtherion_online.git
cd valtherion_online

cp backend/.env.prod backend/.env
# Edit backend/.env and set:
#   SECRET_KEY=$(openssl rand -hex 32)
#   POSTGRES_PASSWORD=<strong-password>

# Replace "api.valtheriononline.com" in Caddyfile with your domain
# Replace the domain in mobile/src/services/api.js and mobile/src/services/websocket.js
```

## Deploy / Redeploy

```bash
cd valtherion_online
git pull
bash scripts/deploy.sh
```

Or manually:

```bash
docker compose up -d --build
docker compose logs -f  # tail logs
docker compose ps       # check status
```

## Verifying the Deploy

```bash
# Check backend health
curl -s https://api.valtheriononline.com/docs

# Check container status
docker compose ps

# Tail all logs
docker compose logs -f
```

## Mobile App URLs

The mobile app selects URLs based on `__DEV__` (automatic in React Native):

| Environment | API Base | WebSocket |
|---|---|---|
| Dev (debug build) | `http://localhost:8000` | `ws://localhost:8000` |
| Prod (release build) | `https://api.valtheriononline.com` | `wss://api.valtheriononline.com` |

To change the production domain, edit:
- `mobile/src/services/api.js:6`
- `mobile/src/services/websocket.js:18`
- `Caddyfile`

## Production .env Reference

File: `backend/.env`

| Key | Description | Example |
|---|---|---|
| `DATABASE_URL` | Async PostgreSQL connection | `postgresql+asyncpg://postgres:password@db:5432/valtherion` |
| `REDIS_URL` | Redis connection | `redis://redis:6379` |
| `SECRET_KEY` | JWT signing key | `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token TTL | `30` |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | JWT refresh token TTL | `10080` (7 days) |

## Android Release Build

```bash
cd mobile

# Generate upload keystore (one-time)
keytool -genkey -v -keystore valtherion.keystore -alias valtherion \\
  -keyalg RSA -keysize 2048 -validity 10000

# Create android/gradle.properties (one-time)
# Add:
#   MYAPP_UPLOAD_STORE_FILE=valtherion.keystore
#   MYAPP_UPLOAD_KEY_ALIAS=valtherion
#   MYAPP_UPLOAD_STORE_PASSWORD=<password>
#   MYAPP_UPLOAD_KEY_PASSWORD=<password>

# Build release APK
cd android && ./gradlew assembleRelease
# APK at: android/app/build/outputs/apk/release/app-release.apk
```

## Useful Commands

```bash
docker compose logs -f backend          # Tail backend logs
docker compose down                     # Stop all services
docker compose up -d backend            # Restart just backend
docker volume ls                        # List volumes (DB data lives here)
docker exec -it valtherion_db psql -U postgres -d valtherion  # DB shell
docker exec -it valtherion_redis redis-cli                      # Redis shell
```

## Monitoring

- **Watchtower**: Auto-updates containers. Included in docker-compose.
- **UptimeRobot** (free): Add `https://api.valtheriononline.com/docs` as a monitor. Alerts on downtime.

## Security Notes

- Ports 5432 and 6379 are NOT exposed to the host in the production docker-compose.yml — they're only accessible within the Docker network.
- Only ports 80 and 443 are public, routed through Caddy.
- Caddy auto-obtains and renews SSL certificates from Let's Encrypt.
- Set a strong `SECRET_KEY` before first deploy.
- Set a strong `POSTGRES_PASSWORD` in `backend/.env` (the docker-compose defaults are weak).

## Project Structure

```
valtherion_online/
├── backend/
│   ├── main.py              # FastAPI app (monolithic)
│   ├── .env                 # Active environment config (gitignored)
│   ├── .env.prod            # Production env template
│   ├── .env.example         # Development env template
│   ├── Dockerfile
│   └── requirements.txt
├── mobile/
│   ├── src/
│   │   ├── services/
│   │   │   ├── api.js       # Axios HTTP client
│   │   │   └── websocket.js # WebSocket client
│   │   ├── store/           # Redux slices
│   │   └── screens/        # React Native screens
│   ├── android/             # Android native project
│   └── ios/                 # iOS native project
├── Caddyfile                # Reverse proxy config
├── docker-compose.yml       # Container orchestration
├── scripts/
│   └── deploy.sh            # Automated deploy script
└── docs/                    # Game design docs
```
