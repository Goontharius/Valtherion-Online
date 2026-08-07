# Valtherion Online Backend

This FastAPI backend supports the core Valtherion systems: player auth, inventory, movement, skills, party and guild management, shop interactions, and real-time chat.

## Local Setup

1. Create a Python virtual environment:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and update credentials:

```bash
cp .env.example .env
```

3. Start the backend:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Docker Setup

The backend is ready for containerized deployment with PostgreSQL and Redis.

```bash
cd /Users/tfe/Projects/valtherion_online
docker compose up --build
```

The service will be available at `http://localhost:8000`.

## Notes

- The backend now loads configuration from environment variables.
- Database tables are created automatically on startup.
- The full game design document is stored at `../docs/Valtherion Online 4.0 GDD.txt`.
