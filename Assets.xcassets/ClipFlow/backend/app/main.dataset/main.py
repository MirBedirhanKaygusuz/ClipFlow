"""ClipFlow Backend — FastAPI Application."""

import shutil
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import upload, process, download, styles, folders, music, thumbnails, validate
from app.config import settings
from app.exceptions import ClipFlowError

# Structured logging — JSON format
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify FFmpeg, create storage dir."""
    # Check FFmpeg
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg bulunamadı! Lütfen yükleyin.")

    version = subprocess.run(
        ["ffmpeg", "-version"], capture_output=True, text=True
    ).stdout.split("\n")[0]
    log.info("ffmpeg_found", version=version)

    # Create storage directory
    Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
    log.info("storage_ready", path=settings.storage_path)

    log.info("app_started", version="0.1.0")
    yield
    log.info("app_shutdown")


app = FastAPI(
    title="ClipFlow API",
    version="0.1.0",
    description="AI-powered video editor backend",
    lifespan=lifespan,
)

# CORS — V1: permissive, V2: restrict to app domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(process.router, prefix="/api/v1", tags=["process"])
app.include_router(download.router, prefix="/api/v1", tags=["download"])
app.include_router(styles.router, prefix="/api/v1", tags=["styles"])
app.include_router(folders.router, prefix="/api/v1", tags=["folders"])
app.include_router(music.router, prefix="/api/v1", tags=["music"])
app.include_router(thumbnails.router, prefix="/api/v1", tags=["thumbnails"])
app.include_router(validate.router, prefix="/api/v1", tags=["validate"])


@app.exception_handler(ClipFlowError)
async def clipflow_error_handler(request: Request, exc: ClipFlowError) -> JSONResponse:
    """Map ClipFlow custom exceptions to HTTP error responses."""
    return JSONResponse(
        status_code=exc.code,
        content={"error": exc.message},
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
