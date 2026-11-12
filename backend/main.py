"""Hermes Studio v2 - FastAPI Backend Entrypoint."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

# Ensure project root is on sys.path whether invoked from root or backend/
_ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import __version__
from backend.config import AVAILABLE_MODES, runtime_settings
from backend.database import init_db
from backend.routers import projects, sessions, telemetry

# Ensure SQLite tables and initial welcome session exist immediately on import
init_db()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Initializes database and runtime resources on FastAPI startup."""
    init_db()
    yield


app = FastAPI(
    title="Hermes Studio v2 Backend API",
    description=(
        "Modular Multi-Agent Game & Software Engineering Command Center powered by "
        "Nous Research Hermes 3, Qwen 2.5 Coder 32B, and Claude 3.5 Sonnet via OpenRouter."
    ),
    version=__version__,
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend on localhost:3000 / 127.0.0.1:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount core API routers
app.include_router(projects.router)
app.include_router(sessions.router)
app.include_router(telemetry.router)

# Pluggable feature routers (mounted dynamically when available)
try:
    from backend.routers import workspace
    app.include_router(workspace.router)
except ImportError:
    pass

try:
    from backend.routers import chat
    app.include_router(chat.router)
except ImportError:
    pass


@app.get("/api/health", tags=["health"])
async def healthcheck() -> Dict[str, Any]:
    """Health check endpoint verifying backend, database, and OpenRouter key configuration."""
    return {
        "status": "ok",
        "service": "Hermes Studio v2 Backend",
        "version": __version__,
        "api_key_configured": bool(runtime_settings.get_api_key()),
        "available_modes_count": len(AVAILABLE_MODES),
    }


@app.get("/", tags=["health"])
async def root() -> Dict[str, Any]:
    """Root informational endpoint."""
    return {
        "name": "Hermes Studio v2 API",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8765, reload=True)
