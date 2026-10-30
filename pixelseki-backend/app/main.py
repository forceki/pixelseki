from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from contextlib import asynccontextmanager

from app.core.broker import broker
from app.core.config import settings
from app.features.auth.router import router as auth_router
from app.features.creations.router import router as creations_router
from app.features.gallery.router import router as gallery_router
from app.features.generations.router import router as generations_router
from app.features.users.router import router as users_router

import app.core.tasks  # noqa: F401 — register tasks with broker


@asynccontextmanager
async def lifespan(application: FastAPI):
    await broker.startup()
    yield
    await broker.shutdown()


app = FastAPI(title="PixelSeki API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET_KEY)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(generations_router, prefix="/api/v1")
app.include_router(creations_router, prefix="/api/v1")
app.include_router(gallery_router, prefix="/api/v1")


static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)

# Wrap StaticFiles with its own CORS so frontend can fetch images
static_app = StaticFiles(directory=str(static_dir))
cors_static = CORSMiddleware(
    app=static_app,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.mount("/static", cors_static, name="static")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
