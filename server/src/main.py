"""Kiha Server — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.auth_middleware import AuthenticationMiddleware
from api.routes.chat import router as chat_router
from api.routes.device import router as device_router
from api.routes.health import router as health_router
from config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("kiha")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler — startup and shutdown."""
    settings = get_settings()
    logger.error(
        "Kiha Server starting on %s:%d (debug=%s)",
        settings.server_host,
        settings.server_port,
        settings.debug,
    )

    # SQLite veritabani baslat
    from infrastructure.database.sqlite_repository import KihaDatabase
    db = KihaDatabase(
        db_path=settings.sqlite_db_path,
        frames_dir=settings.frames_storage_dir,
    )
    await db.connect()
    app.state.db = db
    logger.info("SQLite veritabani basladi: %s", settings.sqlite_db_path)

    yield

    await db.close()
    logger.error("Kiha Server shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Kiha — AI Smart Glasses Server",
        description="TÜBİTAK destekli AI tabanlı akıllı gözlük sunucu API'si",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Refactor - Restrict to Flutter app origin
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuthenticationMiddleware)

    # Routes
    app.include_router(health_router)
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(device_router, prefix="/api/v1")

    return app


app = create_app()
