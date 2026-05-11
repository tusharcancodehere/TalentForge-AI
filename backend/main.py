from __future__ import annotations

import logging
import os
from traceback import format_exc

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router as api_router
from backend.core.github_engine import lifespan


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
)
logger = logging.getLogger("talentforge")

# Fail-fast boot validation for critical runtime dependencies.
# Redis/Upstash remains optional because the application already supports
# degraded mode when leaderboard/state services are not configured.
REQUIRED_ENV_KEYS = [
    "GEMINI_API_KEY",
    "GITHUB_TOKEN",
]
missing_keys = [key for key in REQUIRED_ENV_KEYS if not os.getenv(key)]
if missing_keys:
    raise RuntimeError(
        "Fatal boot error: Missing required environment variables: "
        + ", ".join(missing_keys)
    )

optional_service_keys = [
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
]
missing_optional = [key for key in optional_service_keys if not os.getenv(key)]
if missing_optional:
    logger.warning(
        "Optional services disabled due to missing env vars: %s",
        ", ".join(missing_optional),
    )

app_env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "production")).strip().lower()
frontend_url = os.getenv("FRONTEND_URL", "").strip()
if frontend_url:
    allowed_origins = [frontend_url]
elif app_env in {"dev", "development", "local"}:
    allowed_origins = ["*"]
else:
    raise RuntimeError(
        "Fatal boot error: FRONTEND_URL must be set outside explicit dev environments."
    )

app = FastAPI(title="TalentForge AI Backend", version="1.0.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method,
        request.url.path,
        exc,
        format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": 500,
            "message": "The Architect encountered a systemic anomaly. Please try again.",
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(api_router)

_base_path = os.path.dirname(os.path.abspath(__file__))
_dist_path = os.path.join(_base_path, "dist")
_client_path = os.path.join(_dist_path, "client")
_frontend_dist = _client_path if os.path.isdir(_client_path) else _dist_path

if os.path.isdir(_frontend_dist):
    _assets_path = os.path.join(_frontend_dist, "assets")
    if os.path.isdir(_assets_path):
        app.mount("/assets", StaticFiles(directory=_assets_path), name="assets")

    @app.get("/{catchall:path}")
    async def serve_frontend(catchall: str):
        if catchall.startswith("api"):
            return JSONResponse(status_code=404, content={"detail": "API route not found"})

        _index_file = os.path.join(_frontend_dist, "index.html")
        if os.path.isfile(_index_file):
            return FileResponse(_index_file)
        return JSONResponse(status_code=404, content={"error": "Frontend index.html not found"})
else:

    @app.get("/{catchall:path}")
    async def _no_frontend(catchall: str):
        return JSONResponse(
            status_code=503,
            content={"error": "Frontend build not found. Ensure 'npm run build' completed."},
        )

