# Valtherion Online

A cross-platform RPG project with a React Native mobile client and FastAPI backend.

## Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy the example environment file and update values:

```bash
cp .env.example .env
```

Example values:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/valtherion
REDIS_URL=redis://127.0.0.1:6379
SECRET_KEY=your-secret-key-here-change-in-production
```

Run the backend:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Containerized Deployment

From the project root:

```bash
docker compose up --build
```

The backend will be available at `http://localhost:8000`.

## Game Design Docs

- Full extracted GDD text: `docs/Valtherion Online 4.0 GDD.txt`
- Summary of implemented systems: `docs/GDD_SUMMARY.md`

## Mobile Setup (React Native)

```bash
cd mobile
npm install
```

Run on Android:

```bash
npm run android
```

Run on iOS:

```bash
npm run ios
```

## Notes

- The backend uses JWT authentication and supports WebSocket messaging for real-time features.
- The mobile app includes a game screen, inventory, chat, guild, and party navigation.
