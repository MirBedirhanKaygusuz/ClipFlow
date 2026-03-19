"""ClipFlow Backend — FastAPI Application."""

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import upload, process, download
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

app = FastAPI(
    title="ClipFlow API",
    version="0.1.0",
    description="AI-powered video editor backend",
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
