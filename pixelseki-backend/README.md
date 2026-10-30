# PixelSeki — Backend API

FastAPI backend for PixelSeki. Handles authentication, image generation via Google Gemini, background removal, and async task processing.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Google Gemini API key
- Google OAuth 2.0 credentials

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Environment Variables

Copy the example and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://postgres:postgres@localhost:5432/pixel_generation` | PostgreSQL connection string (must use `asyncpg` driver) |
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key from [AI Studio](https://aistudio.google.com/apikey) |
| `GOOGLE_CLIENT_ID` | Yes | — | OAuth 2.0 Client ID from [Google Cloud Console](https://console.cloud.google.com/) |
| `GOOGLE_CLIENT_SECRET` | Yes | — | OAuth 2.0 Client Secret |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection for task queue |
| `JWT_SECRET_KEY` | Yes | `change-this-secret` | Random secret for signing JWT tokens. **Change this.** |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Token expiry in minutes |
| `CORS_ORIGINS` | No | `["http://localhost:5173", "http://localhost:3000"]` | Allowed frontend origins (JSON array) |
| `APP_HOST` | No | `0.0.0.0` | Server bind host |
| `APP_PORT` | No | `8000` | Server bind port |
| `APP_ENV` | No | `development` | `development` enables SQLAlchemy echo logging |

Example `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pixel_generation
GEMINI_API_KEY=AIza...
GOOGLE_CLIENT_ID=198...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=my-random-secret-key-here
```

## Database

Create the database and run migrations:

```bash
createdb pixel_generation
alembic upgrade head
```

### Migration Commands

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Roll back one migration
alembic downgrade -1

# Check current migration state
alembic current
```

## Running

You need **2 terminals** — one for the API server, one for the task worker.

**Terminal 1 — API server:**

```bash
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Task worker:**

```bash
source venv/bin/activate
taskiq worker app.core.tasks:broker
```

The worker is required — it processes image generation jobs from Redis. Without it, jobs stay in "pending" status forever.

### Verify

- Health check: `GET http://localhost:8000/health` → `{"status": "ok"}`
- API docs: `http://localhost:8000/docs` (Swagger UI)

## Project Structure

```
app/
├── main.py                    # FastAPI app, lifespan, middleware, route registration
├── core/
│   ├── config.py              # Pydantic Settings (all env vars)
│   ├── database.py            # Async SQLAlchemy engine + session factory
│   ├── broker.py              # Taskiq Redis broker
│   ├── tasks.py               # Background tasks (generate, regenerate, creation)
│   ├── security.py            # JWT creation/verification, get_current_user dependency
│   └── gemini.py              # Gemini client, prompt builders, generate_image()
└── features/
    ├── auth/
    │   ├── router.py          # POST /auth/google/login
    │   └── services.py        # Google token verification, find-or-create user
    ├── users/
    │   ├── models.py          # User model (email, google_id, credits, etc.)
    │   ├── router.py          # GET/PATCH /users/me
    │   └── services.py        # User CRUD
    ├── generations/
    │   ├── models.py          # GenerationJob + GenerationItem models
    │   ├── schemas.py         # Request/response Pydantic models
    │   ├── router.py          # All /generations endpoints + SSE stream
    │   ├── services.py        # Generation pipeline, background removal, regeneration
    │   └── log_model.py       # GeminiLog model (API call logging)
    └── creations/
        ├── models.py          # Creation model (categories, directions, versions)
        ├── schemas.py         # Request/response Pydantic models
        ├── router.py          # All /creations endpoints
        └── services.py        # Creation pipeline, prompt building
```

## API Endpoints

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/google/login` | Exchange Google `id_token` for JWT |

### Users
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/users/me` | Get current user profile |
| PATCH | `/api/v1/users/me` | Update name/avatar |

### Generations (Sprite Generator)
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/generations` | Create job (multipart form) |
| GET | `/api/v1/generations` | List jobs |
| GET | `/api/v1/generations/{id}` | Get job with items |
| PATCH | `/api/v1/generations/{id}` | Update job name |
| DELETE | `/api/v1/generations/{id}` | Delete job |
| GET | `/api/v1/generations/{id}/stream` | SSE progress stream |
| GET | `/api/v1/generations/{id}/download` | Download ZIP |
| POST | `/api/v1/generations/{id}/items` | Add direction/tile |
| POST | `/api/v1/generations/{id}/items/{item_id}/regenerate` | Regenerate item |

### Creations (Creation Studio)
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/creations` | Create (multipart form) |
| GET | `/api/v1/creations` | List creations |
| GET | `/api/v1/creations/{id}` | Get creation |
| DELETE | `/api/v1/creations/{id}` | Delete creation |
| GET | `/api/v1/creations/{id}/download` | Download ZIP |
| GET | `/api/v1/creations/{id}/versions` | Version history |
| POST | `/api/v1/creations/{id}/regenerate` | Create new version |

## How Generation Works

1. API receives request → creates DB record → enqueues task to Redis
2. Worker picks up task → builds prompt (description + direction + category + specs)
3. If reference image exists, it's sent to Gemini as multimodal input
4. For multi-direction sprites: front-facing generated first, then used as reference for remaining directions
5. Raw output saved as `original.png`
6. Background removed via `rembg` → saved as `output.png` (or skipped for creations without `transparent_bg`)
7. DB status updated to `completed` or `failed`
8. Frontend picks up the change via polling or SSE

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Activate venv: `source venv/bin/activate` |
| `connection refused` port 5432 | Start PostgreSQL |
| `connection refused` port 6379 | Start Redis |
| Jobs stuck in "pending" | Start the Taskiq worker (Terminal 2) |
| `alembic upgrade head` fails | Check `DATABASE_URL` and that the database exists |
| Gemini returns no image | Check `GEMINI_API_KEY` is valid and has quota |
