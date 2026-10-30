# PixelSeki

AI-powered pixel-art game asset generator. Describe what you need in plain text — a character, an item, a tileset — and PixelSeki generates game-ready pixel sprites, including multi-direction sprite sets and transparent backgrounds, ready to drop into a game engine.

## Who it's for

Indie game developers, game jam teams, and hobbyists who need consistent pixel-art assets quickly but don't have a dedicated artist (or want to prototype before hiring one).

## Features

- **Text-to-sprite generation** — describe an object or character and get a pixel-art sprite at a chosen size (e.g. 64×64).
- **Multi-direction sprites** — generate the same character/object facing multiple directions, with a reference image keeping every direction consistent.
- **Tilesets** — generate a set of tiles that share one global style description.
- **Camera views & pixel size** — choose the perspective (e.g. top-down, side view) and pixel resolution per job.
- **Style references** — supply a reference image so new assets match an existing art style.
- **Transparent backgrounds** — automatic background removal (rembg) for engine-ready PNGs.
- **Versioning & regeneration** — regenerate a single sprite or direction without redoing the whole job; every version is kept.
- **Live progress** — results stream in via Server-Sent Events as each sprite finishes.
- **Gallery & downloads** — browse past work and download individual assets or whole jobs.
- **Multiple AI providers** — Google Gemini or OpenAI image models, switchable per request.
- **Google sign-in & credits** — weekly free generation credits per user.

## Architecture

```
pixelseki/
├── pixelseki-backend/    FastAPI API + Taskiq background workers
└── pixelseki-frontend/   Vue 3 single-page app
```

```
Vue 3 SPA ──HTTP/SSE──▶ FastAPI ──▶ PostgreSQL (users, jobs, creations, logs)
                           │
                           └──▶ Redis queue ──▶ Taskiq worker ──▶ Gemini / OpenAI
                                                      │
                                                      └──▶ rembg ──▶ S3 or local disk
```

| Layer | Tech |
|---|---|
| Frontend | Vue 3, TypeScript, Pinia, Vue Router, Tailwind CSS, Vite |
| Backend | Python 3.11+, FastAPI, SQLAlchemy (async) + asyncpg, Alembic |
| Jobs | Taskiq + Redis |
| AI | Google Gemini (`google-genai`), OpenAI image API |
| Image processing | rembg, Pillow |
| Storage | AWS S3 (optional; falls back to local disk) |
| Auth | Google Identity Services + JWT |

## Quick start

Prerequisites: Python 3.11+, Node.js 20.19+ / 22.12+, PostgreSQL 14+, Redis 6+, a Gemini and/or OpenAI API key, and Google OAuth credentials.

**Backend**

```bash
cd pixelseki-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in your keys
alembic upgrade head
```

Run the API and the worker in separate terminals — see [pixelseki-backend/README.md](pixelseki-backend/README.md) for the exact commands.

**Frontend**

```bash
cd pixelseki-frontend
npm install
# create .env with VITE_API_URL and VITE_GOOGLE_CLIENT_ID
npm run dev
```

Open http://localhost:5173.

## Docs

- [Backend README](pixelseki-backend/README.md) — env vars, database, API, workers
- [Frontend README](pixelseki-frontend/README.md) — setup, auth flow, SSE streaming, styling
